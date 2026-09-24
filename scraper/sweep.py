"""Sweep orchestrator.

Each invocation:

  1. Iterates the configured surnames; for each, GETs the list page and parses
     rows currently in HCSO custody.
  2. Fetches the detail page for any inmate id we don't already know about, or
     whose record is older than ``--max-detail-age-hours``.
  3. Extracts + downscales the inline booking photo.
  4. Writes data/current.json and appends to data/changelog.json.
  5. Removes photos belonging to released inmates.

Designed to fit a ~25-minute budget at Crawl-delay: 0.5s per worker with
16-way concurrency (scraper/client.py: DEFAULT_CRAWL_DELAY,
DEFAULT_CONCURRENCY), so it can run on the hourly GitHub Actions
cron (with a 20-minute skip-gate to avoid back-to-back runs; actual
delivery is best-effort).
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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from . import orc
from .client import DEFAULT_CONCURRENCY, HcsoClient, make_client
from .models import Inmate, ListRow, utcnow_iso
from .parsers import parse_detail_page, parse_list_page
from .photos import downscale_and_save
from .store import (
    WAF_BLOCK_LOG_PATH,
    BlockLogCorruptError,
    SnapshotCorruptError,
    _load_takedowns,
    append_block_evidence,
    append_block_evidence_deduped,
    diff,
    load_block_log,
    load_changelog,
    load_current_or_raise,
    save_anon_changelog,
    save_changelog,
    save_current,
)
from .sweep_guards import (
    SWEEP_BOOTSTRAP_FLOOR,
    SWEEP_MIN_ROSTER_FRACTION,
    DetailFailureMode,
    DetailOutcome,
    check_detail_degraded,
    check_detail_watchdog,
    classify_detail_html,
    classify_http_status_error,
    list_response_looks_blocked,
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


@dataclass(frozen=True)
class SweepPaths:
    photos_dir: Path = field(default_factory=lambda: PHOTOS_DIR)
    current_path: Path = field(default_factory=lambda: CURRENT_PATH)
    changelog_path: Path = field(default_factory=lambda: CHANGELOG_PATH)
    anon_changelog_path: Path = field(default_factory=lambda: ANON_CHANGELOG_PATH)
    takedowns_path: Path = field(default_factory=lambda: Path("data/takedowns.json"))
    orc_offenses_path: Path = field(default_factory=lambda: Path("data/orc_offenses.json"))
    waf_block_log_path: Path = field(default_factory=lambda: WAF_BLOCK_LOG_PATH)


# sweep-F6: orchestrator-side wall-clock cap. The detail-fetch loop bails
# when this many seconds have elapsed since the detail phase started (the
# clock starts at the top of _fetch_details, after the list sweep); the finally
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


def _record_block_evidence(obs: _BlockObservation, paths: SweepPaths | None = None) -> None:
    """Append a 'blocked' record to the durable WAF-block evidence log when the
    degraded-roster guard fires. Do-not-evade posture: we document the denial
    rather than route around it."""
    if paths is None:
        paths = SweepPaths()
    stale_h = roster_stale_hours(_prev_generated_utc(paths.current_path))
    append_block_evidence(
        {
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
        },
        paths.waf_block_log_path,
    )


def _record_detail_page_block(
    inmate_id: str,
    http_status: int | None,
    html: str,
    mode: DetailFailureMode,
    waf_block_log_path: Path | None = None,
) -> None:
    """Append one ``detail_page_waf_block`` record to the hash-chained
    evidence log when an HCSO inmate-detail fetch fails on its final attempt.

    Covers block-shaped bodies (WAF block, zero-byte, truncated), HTTP
    errors (404, 429, 5xx), redirects, timeouts, and connection errors.
    The ``failure_mode`` field keeps the taxonomy queryable; the event name
    stays ``detail_page_waf_block`` for continuity with the existing log
    schema. ``response_signature`` (first 16 hex of the body SHA-256) lets
    identical block templates collate without storing the full body.

    Deduplicated per (inmate_id, failure_mode) over 24 h (M-1): a stale
    inmate is refetched every cycle until its detail succeeds, so without
    dedup a weeks-long detail-only outage would append one record per
    inmate per cycle (each an O(n) full-chain verify + full-file rewrite)
    and grow the evidence log without bound. The per-cycle
    ``detail_degraded`` summary record preserves the systemic signal, so
    repeated per-inmate observations add no information.
    """
    if waf_block_log_path is None:
        waf_block_log_path = WAF_BLOCK_LOG_PATH
    response_signature = hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()[:16] if html else None
    append_block_evidence_deduped(
        {
            "timestamp_utc": utcnow_iso(),
            "event": "detail_page_waf_block",
            "inmate_id": inmate_id,
            "url": f"{DETAIL_PATH}?id={inmate_id}",
            "http_status": http_status,
            "failure_mode": mode.value,
            "response_signature": response_signature,
            "response_length": len(html) if html else 0,
        },
        waf_block_log_path,
        dedupe_event="detail_page_waf_block",
        dedupe_keys=("inmate_id", "failure_mode"),
        dedupe_hours=24.0,
    )


def _record_detail_degraded(
    attempts: int,
    failure_counts: Counter[str],
    waf_block_log_path: Path | None = None,
) -> None:
    """Append one ``detail_degraded`` record to the hash-chained evidence log
    when the systemic detail-failure guard fires. The roster still writes
    (carry-forward keeps it correct), but the degradation is durable evidence
    rather than a silent exit-0. ``failure_counts`` maps failure-mode value to
    the number of fetches whose final outcome was that mode."""
    if waf_block_log_path is None:
        waf_block_log_path = WAF_BLOCK_LOG_PATH
    n_failed = sum(failure_counts.values())
    append_block_evidence(
        {
            "timestamp_utc": utcnow_iso(),
            "event": "detail_degraded",
            "detail_attempts": attempts,
            "detail_failures": n_failed,
            "failure_fraction": round(n_failed / attempts, 4) if attempts else 0.0,
            "failure_modes": dict(sorted(failure_counts.items())),
            "note": "Detail-page fetches systemically failed; roster kept via carry-forward, details marked stale.",
        },
        waf_block_log_path,
    )


def _record_recovery_if_blocked(seen_count: int, waf_block_log_path: Path | None = None) -> None:
    """If the last evidence entry was 'blocked', append a single 'recovered'
    record so each denial period has a clean end-timestamp. No-op otherwise."""
    if waf_block_log_path is None:
        waf_block_log_path = WAF_BLOCK_LOG_PATH
    try:
        entries = load_block_log(waf_block_log_path)
    except BlockLogCorruptError as e:
        # C-1: the log is unreadable; the append path refuses writes against
        # it, so there is no recovery record to add. Loud log, no crash.
        log.error("recovery check skipped: WAF-block log unreadable (%s)", e)
        return
    if entries and entries[-1].get("event") == "blocked":
        append_block_evidence(
            {
                "timestamp_utc": utcnow_iso(),
                "event": "recovered",
                "seen_count": seen_count,
                "note": "HCSO list sweep succeeded; automated access restored.",
            },
            waf_block_log_path,
        )


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
        log.info(
            "egress evidence captured: runner_ip=%s in_actions_range=%s",
            rec.get("runner_ip"),
            rec.get("runner_ip_in_actions_range"),
        )
    except Exception as e:
        log.warning("egress evidence capture failed (non-fatal): %s", e)


# Back-compat alias: prefer scraper.sweep_guards.sweep_looks_healthy in new code.
_sweep_looks_healthy = sweep_looks_healthy


MIN_SWEEP_INTERVAL_S = 20 * 60  # 20 minutes
# Conventional exit status for SIGINT. run() returns this (rather than
# re-raising KeyboardInterrupt) so callers can observe an interrupted sweep
# as a return code; the process exit status is identical either way (Python
# exits 130 on an uncaught KeyboardInterrupt), and the finally block still
# persists the partial snapshot before the return.
INTERRUPTED_EXIT_CODE = 130


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


def _parse_hcso_booking_day(s: str) -> date | None:
    """Parse an HCSO ``M/D/YY`` / ``M/D/YYYY`` date to a ``date``.

    Returns None when the value is missing or unparseable. Comparing parsed
    dates (rather than raw strings) keeps zero-padding drift like
    ``9/20/2026`` vs ``09/20/2026`` from looking like a new booking.
    """
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _rebooked(prev: Inmate, row: ListRow | None) -> bool:
    """True when the list row's admit date differs from the stored booking date.

    HCSO reuses inmate numbers across bookings, so a changed admit date for a
    known inmate number means the person was booked again. Both sides must
    parse as an HCSO date; anything missing or unparseable is treated as "no
    change" so parser drift can never trigger a refetch storm.
    """
    if row is None:
        return False
    prev_day = _parse_hcso_booking_day(prev.booking_date)
    cur_day = _parse_hcso_booking_day(row.admit_date)
    return prev_day is not None and cur_day is not None and prev_day != cur_day


def _plan_detail_fetch(
    seen_ids: set[str],
    previous: dict[str, Inmate],
    refresh_known: bool,
    row_by_id: dict[str, ListRow] | None = None,
) -> list[str]:
    """Return the sorted inmate ids whose detail pages should be fetched.

    A known inmate is refetched when ``refresh_known`` is set, when they have
    no photo yet, when their last detail attempt failed (``detail_stale``), or
    when the list row's admit date differs from the stored booking date: that
    is a rebooking under the same inmate number, and the detail page must be
    refetched so the roster picks up the newest booking photo instead of the
    prior booking's cached one.
    """
    rows = row_by_id or {}
    to_fetch: list[str] = []
    for inmate_id in sorted(seen_ids):
        if inmate_id not in previous:
            to_fetch.append(inmate_id)
        elif refresh_known:
            to_fetch.append(inmate_id)
        elif not previous[inmate_id].photo_filename:
            to_fetch.append(inmate_id)
        elif previous[inmate_id].detail_stale:
            # A previous cycle attempted this detail page and failed (the
            # record was carried forward marked stale). Retry it: transient
            # 503s and WAF windows clear, and without this the stale mark
            # would stick until an unrelated refresh reason fired.
            to_fetch.append(inmate_id)
        elif _rebooked(previous[inmate_id], rows.get(inmate_id)):
            log.info(
                "rebooking detected for id=%s (stored booking_date=%s list admit_date=%s); "
                "refetching detail page for newest booking photo",
                inmate_id,
                previous[inmate_id].booking_date,
                rows[inmate_id].admit_date,
            )
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
    current_path: Path,
) -> None:
    """Persist an in-progress roster checkpoint when it clears safety guards."""
    if len(previous) < SWEEP_BOOTSTRAP_FLOOR or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous):
        save_current(current_path, current.values())
        log.info("checkpoint: %d/%d details fetched, %d inmates", done, total, len(current))
    else:
        log.info(
            "checkpoint skipped at %d/%d details: in-memory roster %d below %.0f%% of previous %d",
            done,
            total,
            len(current),
            100 * SWEEP_MIN_ROSTER_FRACTION,
            len(previous),
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
    current_path: Path,
    photos_dir: Path,
    waf_block_log_path: Path | None = None,
) -> tuple[int, int, int, Counter[str]]:
    """Run the detail-page worker pool and merge successful or fallback rows.

    Returns ``(attempts, named, with_photo, failure_counts)`` where
    ``failure_counts`` maps each non-``ok`` :class:`DetailFailureMode` value
    to the number of fetches whose final outcome was that mode. Fetches that
    fail for a known inmate carry the previous-good record forward marked
    ``detail_stale``; the list page remains authoritative for presence, so a
    failed detail fetch never drops a listed inmate.
    """
    done = 0
    n_detail_attempts = 0
    n_detail_named = 0
    n_detail_with_photo = 0
    failure_counts: Counter[str] = Counter()
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        futures = {
            pool.submit(
                _fetch_one,
                client,
                iid,
                previous,
                row_by_id.get(iid),
                waf_tracker=waf_tracker,
                photos_dir=photos_dir,
                waf_block_log_path=waf_block_log_path,
            ): iid
            for iid in to_fetch
        }
        for fut in as_completed(futures):
            # sweep-F6: bail out cleanly when we've burned the wall-clock
            # budget. The finally block still writes the partial roster
            # (clean_finish=True because we exited the try-body naturally).
            if time.monotonic() - t0 > SWEEP_WALLCLOCK_HARD_CAP_S:
                log.warning(
                    "sweep wall-clock cap reached at %d/%d details; finalizing",
                    done,
                    len(to_fetch),
                )
                # Drop queued fetches so the with-block exit doesn't run the
                # whole remaining queue after the cap fired.
                pool.shutdown(wait=False, cancel_futures=True)
                # Carry the never-fetched remainder forward from previous;
                # without this they vanish from current and the diff emits
                # synthetic release events for people still in custody.
                for pending_iid in to_fetch:
                    if pending_iid not in current and pending_iid in previous:
                        current[pending_iid] = previous[pending_iid].model_copy(update={"last_seen_utc": utcnow_iso()})
                break
            done += 1
            n_detail_attempts += 1
            iid = futures[fut]
            try:
                inm, detail_named, detail_had_photo, outcome = fut.result()
            except Exception as e:
                # One worker raising shouldn't terminate the pool - the
                # other detail fetches and the final write still run.
                # Count it as an attempt with neither name nor photo so
                # the watchdog reflects the failure, and record the mode
                # so the degraded guard sees it. Fall back to the
                # previous snapshot entry if we have one so a transient
                # detail-page error doesn't drop the inmate from current.
                log.warning("detail fetch worker raised: %s", e)
                failure_counts[DetailFailureMode.ERROR.value] += 1
                if iid in previous:
                    current[iid] = previous[iid].model_copy(
                        update={"last_seen_utc": utcnow_iso(), "detail_stale": True}
                    )
                continue
            if outcome.mode != DetailFailureMode.OK:
                failure_counts[outcome.mode.value] += 1
            if inm is not None:
                current[inm.inmate_number] = inm
            elif iid in previous:
                # _fetch_one returned None (detail fetch failed for a known
                # inmate). Without this fallback the inmate would silently
                # drop out of current.json for one cycle and re-appear on
                # the next; with it, we keep their previous record
                # (preserves cached photo and bio) until the next
                # successful fetch. Marked stale: the detail data was not
                # refreshed this cycle.
                current[iid] = previous[iid].model_copy(update={"last_seen_utc": utcnow_iso(), "detail_stale": True})
            else:
                # New inmate, no list row to build a minimal record from.
                # _fetch_one already logged; nothing to carry forward.
                log.warning(
                    "detail fetch failed for new id=%s with no list row; inmate omitted this cycle",
                    iid,
                )
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
                # snapshot until the next best-effort retry, rather
                # than persisting a degraded baseline.
                _maybe_checkpoint_partial(previous, current, done, len(to_fetch), current_path)
    elapsed_s = round(time.monotonic() - t0, 2)
    log.info(
        "detail phase: %d attempts, %d named, %d with photo, %d failed %s in %.1fs",
        n_detail_attempts,
        n_detail_named,
        n_detail_with_photo,
        sum(failure_counts.values()),
        dict(sorted(failure_counts.items())) if failure_counts else {},
        elapsed_s,
    )
    return n_detail_attempts, n_detail_named, n_detail_with_photo, failure_counts


def _anon_enrichment(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    offenses: dict[str, dict],
) -> dict[str, dict[str, str | None]]:
    """Build anon-feed enrichment for every inmate in either roster.

    Release events come from inmates present only in the previous roster, so
    enrichment cannot be derived from current alone. Current records take
    precedence when an inmate exists in both snapshots. ORC lookup is
    normalized so subsection suffixes such as 2925.11A resolve to 2925.11.
    Missing or unknown degrees are represented as None, not the internal
    question-mark sentinel.
    """
    combined = dict(previous)
    combined.update(current)
    enrichment: dict[str, dict[str, str | None]] = {}
    for inmate_number, inmate in combined.items():
        tier: str | None = None
        category: str | None = None
        if inmate.charges:
            first_charge = inmate.charges[0]
            code = orc.normalize_code((first_charge.orc_code or "").strip())
            if code:
                entry = orc.lookup(code, offenses)
                if isinstance(entry, dict):
                    raw_degree = entry.get("degree")
                    tier = raw_degree if raw_degree and raw_degree != orc.UNKNOWN else None
                    raw_title = entry.get("title")
                    category = raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else None
        enrichment[inmate_number] = {"tier": tier, "category": category}
    return enrichment


def _load_anon_offenses(path: Path) -> dict[str, dict]:
    """Load the ORC offense map for anon enrichment, failing closed on bad input."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    offenses = raw.get("offenses")
    if not isinstance(offenses, dict):
        return {}
    return {
        str(code): entry
        for code, entry in offenses.items()
        if isinstance(code, str) and isinstance(entry, dict)
    }


