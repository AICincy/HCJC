"""Sweep orchestrator.

Each invocation:

  1. Iterates the configured surnames; for each, GETs the list page and parses
     rows currently in HCSO custody.
  2. Fetches the detail page for any inmate id we don't already know about, or
     whose record is older than ``--max-detail-age-hours``.
  3. Extracts + downscales the inline booking photo.
  4. Writes data/current.json and appends to data/changelog.json.
  5. Removes photos belonging to released inmates.

Designed to fit a ~25-minute budget at Crawl-delay: 10s, so it can run on the
`*/15 * * * *` GitHub Actions cron (with a 20-minute skip-gate to keep effective
cadence at ~20-45 min).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .client import DEFAULT_CONCURRENCY, HcsoClient, make_client
from .models import Inmate, ListRow, utcnow_iso
from .parsers import parse_detail_page, parse_list_page
from .photos import downscale_and_save
from .store import (
    WAF_BLOCK_LOG_PATH,
    SnapshotCorruptError,
    append_block_evidence,
    diff,
    load_block_log,
    load_changelog,
    load_current_or_raise,
    save_anon_changelog,
    save_changelog,
    save_current,
)
from .sweep_guards import (
    PHOTO_PRUNE_MAX_FRACTION,
    SWEEP_BOOTSTRAP_FLOOR,
    SWEEP_MIN_ROSTER_FRACTION,
    check_detail_watchdog,
    prune_photos,
    roster_stale_hours,
    sweep_looks_healthy,
)

log = logging.getLogger("jcstream.sweep")


SEARCH_PATH = "/justice-center-services/inmate-search/"
DETAIL_PATH = "/justice-center-services/inmate-search/inmate-detail/"
PHOTOS_DIR = Path("data/photos")
CURRENT_PATH = Path("data/current.json")
CHANGELOG_PATH = Path("data/changelog.json")
# Phase 11: PII-stripped append-only log of all events, kept forever. Events
# older than ANON_EXPIRY_DAYS lose name/inmate_number/booking_number; only
# event type, date (day), tier, and primary charge category survive.
ANON_CHANGELOG_PATH = Path("data/anon_changelog.json")

# sweep-F6: orchestrator-side wall-clock cap. The detail-fetch loop bails
# when this many seconds have elapsed since make_client(); the finally
# block then writes the partial roster (clean_finish=True). The GitHub
# Actions workflow has timeout-minutes: 50, so 22 minutes leaves time for
# the build + commit + Pages deploy that follow this script. Without the
# cap a slow-but-not-failing HCSO front-end could let the runner kill the
# job mid-checkpoint at 50 minutes rather than producing a clean partial.
SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60


def _prev_generated_utc(path: Path) -> str | None:
    """The ``generated_utc`` of the last-good roster file, or None if the file
    is missing/malformed. Used by the freeze alarm to measure how long the
    degraded-roster guard has been holding stale data."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    gen = data.get("generated_utc") if isinstance(data, dict) else None
    # Only a str is usable by roster_stale_hours (which calls .strip()); a
    # malformed non-str generated_utc degrades to None rather than crashing
    # the freeze-alarm path.
    return gen if isinstance(gen, str) else None


@dataclass(frozen=True)
class _BlockObservation:
    """One degraded-sweep observation, bundled so _record_block_evidence takes a
    single cohesive argument. ``block_sample`` is the forensic snapshot of the
    block response (status, body length + SHA-256, body sample, headers)."""
    prev_count: int
    seen_count: int
    n_surnames: int
    n_failed: int
    status_counts: dict[str, int]
    block_sample: dict | None = None


def _record_block_evidence(obs: _BlockObservation) -> None:
    """Append a 'blocked' record to the durable WAF-block evidence log when the
    degraded-roster guard fires. Do-not-evade posture: we document the denial
    rather than route around it."""
    stale_h = roster_stale_hours(_prev_generated_utc(CURRENT_PATH))
    append_block_evidence({
        "timestamp_utc": utcnow_iso(),
        "event": "blocked",
        "prev_count": obs.prev_count,
        "seen_count": obs.seen_count,
        "surnames_total": obs.n_surnames,
        "surnames_failed": obs.n_failed,
        "failed_fraction": round(obs.n_failed / obs.n_surnames, 4) if obs.n_surnames else 0.0,
        "http_status_counts": obs.status_counts,
        "block_sample": obs.block_sample,
        "roster_stale_hours": round(stale_h, 1) if stale_h is not None else None,
        "note": "HCSO list sweep returned a degraded roster; last-good data kept.",
    }, WAF_BLOCK_LOG_PATH)



def _record_recovery_if_blocked(seen_count: int) -> None:
    """If the last evidence entry was 'blocked', append a single 'recovered'
    record so each denial period has a clean end-timestamp. No-op otherwise."""
    entries = load_block_log(WAF_BLOCK_LOG_PATH)
    if entries and entries[-1].get("event") == "blocked":
        append_block_evidence({
            "timestamp_utc": utcnow_iso(),
            "event": "recovered",
            "seen_count": seen_count,
            "note": "HCSO list sweep succeeded; automated access restored.",
        }, WAF_BLOCK_LOG_PATH)



def _record_egress_evidence() -> None:
    """Best-effort: on a block, snapshot the runner egress IP against GitHub's
    published Actions ranges into data/egress_evidence.json, so the record shows
    which source IP HCSO blocked. Gated on JCSTREAM_CAPTURE_EGRESS=1 so it runs
    only in the CI sweep (it makes a network call), not in unit tests. Never
    raises: an egress-lookup failure must not break the sweep."""
    if os.environ.get("JCSTREAM_CAPTURE_EGRESS") != "1":
        return
    try:
        from . import egress_ip
        rec = egress_ip.write_snapshot()
        log.info("egress evidence captured: runner_ip=%s in_actions_range=%s",
                 rec.get("runner_ip"), rec.get("runner_ip_in_actions_range"))
    except Exception as e:
        log.warning("egress evidence capture failed (non-fatal): %s", e)


# Back-compat alias: prefer scraper.sweep_guards.sweep_looks_healthy in new code.
_sweep_looks_healthy = sweep_looks_healthy


MIN_SWEEP_INTERVAL_S = 20 * 60  # 20 minutes


@dataclass
class WafBackoffTracker:
    """Thread-safe WAF-block backoff tracker, instantiated once per sweep run.

    Replaces the prior module-level globals (_waf_block_streak, _waf_block_lock)
    so each run() gets a clean instance and there is no stale-streak window:
    observe() atomically increments the streak AND computes the backoff inside
    the lock, returning the backoff seconds directly.
    """

    _BASE_S: float = 2.0
    _CAP_S: float = 30.0
    _streak: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def observe(self) -> tuple[int, float]:
        """Record a WAF-block-shaped response (thread-safe).

        Returns ``(streak, backoff_seconds)`` computed atomically so the
        caller never acts on a stale streak value.
        """
        with self._lock:
            self._streak += 1
            streak = self._streak
            backoff = min(self._BASE_S * (2 ** (streak - 1)), self._CAP_S)
        return streak, backoff

    def clear(self) -> None:
        """Reset the streak after a successful parse."""
        with self._lock:
            self._streak = 0

    @property
    def streak(self) -> int:
        with self._lock:
            return self._streak


# Valid HCSO inmate-detail pages are 91-230 KB (2026-05-19 verification). The
# WAF returns truncated/blocked responses well under 5 KB to automated callers,
# and parse_detail_page silently yields an empty Inmate from them.
_WAF_BLOCK_MAX_BYTES = 5000


def _looks_like_waf_block(html: str, inm: Inmate, photo_bytes: bytes | None,
                          photo_url: str | None) -> bool:
    """True when a detail response has the shape of a WAF block: a tiny body
    that parsed to no name, no charges, and no photo. Pure predicate, extracted
    from _fetch_one so the heuristic that drives the retry/backoff and the
    carry-forward is unit-testable in isolation."""
    return (
        len(html) < _WAF_BLOCK_MAX_BYTES
        and not inm.last_name
        and not inm.first_name
        and not inm.charges
        and not photo_bytes
        and not photo_url
    )


def _list_response_looks_blocked(html: str, rows: list[ListRow]) -> bool:
    """True when a surname-search response has the shape of a WAF block served
    as HTTP 200: a tiny body that parsed to zero rows. A legitimate no-results
    search still returns the full page chrome (tens of KB), so the size floor
    (``_WAF_BLOCK_MAX_BYTES``) discriminates a block stub from a real empty
    result. This is the 200-mode sibling of the 403 path in ``_sweep_list``."""
    return not rows and len(html) < _WAF_BLOCK_MAX_BYTES


def _plan_detail_fetch(
    seen_ids: set[str], previous: dict[str, Inmate], refresh_known: bool
) -> list[str]:
    """Return the sorted inmate ids whose detail pages should be fetched."""
    to_fetch: list[str] = []
    for inmate_id in sorted(seen_ids):
        if inmate_id not in previous:
            to_fetch.append(inmate_id)
        elif refresh_known:
            to_fetch.append(inmate_id)
        elif not previous[inmate_id].photo_filename:
            to_fetch.append(inmate_id)
    return to_fetch