def _save_changelog_and_anon(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
    paths: SweepPaths,
) -> None:
    """Append diff events and refresh the anonymized rolling feed."""
    events = diff(previous, current)
    if not events:
        return
    log.info(
        "diff: %d events (%d booked, %d released, %d updated)",
        len(events),
        sum(1 for e in events if e.event == "booked"),
        sum(1 for e in events if e.event == "released"),
        sum(1 for e in events if e.event == "updated"),
    )
    changelog = None
    try:
        changelog = load_changelog(paths.changelog_path)
    except SnapshotCorruptError as e:
        # C-2: the changelog is unreadable; extending it would truncate the
        # full history to this cycles events. Leave the file untouched for
        # investigation and skip the changelog + anon-feed update this cycle.
        log.error(
            "refusing to update changelog: %s is corrupt (%s); leaving file untouched",
            paths.changelog_path,
            e,
        )
        return
    changelog.extend(events)
    save_changelog(paths.changelog_path, changelog)
    # Phase 11: maintain the PII-expiring append-only feed. Build enrichment
    # from both snapshots so released inmates retain their last-known tags.
    offenses = _load_anon_offenses(paths.orc_offenses_path)
    enrichment = _anon_enrichment(previous, current, offenses)
    save_anon_changelog(paths.anon_changelog_path, changelog, enrichment)