def _carry_forward_known(
    current: dict[str, Inmate],
    seen_ids: set[str],
    previous: dict[str, Inmate],
    to_fetch: list[str],
) -> None:
    """Copy unchanged known inmates into ``current`` with refreshed last_seen."""
    to_fetch_set = set(to_fetch)
    for inmate_id in seen_ids:
        if inmate_id in previous and inmate_id not in to_fetch_set:
            current[inmate_id] = previous[inmate_id].model_copy(update={"last_seen_utc": utcnow_iso()})


def _maybe_checkpoint_partial(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    done: int,
    total: int,
) -> None:
    """Persist an in-progress roster checkpoint when it clears safety guards."""
    if (
        len(previous) < SWEEP_BOOTSTRAP_FLOOR
        or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous)
    ):
        save_current(CURRENT_PATH, current.values())
        log.info("checkpoint: %d/%d details fetched, %d inmates", done, total, len(current))
    else:
        log.info(
            "checkpoint skipped at %d/%d details: in-memory "
            "roster %d below %.0f%% of previous %d",
            done, total, len(current),
            100 * SWEEP_MIN_ROSTER_FRACTION, len(previous),
        )


def _fetch_details(
    *,
    client: HcsoClient,
    to_fetch: list[str],
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    row_by_id: dict[str, ListRow],
    dry_run: bool,
    waf_tracker: WafBackoffTracker,
) -> tuple[int, int, int]:
    """Run the detail-page worker pool and merge successful or fallback rows."""
    done = 0
    n_detail_attempts = 0
    n_detail_named = 0
    n_detail_with_photo = 0
    t0 = time.monotonic()
    sweep_started = time.monotonic()
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        futures = {
            pool.submit(_fetch_one, client, iid, previous, row_by_id.get(iid), waf_tracker=waf_tracker): iid
            for iid in to_fetch
        }
        for fut in as_completed(futures):
            # sweep-F6: bail out cleanly when we've burned the wall-clock
            # budget. The finally block still writes the partial roster
            # (clean_finish=True because we exited the try-body naturally).
            if time.monotonic() - sweep_started > SWEEP_WALLCLOCK_HARD_CAP_S:
                log.warning(
                    "sweep wall-clock cap reached at %d/%d details; finalizing",
                    done, len(to_fetch),
                )
                break
            done += 1
            n_detail_attempts += 1
            iid = futures[fut]
            try:
                inm, detail_named, detail_had_photo = fut.result()
            except Exception as e:
                # One worker raising shouldn't terminate the pool - the
                # other detail fetches and the final write still run.
                # Count it as an attempt with neither name nor photo so
                # the watchdog reflects the failure. Fall back to the
                # previous snapshot entry if we have one so a transient
                # detail-page error doesn't drop the inmate from current.
                log.warning("detail fetch worker raised: %s", e)
                if iid in previous:
                    current[iid] = previous[iid].model_copy(update={"last_seen_utc": utcnow_iso()})
                continue
            if inm is not None:
                current[inm.inmate_number] = inm
            elif iid in previous:
                # _fetch_one returned None (HCSO refused or timed out).
                # Without this fallback the inmate would silently drop
                # out of current.json for one cycle and re-appear on the
                # next; with it, we keep their previous record (preserves
                # cached photo and bio) until the next successful fetch.
                current[iid] = previous[iid].model_copy(update={"last_seen_utc": utcnow_iso()})
            if detail_named:
                n_detail_named += 1
            if detail_had_photo:
                n_detail_with_photo += 1
            if not dry_run and done % 50 == 0:
                # sweep-F3: don't checkpoint a sub-threshold roster.
                # Bootstrap (previous below floor) always checkpoints;
                # otherwise the in-memory size must still clear the
                # 50% guard. A real catastrophic mid-sweep crash with
                # a huge to_fetch list now keeps the previous-good
                # snapshot until the next ~20-45 minute retry, rather
                # than persisting a degraded baseline.
                _maybe_checkpoint_partial(previous, current, done, len(to_fetch))
    elapsed_s = round(time.monotonic() - t0, 2)
    log.info(
        "detail phase: %d attempts, %d named, %d with photo in %.1fs",
        n_detail_attempts, n_detail_named, n_detail_with_photo, elapsed_s,
    )
    return n_detail_attempts, n_detail_named, n_detail_with_photo


def _save_changelog_and_anon(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
) -> None:
    """Append diff events and refresh the anonymized rolling feed."""
    events = diff(previous, current)
    if not events:
        return
    log.info("diff: %d events (%d booked, %d released, %d updated)",
             len(events),
             sum(1 for e in events if e.event == "booked"),
             sum(1 for e in events if e.event == "released"),
             sum(1 for e in events if e.event == "updated"))
    changelog = load_changelog(CHANGELOG_PATH)
    changelog.extend(events)
    save_changelog(CHANGELOG_PATH, changelog)
    # Phase 11: maintain the PII-expiring append-only feed.
    # Build enrichment so anonymized rows still carry tier +
    # category aggregate signal (which is what makes the
    # long-term feed useful at all).
    enrichment: dict[str, dict] = {}
    offenses_path = Path("data/orc_offenses.json")
    offenses: dict = {}
    if offenses_path.exists():
        try:
            offenses = json.loads(offenses_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            offenses = {}
    for inm in current.values():
        first_charge = inm.charges[0] if inm.charges else None
        tier = None
        category = None
        if first_charge:
            code = (first_charge.orc_code or "").strip()
            ent = offenses.get(code) if isinstance(offenses, dict) else None
            if isinstance(ent, dict):
                tier = ent.get("degree")
                category = ent.get("title")
        enrichment[inm.inmate_number] = {
            "tier": tier,
            "category": category,
        }
    save_anon_changelog(ANON_CHANGELOG_PATH, changelog, enrichment)


def run(
    surnames: list[str],
    *,
    max_surnames: int | None,
    refresh_known: bool,
    dry_run: bool,
) -> int:
    if max_surnames is not None:
        surnames = surnames[:max_surnames]
    sweep_id = uuid.uuid4().hex[:12]
    log.info(
        "sweep %s started (surnames=%d, max=%s, refresh=%s, dry_run=%s)",
        sweep_id, len(surnames), max_surnames, refresh_known, dry_run,
    )

    # Skip-gate: don't re-scrape if the roster DATA is still fresh. Key off the
    # generated_utc inside current.json, NOT the file mtime: actions/checkout
    # rewrites every file each run, so st_mtime is always "just now" on CI and an
    # mtime-based gate skipped the scrape every cycle (the 2026-05-19 roster
    # freeze). generated_utc is file content, so it survives the checkout.
    stale_h = roster_stale_hours(_prev_generated_utc(CURRENT_PATH))
    if stale_h is not None and stale_h * 3600 < MIN_SWEEP_INTERVAL_S:
        log.info(
            "current.json data is %.0fs old (< %ds); skipping this cycle",
            stale_h * 3600, MIN_SWEEP_INTERVAL_S,
        )
        return 0

    try:
        previous = load_current_or_raise(CURRENT_PATH)
    except SnapshotCorruptError as e:
        # Refuse the cycle: a missing-file bootstrap is fine, but a corrupted
        # current.json composed with the SWEEP_BOOTSTRAP_FLOOR semantics would
        # let any non-trivial sweep canonicalize a degraded roster. Keep the
        # last-good (broken) file in place so the operator can inspect it.
        log.error(
            "refusing sweep: data/current.json is unreadable (%s); "
            "last-good file kept in place for inspection",
            e,
        )
        log.error("sweep %s aborted (corrupt snapshot)", sweep_id)
        return 0
    log.info("loaded %d previously-known inmates", len(previous))

    current: dict[str, Inmate] = {}
    seen_ids: set[str] = set()
    roster_ok = True
    # Set just before the try-block exits cleanly. The finally below uses this
    # flag to decide whether to compute a diff() and append to the changelog:
    # an interrupted sweep persists its partial roster snapshot (so the next
    # cycle anchors correctly) but MUST NOT emit a wave of synthetic
    # "released" events for ids it simply never reached.
    clean_finish = False

    try:
        with make_client() as client:
            rows, n_failed, status_counts, block_sample = _sweep_list(client, surnames)
            seen_ids = {r.inmate_number for r in rows}
            log.info("list sweep returned %d unique inmate ids (%d/%d surname fetches failed)",
                     len(seen_ids), n_failed, len(surnames))

            if not sweep_looks_healthy(len(previous), len(seen_ids), len(surnames), n_failed):
                roster_ok = False
                log.error(
                    "list sweep looks degraded (prev=%d, seen=%d, %d/%d surname fetches failed) "
                    "— NOT writing the roster this cycle; keeping last-good data",
                    len(previous), len(seen_ids), n_failed, len(surnames),
                )

                # The list-sweep guard thresholds (>10% surname errors or
                # roster collapsed below 50% of prior) are checked in
                # scraper/sweep_guards.sweep_looks_healthy. A prolonged freeze
                # is surfaced by the "Roster freeze alarm" step in sweep.yml
                # (roster_stale_hours), which runs every cycle regardless of
                # which guard path fired. Document the denial as durable
                # evidence (do-not-evade posture); never route around it.
                _record_block_evidence(_BlockObservation(
                    prev_count=len(previous), seen_count=len(seen_ids),
                    n_surnames=len(surnames), n_failed=n_failed,
                    status_counts=status_counts, block_sample=block_sample))
                _record_egress_evidence()
                log.error("sweep %s blocked (degraded list guard)", sweep_id)
                return 0

            # Healthy sweep: if we were previously blocked, close the denial
            # period with a 'recovered' evidence record.
            _record_recovery_if_blocked(len(seen_ids))

            # Decide which detail pages to fetch.
            to_fetch = _plan_detail_fetch(seen_ids, previous, refresh_known)

            log.info("will fetch %d detail pages (refresh_known=%s)", len(to_fetch), refresh_known)

            # Carry forward records we already know about and aren't re-fetching.
            _carry_forward_known(current, seen_ids, previous, to_fetch)

            # Map inmate_id -> list row for name fallback when the detail
            # page heading is missing/unparseable.
            row_by_id = {r.inmate_number: r for r in rows}
            waf_tracker = WafBackoffTracker()
            n_detail_attempts, n_detail_named, n_detail_with_photo = _fetch_details(
                client=client,
                to_fetch=to_fetch,
                previous=previous,
                current=current,
                row_by_id=row_by_id,
                dry_run=dry_run,
                waf_tracker=waf_tracker,
            )
            watchdog_ok = check_detail_watchdog(
                n_detail_attempts, n_detail_named, n_detail_with_photo
            )
            # Watchdog already logs WARN to stdout via check_detail_watchdog;
            # the hard-BLOCK path flips roster_ok so the finally block keeps
            # the last-good roster.
            if not watchdog_ok:
                roster_ok = False

        clean_finish = True
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
    except Exception:
        # Anything else escaping the sweep body is unexpected: log and re-raise.
        # `roster_ok` stays True only if we already cleared the list-sweep
        # guard; the `finally` will use that to decide whether to persist
        # the partial roster.
        log.exception("unhandled exception in sweep main loop")
        log.error("sweep %s failed with unhandled exception", sweep_id)
        raise
    finally:
        # Write whatever we have so far (so an interrupted sweep doesn't blank
        # the site) - but never when the list sweep itself looked degraded.
        save_ok = False
        if not dry_run and roster_ok:
            try:
                save_current(CURRENT_PATH, current.values())
                save_ok = True
            except OSError as e:
                # Disk full, permission denied, atomic-rename failure. The
                # snapshot is unchanged on disk; just skip the prune to avoid
                # deleting photos for ids that never made it to current.json.
                log.error("save_current failed (%s); skipping changelog and prune", e)

            if save_ok and clean_finish:
                _save_changelog_and_anon(previous, current)
            elif save_ok:
                # Interrupted (or otherwise short-circuited) sweep: do not diff.
                # `current` is a partial subset of `previous`, so every unreached
                # id would synthesize a bogus `released` event and evict real
                # events from the rolling CHANGELOG_LIMIT=500 window.
                log.warning(
                    "skipping diff/changelog append: sweep did not finish cleanly"
                )
            # sweep-F5: only prune photos when save_current succeeded for this
            # cycle. A failed save leaves seen_ids ungrounded against any
            # persisted snapshot; pruning then could delete photos for ids
            # that were never written and that the next cycle still needs.
            if save_ok and seen_ids:
                _prune_and_report(PHOTOS_DIR, seen_ids)


    if dry_run:
        log.info("dry-run; not writing")
    log.info(
        "sweep %s completed (roster_ok=%s, clean=%s, seen=%d, current=%d)",
        sweep_id, roster_ok, clean_finish, len(seen_ids), len(current),
    )
    return 0


# Back-compat alias: prefer scraper.sweep_guards.check_detail_watchdog in new code.
_check_detail_watchdog = check_detail_watchdog


def _prune_and_report(photos_dir: Path, active_ids: set[str]) -> None:
    """Run ``prune_photos`` and log when the safety threshold skips the prune.

    The skip path in ``sweep_guards.prune_photos`` is one of the silent-staleness
    pre-conditions: the prune passes but the on-disk photo set drifts out of
    sync with the roster. The check below is a *read* against the same
    filesystem the prune is about to inspect, so it can't lie about what the
    prune would have done. We keep the prune logic untouched and just report.
    """
    if photos_dir.exists():
        existing = list(photos_dir.glob("*.jpg"))
        doomed = [f for f in existing if f.stem not in active_ids]
        if doomed and existing and len(doomed) / len(existing) > PHOTO_PRUNE_MAX_FRACTION:
            log.warning(
                "photo prune skipped: %d/%d (%.1f%%) exceed threshold",
                len(doomed), len(existing),
                100.0 * len(doomed) / len(existing),
            )
    prune_photos(photos_dir, active_ids)


_SENSITIVE_HEADERS = frozenset({"cookie", "set-cookie", "authorization", "proxy-authorization"})


def _redact_headers(headers: httpx.Headers) -> dict:
    """Copy request/response headers for the evidence log, replacing the value
    of any session or credential header with a placeholder. The header's
    presence is preserved (forensically useful) but its token value never
    reaches the public data/waf_block_log.json: a WAF can set a clearance
    cookie that the client's cookie jar echoes back, and a proxy could add an
    auth header."""
    return {k: ("[redacted]" if k.lower() in _SENSITIVE_HEADERS else v)
            for k, v in headers.items()}


def _forensic_sample(resp: httpx.Response) -> dict:
    """Forensic snapshot of a WAF-block response for the evidence log: capture
    time, the denied request (method/url/headers), status, body length +
    SHA-256 (tamper-evidence), a bounded body sample, and the response headers.
    A 403 block page carries no PII; session/credential headers (Cookie,
    Set-Cookie, Authorization, Proxy-Authorization) are redacted before they
    reach the public log."""
    body = resp.content or b""
    # Strip potential user-specific tokens from body (defense-in-depth;
    # WAF block pages should not contain PII but upstream can change).
    body_text = (resp.text or "")[:1000]
    body_text = re.sub(r'[0-9a-fA-F]{32,}', '[redacted-token]', body_text)
    sample: dict = {
        "captured_utc": utcnow_iso(),
        "status": resp.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "body_sample": body_text,
        "headers": _redact_headers(resp.headers),
    }
    try:
        req = resp.request
    except RuntimeError:
        req = None
    if req is not None:
        sample["request"] = {
            "method": req.method,
            "url": str(req.url),
            "headers": _redact_headers(req.headers),
        }
    return sample


def _fetch_list_page(client: HcsoClient, surname: str) -> tuple[list[ListRow] | None, int | None, dict | None]:
    """Fetch one surname-search page for ``_sweep_list``. Returns
    ``(rows, status, sample)``. ``rows`` is None on a failed fetch, which is
    either a raised error or a detected WAF block (an HTTP 403 that raised, or an
    HTTP 200 whose tiny body parsed to zero rows); the HTTP status and a forensic
    sample accompany it. Otherwise ``rows`` is the parsed list. Treating a
    detected 200-block as a failure keeps the blocked record self-consistent:
    it is counted in n_failed and the status histogram, not silently dropped.

    sweep-F8: this MUST swallow every exception and return (None, ...) on
    failure so ``as_completed`` in the caller can process all surnames even
    when individual fetches fail.
    """
    try:
        resp = client.get_response(SEARCH_PATH, params={"last": surname})
    except httpx.HTTPStatusError as e:
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, e.response.status_code, _forensic_sample(e.response)
    except Exception as e:
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, None, None
    rows = parse_list_page(resp.text)
    # Empty-page block mode: the WAF can serve HTTP 200 with a tiny body that
    # parses to zero rows (instead of a 403). The fetch does not raise, so treat
    # it as a failure here (rows=None) carrying the 200 status and a forensic
    # sample, so it is counted like the 403 path rather than silently dropped.
    if _list_response_looks_blocked(resp.text, rows):
        log.warning("list fetch for surname=%s looks WAF-blocked (HTTP %d, %d bytes, 0 rows)",
                    surname, resp.status_code, len(resp.text))
        return None, resp.status_code, _forensic_sample(resp)
    return rows, None, None


def _sweep_list(client: HcsoClient, surnames: list[str]) -> tuple[list[ListRow], int, dict[str, int], dict | None]:
    """Parallel surname search across the configured list.

    Returns ``(rows, n_failed, status_counts, block_sample)`` — ``n_failed`` is
    how many surname fetches failed, counting both raised errors and detected
    WAF blocks (an HTTP 403, or an HTTP 200 stripped to zero rows), distinct
    from a surname that legitimately returned zero rows. ``status_counts`` is a
    histogram of those statuses (e.g. ``{"403": 24}`` or ``{"200": 26}``);
    ``block_sample`` is one representative forensic snapshot of the first blocked
    response. ``status_counts`` and ``block_sample`` both feed the durable
    WAF-block evidence log. Each page is fetched by ``_fetch_list_page``.
    """
    aggregated: list[ListRow] = []
    seen: set[str] = set()
    failed = 0
    status_counts: dict[str, int] = {}
    block_sample: dict | None = None
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        futures = {pool.submit(_fetch_list_page, client, s): s for s in surnames}
        for future in as_completed(futures):
            rows, status, sample = future.result()
            if block_sample is None and sample is not None:
                block_sample = sample
            if rows is None:
                failed += 1
                if status is not None:
                    key = str(status)
                    status_counts[key] = status_counts.get(key, 0) + 1
                continue
            for r in rows:
                if r.inmate_number not in seen:
                    seen.add(r.inmate_number)
                    aggregated.append(r)
    elapsed_s = round(time.monotonic() - t0, 2)
    log.info(
        "list phase: %d unique ids, %d/%d failed in %.1fs",
        len(seen), failed, len(surnames), elapsed_s,
    )
    return aggregated, failed, status_counts, block_sample


def _fetch_one(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    list_row: ListRow | None = None,
    *,
    waf_tracker: WafBackoffTracker,
) -> tuple[Inmate | None, bool, bool]:
    """Fetch and parse one detail page.

    Returns ``(inmate, detail_named, detail_had_photo)`` — the two booleans
    reflect what the *detail parser* produced, before any list-row name
    fallback or disk-cached photo carry-forward is applied, so callers can
    measure detail-page health distinct from the list-side path.

    ``waf_tracker`` is required (keyword-only): the WAF-block streak is shared
    across the worker pool, so a caller that omitted it would silently get a
    throwaway tracker and disable cross-call backoff.
    """
    inm, photo_bytes, photo_url = _fetch_detail_with_retry(
        client, inmate_id, previous, waf_tracker
    )
    if inm is None:
        return None, False, False
    detail_named = bool(inm.last_name or inm.first_name)
    detail_had_photo = bool(photo_bytes or photo_url)

    photo_bytes = _fetch_photo_bytes_from_url(client, inmate_id, photo_url, photo_bytes)
    _apply_list_row_fallback(inm, list_row)
    _attach_photo_filename(inm, photo_bytes)
    _set_seen_timestamps(inm, inmate_id, previous)
    return inm, detail_named, detail_had_photo


def _fetch_detail_with_retry(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    waf_tracker: WafBackoffTracker,
) -> tuple[Inmate | None, bytes | None, str | None]:
    # WAF / geo-block tolerant fetch. Per the 2026-05-19 Claude.ai HCSO
    # verification, valid inmate-detail pages from HCSO are 91-230 KB.
    # HCSO's WAF returns truncated/blocked responses well under 5 KB to
    # automated callers, and the parser silently produces an empty Inmate
    # from them. On the first attempt's WAF-block-shaped response we sleep
    # the exponential backoff and retry once: if the WAF window has
    # cleared, we get a real response and the photo lands this cycle
    # rather than waiting for the next cron run.
    inm = None
    photo_bytes = None
    photo_url = None
    html = ""
    for attempt in range(2):
        try:
            html = client.get(DETAIL_PATH, params={"id": inmate_id})
        except Exception as e:
            log.warning("detail fetch failed for id=%s: %s", inmate_id, e)
            return None, None, None
        inm, photo_bytes, photo_url = parse_detail_page(html, inmate_id)
        if not _looks_like_waf_block(html, inm, photo_bytes, photo_url):
            waf_tracker.clear()
            break
        streak, backoff = waf_tracker.observe()
        if attempt == 0:
            log.warning(
                "WAF-block-shaped response for id=%s (%d bytes, streak=%d); "
                "sleeping %.1fs and retrying once",
                inmate_id, len(html), streak, backoff,
            )
            time.sleep(backoff)
            continue
        # Second attempt also looked like a block. Sleep the latest
        # backoff to slow the worker before returning, then either trigger
        # carry-forward (known inmate) or fall through to list_row
        # fallback (new inmate).
        log.warning(
            "WAF-block-shaped response for id=%s (%d bytes, streak=%d); "
            "retry also blocked, returning without overwriting",
            inmate_id, len(html), streak,
        )
        time.sleep(backoff)
        if inmate_id in previous:
            # Known inmate: return None so the carry-forward path in
            # `run()` preserves the previous-good record (cached photo,
            # prior bio + charges) instead of overwriting with empty data.
            return None, None, None
        # New inmate (not in previous): fall through so the list_row
        # fallback below can rescue the interstitial response into a
        # minimal Inmate. Better a name than nothing for a newly-booked
        # record.
        break
    # range(2) always runs iteration 0, which either returns at the
    # fetch-exception guard or assigns inm from parse_detail_page (which always
    # yields an Inmate), so inm is never None here. The assert narrows
    # Inmate | None for the type checker and documents the invariant without
    # adding a runtime branch.
    assert inm is not None
    return inm, photo_bytes, photo_url


def _fetch_photo_bytes_from_url(
    client: HcsoClient,
    inmate_id: str,
    photo_url: str | None,
    photo_bytes: bytes | None,
) -> bytes | None:
    # If the page provided a direct photo URL, fetch it (more reliable than
    # base64). Fall back to inline bytes if the URL fetch fails.
    if photo_url and not photo_bytes:
        try:
            return client.get_bytes(photo_url)
        except Exception as e:
            log.warning("photo URL fetch failed for id=%s url=%s: %s", inmate_id, photo_url, e)
    return photo_bytes


def _apply_list_row_fallback(inm: Inmate, list_row: ListRow | None) -> None:
    if list_row is None:
        return
    if not inm.last_name and list_row.last_name:
        inm.last_name = list_row.last_name
    if not inm.first_name and list_row.first_name:
        inm.first_name = list_row.first_name
    if not inm.booking_date and list_row.admit_date:
        inm.booking_date = list_row.admit_date


def _attach_photo_filename(inm: Inmate, photo_bytes: bytes | None) -> None:
    photo_path = PHOTOS_DIR / f"{inm.inmate_number}.jpg"
    # Defense-in-depth: even though the model validator enforces digits-only,
    # assert the filename is safe to prevent path traversal if the validator
    # is ever relaxed.
    if ".." in photo_path.name or "/" in photo_path.name:
        raise ValueError(f"unsafe photo filename: {photo_path.name!r}")
    # Save fresh bytes if we got them AND they decoded; otherwise fall through
    # to the disk-cached photo from a prior successful sweep. Previously the
    # second branch was an `elif`, which meant a corrupt-bytes failure on one
    # cycle would discard a previously-good cached photo from the snapshot.
    if photo_bytes and downscale_and_save(photo_bytes, photo_path):
        inm.photo_filename = photo_path.name
    elif photo_path.exists():
        inm.photo_filename = photo_path.name


def _set_seen_timestamps(inm: Inmate, inmate_id: str, previous: dict[str, Inmate]) -> None:
    inm.first_seen_utc = (
        previous[inmate_id].first_seen_utc
        if inmate_id in previous and previous[inmate_id].first_seen_utc
        else utcnow_iso()
    )
    inm.last_seen_utc = utcnow_iso()


# Back-compat alias: prefer scraper.sweep_guards.prune_photos in new code.
# Note the signature swap: the new public version takes photos_dir as the first
# arg so it can be unit-tested without monkey-patching a module-level path.
def _prune_photos(active_ids: set[str]) -> None:
    prune_photos(PHOTOS_DIR, active_ids)


def _read_surnames(path: Path) -> list[str]:
    # sweep-F7: strip a leading UTF-8 BOM (U+FEFF) if a Windows editor saved
    # the file with one. Without this the first surname becomes "﻿A",
    # HCSO returns zero rows for it, and no guard fires (one zero-row letter
    # is below the 10% failure threshold).
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    return [
        line.strip().upper()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one JCStream sweep")
    parser.add_argument("--surnames", default="data/surnames.txt", type=Path)
    parser.add_argument("--max-surnames", type=int, default=None,
                        help="cap the surname list for quick smoke tests")
    parser.add_argument("--refresh-known", action="store_true",
                        help="re-fetch detail pages even for already-known inmates")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    surnames = _read_surnames(args.surnames)
    log.info("loaded %d surnames from %s", len(surnames), args.surnames)
    started = time.monotonic()
    rc = run(
        surnames,
        max_surnames=args.max_surnames,
        refresh_known=args.refresh_known,
        dry_run=args.dry_run,
    )
    log.info("sweep finished in %.1fs (rc=%d)", time.monotonic() - started, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