def run(
    surnames: list[str],
    *,
    max_surnames: int | None,
    refresh_known: bool,
    dry_run: bool,
    paths: SweepPaths | None = None,
) -> int:
    if paths is None:
        paths = SweepPaths()
    if max_surnames is not None:
        surnames = surnames[:max_surnames]
    sweep_id = uuid.uuid4().hex[:12]
    log.info(
        "sweep %s started (surnames=%d, max=%s, refresh=%s, dry_run=%s)",
        sweep_id,
        len(surnames),
        max_surnames,
        refresh_known,
        dry_run,
    )

    # Skip-gate: don't re-scrape if the roster DATA is still fresh. Key off the
    # generated_utc inside current.json, NOT the file mtime: actions/checkout
    # rewrites every file each run, so st_mtime is always "just now" on CI and an
    # mtime-based gate skipped the scrape every cycle (the 2026-05-19 roster
    # freeze). generated_utc is file content, so it survives the checkout.
    stale_h = roster_stale_hours(_prev_generated_utc(paths.current_path))
    if stale_h is not None and stale_h * 3600 < MIN_SWEEP_INTERVAL_S:
        log.info(
            "current.json data is %.0fs old (< %ds); skipping this cycle",
            stale_h * 3600,
            MIN_SWEEP_INTERVAL_S,
        )
        return 0

    try:
        previous = load_current_or_raise(paths.current_path)
    except SnapshotCorruptError as e:
        # Refuse the cycle: a missing-file bootstrap is fine, but a corrupted
        # current.json composed with the SWEEP_BOOTSTRAP_FLOOR semantics would
        # let any non-trivial sweep canonicalize a degraded roster. Keep the
        # last-good (broken) file in place so the operator can inspect it.
        log.error(
            "refusing sweep: data/current.json is unreadable (%s); last-good file kept in place for inspection",
            e,
        )
        log.error("sweep %s aborted (corrupt snapshot)", sweep_id)
        return 1
    log.info("loaded %d previously-known inmates", len(previous))

    # Read expunged inmate IDs from data/takedowns.json. Fail closed: a
    # malformed seal file must refuse loudly here, never silently build
    # without seals. store._load_takedowns enforces the same contract at the
    # save_current write boundary; loading it here too keeps the
    # previous/rows pre-filter consistent with the persisted snapshot.
    try:
        takedowns_set = _load_takedowns(paths.takedowns_path.parent)
    except SnapshotCorruptError as e:
        log.error("refusing sweep: %s", e)
        return 1

    if takedowns_set:
        original_prev_len = len(previous)
        previous = {iid: inm for iid, inm in previous.items() if iid not in takedowns_set}
        if len(previous) < original_prev_len:
            log.info("filtered out %d expunged inmates from previous database", original_prev_len - len(previous))

    current: dict[str, Inmate] = {}
    seen_ids: set[str] = set()
    detail_failures: Counter[str] = Counter()
    roster_ok = False
    # Set just before the try-block exits cleanly. The finally below uses this
    # flag to decide whether to compute a diff() and append to the changelog:
    # an interrupted sweep persists its partial roster snapshot (so the next
    # cycle anchors correctly) but MUST NOT emit a wave of synthetic
    # "released" events for ids it simply never reached.
    clean_finish = False

    try:
        with make_client() as client:
            rows, n_failed, status_counts, block_sample = _sweep_list(client, surnames)
            if takedowns_set:
                original_rows_len = len(rows)
                rows = [r for r in rows if r.inmate_number not in takedowns_set]
                if len(rows) < original_rows_len:
                    log.info("filtered out %d expunged inmates from sweep list", original_rows_len - len(rows))
            seen_ids = {r.inmate_number for r in rows}
            log.info(
                "list sweep returned %d unique inmate ids (%d/%d surname fetches failed)",
                len(seen_ids),
                n_failed,
                len(surnames),
            )

            if not sweep_looks_healthy(len(previous), len(seen_ids), len(surnames), n_failed):
                roster_ok = False
                log.error(
                    "list sweep looks degraded (prev=%d, seen=%d, %d/%d surname fetches failed) "
                    "- NOT writing the roster this cycle; keeping last-good data",
                    len(previous),
                    len(seen_ids),
                    n_failed,
                    len(surnames),
                )

                # The list-sweep guard thresholds (>10% surname errors or
                # roster collapsed below 50% of prior) are checked in
                # scraper/sweep_guards.sweep_looks_healthy. A prolonged freeze
                # is surfaced by the "Roster freeze alarm" step in sweep.yml
                # (roster_stale_hours), which runs every cycle regardless of
                # which guard path fired. Document the denial as durable
                # evidence (do-not-evade posture); never route around it.
                _record_block_evidence(
                    _BlockObservation(
                        prev_count=len(previous),
                        seen_count=len(seen_ids),
                        n_surnames=len(surnames),
                        n_failed=n_failed,
                        status_counts=status_counts,
                        block_sample=block_sample,
                    ),
                    paths,
                )
                _record_egress_evidence()
                log.error("sweep %s blocked (degraded list guard)", sweep_id)
                return 0

            roster_ok = True

            # Healthy sweep: if we were previously blocked, close the denial
            # period with a 'recovered' evidence record.
            _record_recovery_if_blocked(len(seen_ids), paths.waf_block_log_path)

            # Map inmate_id -> list row for name fallback when the detail
            # page heading is missing/unparseable, and for rebooking
            # detection (a changed admit date forces a detail refetch so a
            # rebooked inmate gets the newest booking photo).
            row_by_id = {r.inmate_number: r for r in rows}

            # Decide which detail pages to fetch.
            to_fetch = _plan_detail_fetch(seen_ids, previous, refresh_known, row_by_id)

            log.info("will fetch %d detail pages (refresh_known=%s)", len(to_fetch), refresh_known)

            # Carry forward records we already know about and aren't re-fetching.
            _carry_forward_known(current, seen_ids, previous, to_fetch)

            waf_tracker = WafBackoffTracker()
            n_detail_attempts, n_detail_named, n_detail_with_photo, detail_failures = _fetch_details(
                client=client,
                to_fetch=to_fetch,
                previous=previous,
                current=current,
                row_by_id=row_by_id,
                dry_run=dry_run,
                waf_tracker=waf_tracker,
                current_path=paths.current_path,
                photos_dir=paths.photos_dir,
                waf_block_log_path=paths.waf_block_log_path,
            )
            watchdog_ok = check_detail_watchdog(n_detail_attempts, n_detail_named, n_detail_with_photo)
            # Watchdog already logs WARN to stdout via check_detail_watchdog;
            # the hard-BLOCK path flips roster_ok so the finally block keeps
            # the last-good roster.
            if not watchdog_ok:
                roster_ok = False
            # Systemic detail failure must not report plain success. The
            # roster still writes (carry-forward keeps it correct and the
            # pipeline must continue), but the degradation is logged as an
            # error, annotated on the workflow run, and recorded as durable
            # evidence.
            if check_detail_degraded(n_detail_attempts, detail_failures):
                _record_detail_degraded(n_detail_attempts, detail_failures, paths.waf_block_log_path)
                print(
                    f"::error::detail fetch degraded: "
                    f"{sum(detail_failures.values())}/{n_detail_attempts} failed "
                    f"{dict(sorted(detail_failures.items()))}; roster kept via "
                    f"carry-forward, failed details marked stale",
                    flush=True,
                )

        clean_finish = True
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
        # Return the conventional SIGINT status instead of re-raising: the
        # finally block above already persisted the partial snapshot, and a
        # return code keeps the interruption observable (and testable) for
        # callers. sweep.yml marks the step failed either way.
        return INTERRUPTED_EXIT_CODE
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
            # A2: last_healthy_sweep_utc advances only on a fully healthy
            # sweep: the roster wrote cleanly AND detail failures stayed
            # below the degraded threshold. A degraded detail phase keeps
            # the previous clock value so the freshness signal stays honest.
            detail_healthy = not check_detail_degraded(n_detail_attempts, detail_failures)
            try:
                save_current(
                    paths.current_path,
                    current.values(),
                    last_healthy_sweep_utc=utcnow_iso() if (clean_finish and detail_healthy) else None,
                )
                save_ok = True
            except (OSError, SnapshotCorruptError) as e:
                # Disk full, permission denied, atomic-rename failure, or a
                # corrupt on-disk snapshot that C-1/C-2 fail-closed on. The
                # snapshot is unchanged on disk; just skip the prune to avoid
                # deleting photos for ids that never made it to current.json.
                log.error("save_current failed (%s); skipping changelog and prune", e)

            if save_ok and clean_finish:
                try:
                    _save_changelog_and_anon(previous, current, paths)
                except (OSError, SnapshotCorruptError) as e:
                    # C-7: a corrupt takedowns.json (raised by save_changelog's
                    # _load_takedowns) or an I/O failure must not escape the
                    # finally block and crash the sweep. The roster is already
                    # persisted above; leave the changelog and anon feed
                    # untouched for investigation and skip the append this
                    # cycle. The next healthy cycle diffs again, so no roster
                    # data is lost, only this cycle's changelog events.
                    log.error("skipping changelog/anon update: %s", e)
            elif save_ok:
                # Interrupted (or otherwise short-circuited) sweep: do not diff.
                # `current` is a partial subset of `previous`, so every unreached
                # id would synthesize a bogus `released` event and evict real
                # events from the rolling CHANGELOG_LIMIT=10000 window.
                log.warning("skipping diff/changelog append: sweep did not finish cleanly")
            # sweep-F5: only prune photos when save_current succeeded for this
            # cycle. A failed save leaves seen_ids ungrounded against any
            # persisted snapshot; pruning then could delete photos for ids
            # that were never written and that the next cycle still needs.
            if save_ok and seen_ids:
                prune_photos(paths.photos_dir, seen_ids)

    if dry_run:
        log.info("dry-run; not writing")
    log.info(
        "sweep %s completed (roster_ok=%s, clean=%s, seen=%d, current=%d, detail_failures=%s)",
        sweep_id,
        roster_ok,
        clean_finish,
        len(seen_ids),
        len(current),
        dict(sorted(detail_failures.items())) if detail_failures else {},
    )
    return 0


# Back-compat alias: prefer scraper.sweep_guards.check_detail_watchdog in new code.
_check_detail_watchdog = check_detail_watchdog


_SENSITIVE_HEADERS = frozenset({"cookie", "set-cookie", "authorization", "proxy-authorization"})


def _redact_headers(headers: httpx.Headers) -> dict:
    """Copy request/response headers for the evidence log, replacing the value
    of any session or credential header with a placeholder. The header's
    presence is preserved (forensically useful) but its token value never
    reaches the public data/waf_block_log.json: a WAF can set a clearance
    cookie that the client's cookie jar echoes back, and a proxy could add an
    auth header."""
    return {k: ("[redacted]" if k.lower() in _SENSITIVE_HEADERS else v) for k, v in headers.items()}


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
    body_text = re.sub(r"[0-9a-fA-F]{32,}", "[redacted-token]", body_text)
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
    if list_response_looks_blocked(resp.text, rows):
        log.warning(
            "list fetch for surname=%s looks WAF-blocked (HTTP %d, %d bytes, 0 rows)",
            surname,
            resp.status_code,
            len(resp.text),
        )
        return None, resp.status_code, _forensic_sample(resp)
    return rows, None, None


def _sweep_list(client: HcsoClient, surnames: list[str]) -> tuple[list[ListRow], int, dict[str, int], dict | None]:
    """Parallel surname search across the configured list.

    Returns ``(rows, n_failed, status_counts, block_sample)`` - ``n_failed`` is
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
        len(seen),
        failed,
        len(surnames),
        elapsed_s,
    )
    return aggregated, failed, status_counts, block_sample


def _fetch_one(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    list_row: ListRow | None = None,
    *,
    waf_tracker: WafBackoffTracker,
    photos_dir: Path | None = None,
    waf_block_log_path: Path | None = None,
) -> tuple[Inmate | None, bool, bool, DetailOutcome]:
    """Fetch and parse one detail page.

    Returns ``(inmate, detail_named, detail_had_photo, outcome)`` - the two
    booleans reflect what the *detail parser* produced, before any list-row
    name fallback or disk-cached photo carry-forward is applied, so callers
    can measure detail-page health distinct from the list-side path.
    ``outcome`` is the classified fetch result (``DetailFailureMode.OK`` on
    success); callers use it for per-mode failure accounting and staleness
    marking.

    List-page authority: when the detail fetch fails for an inmate the list
    page saw, the inmate stays on the roster. Known inmates are carried
    forward by the caller (marked stale); new inmates get a minimal record
    built from the list row (marked stale, never successfully fetched).

    ``waf_tracker`` is required (keyword-only): the WAF-block streak is shared
    across the worker pool, so a caller that omitted it would silently get a
    throwaway tracker and disable cross-call backoff.
    """
    if photos_dir is None:
        photos_dir = PHOTOS_DIR
    inm, photo_bytes, photo_url, outcome = _fetch_detail_with_retry(
        client, inmate_id, previous, waf_tracker, waf_block_log_path=waf_block_log_path
    )
    if inm is None:
        if inmate_id in previous:
            # Known inmate: the caller carries forward the previous-good
            # record (marked stale). Returning None signals that path.
            return None, False, False, outcome
        if list_row is not None:
            # New inmate: the list saw them, so they are in custody even
            # though the detail page failed. Build the minimal record from
            # the list row rather than dropping them for a cycle.
            return _minimal_inmate_from_list_row(list_row), False, False, outcome
        log.warning(
            "detail fetch failed for id=%s with no list row to fall back on; inmate omitted this cycle",
            inmate_id,
        )
        return None, False, False, outcome
    detail_named = bool(inm.last_name or inm.first_name)
    detail_had_photo = bool(photo_bytes or photo_url)

    photo_bytes = _fetch_photo_bytes_from_url(client, inmate_id, photo_url, photo_bytes)
    _apply_list_row_fallback(inm, list_row)
    _attach_photo_filename(inm, photo_bytes, photos_dir)
    _set_seen_timestamps(inm, inmate_id, previous)
    inm.last_detail_fetch_utc = utcnow_iso()
    inm.detail_stale = False
    return inm, detail_named, detail_had_photo, outcome


def _minimal_inmate_from_list_row(row: ListRow) -> Inmate:
    """Build a presence record for a new inmate whose detail page failed.

    The list page is authoritative for custody: a failed detail fetch must
    not drop a listed inmate from the roster. The record carries the list
    row's name and admit date, is marked stale, and records that its detail
    was never successfully fetched. ``booking_date`` is assigned
    post-construction (mirroring ``_apply_list_row_fallback``) so an
    unexpected admit-date shape cannot raise and drop the inmate.
    """
    now = utcnow_iso()
    inm = Inmate(
        inmate_number=row.inmate_number,
        last_name=row.last_name,
        first_name=row.first_name,
        first_seen_utc=now,
        last_seen_utc=now,
        last_detail_fetch_utc="",
        detail_stale=True,
    )
    if row.admit_date:
        inm.booking_date = row.admit_date
    return inm


# Detail-fetch modes that get one bounded retry with WAF backoff: the body
# was block-shaped (or suspiciously close), so the retry waits out a
# transient WAF window with the same identity, IP, and crawl delay. This is
# explicitly not evasion: no header, proxy, or session rotation.
_RETRYABLE_BLOCK_MODES = frozenset(
    {
        DetailFailureMode.WAF_BLOCK,
        DetailFailureMode.ZERO_BYTE,
        DetailFailureMode.TRUNCATED,
    }
)


def _fetch_detail_with_retry(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    waf_tracker: WafBackoffTracker,
    *,
    waf_block_log_path: Path | None = None,
) -> tuple[Inmate | None, bytes | None, str | None, DetailOutcome]:
    """Fetch one detail page with per-mode bounded retries.

    Every fetch ends classified as a :class:`DetailFailureMode`. Retry policy:
    block-shaped bodies (WAF block, zero-byte, truncated) get one retry with
    exponential WAF backoff; transient network errors (timeout, connection
    error) get one immediate retry (the client's crawl delay still spaces
    requests); HTTP errors are not retried at this level (the client already
    retried 5xx/429 once, and 404/redirect will not heal on retry). No retry
    path changes identity, IP, headers, or proxy: bounded, non-evasive.

    Returns ``(inmate, photo_bytes, photo_url, outcome)``. On any final
    failure the inmate is None and the caller applies the carry-forward /
    list-row fallback; the outcome drives per-mode accounting.
    """
    # Prefer get_response so the outcome can record the HTTP status and the
    # redirect check can see the final URL. Fall back to plain get() for
    # clients (notably the test fakes) that only implement the text-returning
    # method.
    get_response = getattr(client, "get_response", None)
    inm: Inmate | None = None
    photo_bytes: bytes | None = None
    photo_url: str | None = None
    html = ""
    http_status: int | None = None
    final_path: str | None = None
    outcome = DetailOutcome(DetailFailureMode.ERROR, None, 0)

    for attempt in range(2):
        try:
            if get_response is not None:
                response = get_response(DETAIL_PATH, params={"id": inmate_id})
                html = response.text
                http_status = response.status_code
                try:
                    final_path = urlparse(str(response.url)).path or None
                except Exception:
                    final_path = None
            else:
                html = client.get(DETAIL_PATH, params={"id": inmate_id})
                http_status = None
                final_path = None
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else None
            mode = classify_http_status_error(status)
            outcome = DetailOutcome(mode, status, 0)
            log.warning("detail fetch HTTP %s for id=%s: %s", status, inmate_id, e)
            _record_detail_page_block(
                inmate_id=inmate_id,
                http_status=status,
                html="",
                mode=mode,
                waf_block_log_path=waf_block_log_path,
            )
            break
        except httpx.TimeoutException as e:
            outcome = DetailOutcome(DetailFailureMode.TIMEOUT, None, 0)
            log.warning("detail fetch timeout for id=%s: %s", inmate_id, e)
            if attempt == 0:
                continue  # one bounded retry; transient network, not a WAF signal
            _record_detail_page_block(
                inmate_id=inmate_id,
                http_status=None,
                html="",
                mode=DetailFailureMode.TIMEOUT,
                waf_block_log_path=waf_block_log_path,
            )
            break
        except httpx.HTTPError as e:
            outcome = DetailOutcome(DetailFailureMode.CONNECTION_ERROR, None, 0)
            log.warning("detail fetch connection error for id=%s: %s", inmate_id, e)
            if attempt == 0:
                continue  # one bounded retry
            _record_detail_page_block(
                inmate_id=inmate_id,
                http_status=None,
                html="",
                mode=DetailFailureMode.CONNECTION_ERROR,
                waf_block_log_path=waf_block_log_path,
            )
            break
        except Exception as e:
            outcome = DetailOutcome(DetailFailureMode.ERROR, None, 0)
            log.warning("detail fetch failed for id=%s: %s", inmate_id, e)
            _record_detail_page_block(
                inmate_id=inmate_id,
                http_status=None,
                html="",
                mode=DetailFailureMode.ERROR,
                waf_block_log_path=waf_block_log_path,
            )
            break

        inm, photo_bytes, photo_url = parse_detail_page(html, inmate_id, record_evidence=True)
        mode = classify_detail_html(
            html,
            inm,
            photo_bytes,
            photo_url,
            final_path=final_path,
            detail_path=DETAIL_PATH,
        )
        outcome = DetailOutcome(mode, http_status, len(html))
        if mode == DetailFailureMode.OK:
            waf_tracker.clear()
            break
        if mode in _RETRYABLE_BLOCK_MODES:
            streak, backoff = waf_tracker.observe()
            if attempt == 0:
                log.warning(
                    "%s response for id=%s (%d bytes, streak=%d); sleeping %.1fs and retrying once",
                    mode.value,
                    inmate_id,
                    len(html),
                    streak,
                    backoff,
                )
                time.sleep(backoff)
                continue
            # Second attempt also block-shaped. Sleep the latest backoff to
            # slow the worker, record the evidence, and return the failure.
            log.warning(
                "%s response for id=%s (%d bytes, streak=%d); retry also failed, returning without overwriting",
                mode.value,
                inmate_id,
                len(html),
                streak,
            )
            _record_detail_page_block(
                inmate_id=inmate_id,
                http_status=http_status,
                html=html,
                mode=mode,
                waf_block_log_path=waf_block_log_path,
            )
            time.sleep(backoff)
            break
        # Any other non-OK mode (redirect, and any future non-retryable
        # classification): observed and classified, not retried. Still
        # recorded: a 404/redirect on a listed inmate is source-side
        # evidence, and the failure_mode field keeps the taxonomy queryable.
        log.warning(
            "detail fetch for id=%s classified as %s (HTTP %s, %d bytes); not retrying",
            inmate_id,
            mode.value,
            http_status,
            len(html),
        )
        _record_detail_page_block(
            inmate_id=inmate_id,
            http_status=http_status,
            html=html,
            mode=mode,
            waf_block_log_path=waf_block_log_path,
        )
        break

    if outcome.mode != DetailFailureMode.OK:
        return None, None, None, outcome
    # The loop always runs iteration 0, which either breaks at an exception
    # guard (outcome != OK, returned above) or assigns inm from
    # parse_detail_page (which always yields an Inmate). The assert narrows
    # Inmate | None for the type checker and documents the invariant without
    # adding a runtime branch.
    assert inm is not None
    return inm, photo_bytes, photo_url, outcome


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


def _attach_photo_filename(inm: Inmate, photo_bytes: bytes | None, photos_dir: Path) -> None:
    photo_path = photos_dir / f"{inm.inmate_number}.jpg"
    # Defense-in-depth: even though the model validator enforces digits-only,
    # assert the filename is safe to prevent path traversal if the validator
    # is ever relaxed.
    if ".." in photo_path.name or "/" in photo_path.name or "\\" in photo_path.name:
        raise ValueError(f"unsafe photo filename: {photo_path.name!r}")

    try:
        resolved_photos_dir = photos_dir.resolve()
        resolved_photo_path = photo_path.resolve()
    except Exception as e:
        raise ValueError(f"could not resolve photo path: {e}") from e

    try:
        resolved_photo_path.relative_to(resolved_photos_dir)
    except ValueError as e:
        raise ValueError(
            f"unsafe photo path traversal: {photo_path} (resolved: {resolved_photo_path}) is outside PHOTOS_DIR ({resolved_photos_dir})"
        ) from e
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
    return [line.strip().upper() for line in text.splitlines() if line.strip() and not line.startswith("#")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one JCStream sweep")
    parser.add_argument("--surnames", default="data/surnames.txt", type=Path)
    parser.add_argument("--max-surnames", type=int, default=None, help="cap the surname list for quick smoke tests")
    parser.add_argument(
        "--refresh-known", action="store_true", help="re-fetch detail pages even for already-known inmates"
    )
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
