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
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .client import DEFAULT_CONCURRENCY, HcsoClient, make_client
from .models import Inmate, ListRow, utcnow_iso
from .parsers import parse_detail_page, parse_list_page
from .photos import downscale_and_save
from .store import (
    SnapshotCorruptError,
    diff,
    load_changelog,
    load_current_or_raise,
    save_changelog,
    save_anon_changelog,
    save_current,
)
from .sweep_guards import (
    DETAIL_WATCHDOG_MIN_SAMPLE,
    DETAIL_WATCHDOG_NAME_FLOOR,
    DETAIL_WATCHDOG_PHOTO_FLOOR,
    PHOTO_PRUNE_MAX_FRACTION,
    SWEEP_BOOTSTRAP_FLOOR,
    SWEEP_MAX_FAILED_FRACTION,
    SWEEP_MIN_ROSTER_FRACTION,
    check_detail_watchdog,
    prune_photos,
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


# Back-compat alias: prefer scraper.sweep_guards.sweep_looks_healthy in new code.
_sweep_looks_healthy = sweep_looks_healthy


MIN_SWEEP_INTERVAL_S = 20 * 60  # 20 minutes


def run(
    surnames: list[str],
    *,
    max_surnames: int | None,
    refresh_known: bool,
    dry_run: bool,
) -> int:
    if max_surnames is not None:
        surnames = surnames[:max_surnames]

    if CURRENT_PATH.exists():
        age_s = time.time() - CURRENT_PATH.stat().st_mtime
        if age_s < MIN_SWEEP_INTERVAL_S:
            log.info(
                "current.json is %.0fs old (< %ds); skipping this cycle",
                age_s, MIN_SWEEP_INTERVAL_S,
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
            rows, n_failed = _sweep_list(client, surnames)
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
                # Emit a Sentry alert distinguishing the two failure modes the
                # guard checks (scraper/sweep_guards.sweep_looks_healthy for
                # the thresholds). Both are already logged via `log.warning`
                # in sweep_guards; no further telemetry needed.
                return 0

            # Decide which detail pages to fetch.
            to_fetch: list[str] = []
            for inmate_id in sorted(seen_ids):
                if inmate_id not in previous:
                    to_fetch.append(inmate_id)
                elif refresh_known:
                    to_fetch.append(inmate_id)
                elif not previous[inmate_id].photo_filename:
                    to_fetch.append(inmate_id)

            log.info("will fetch %d detail pages (refresh_known=%s)", len(to_fetch), refresh_known)

            # Carry forward records we already know about and aren't re-fetching.
            for inmate_id in seen_ids:
                if inmate_id in previous and inmate_id not in to_fetch:
                    carry = previous[inmate_id].model_copy(update={"last_seen_utc": utcnow_iso()})
                    current[inmate_id] = carry

            # Map inmate_id -> list row for name fallback when the detail
            # page heading is missing/unparseable.
            row_by_id = {r.inmate_number: r for r in rows}
            done = 0
            n_detail_attempts = 0
            n_detail_named = 0
            n_detail_with_photo = 0
            sweep_started = time.monotonic()
            with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
                futures = {
                    pool.submit(_fetch_one, client, iid, previous, row_by_id.get(iid)): iid
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
                        if (
                            len(previous) < SWEEP_BOOTSTRAP_FLOOR
                            or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous)
                        ):
                            save_current(CURRENT_PATH, current.values())
                            log.info("checkpoint: %d/%d details fetched, %d inmates",
                                     done, len(to_fetch), len(current))
                        else:
                            log.info(
                                "checkpoint skipped at %d/%d details: in-memory "
                                "roster %d below %.0f%% of previous %d",
                                done, len(to_fetch), len(current),
                                100 * SWEEP_MIN_ROSTER_FRACTION, len(previous),
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
                events = diff(previous, current)
                if events:
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
    return 0


# Back-compat alias: prefer scraper.sweep_guards.check_detail_watchdog in new code.
_check_detail_watchdog = check_detail_watchdog


def _prune_and_report(photos_dir: Path, active_ids: set[str]) -> None:
    """Run ``prune_photos`` and emit a Sentry breadcrumb when it skips.

    The skip path in ``sweep_guards.prune_photos`` is one of the silent-staleness
    pre-conditions: the prune passes but the on-disk photo set drifts out of
    sync with the roster. The check below is a *read* against the same
    filesystem the prune is about to inspect, so it can't lie about what the
    prune would have done. We keep the prune logic untouched and just report.
    """
    # prune_photos itself logs (log.warning) and bails on its own when the
    # delete fraction would exceed PHOTO_PRUNE_MAX_FRACTION; we always call
    # it so the actual delete behavior stays owned by sweep_guards.
    prune_photos(photos_dir, active_ids)


def _sweep_list(client: HcsoClient, surnames: list[str]) -> tuple[list[ListRow], int]:
    """Parallel surname search across the configured list.

    Returns ``(rows, n_failed)`` — ``n_failed`` is how many surname fetches
    raised (distinct from a surname that legitimately returned zero rows), so
    the caller can decide whether the roster is trustworthy this cycle.
    """
    aggregated: list[ListRow] = []
    seen: set[str] = set()

    # sweep-F8: fetch_one MUST swallow every exception and return None on
    # failure. pool.map below surfaces the first worker raise when iterated,
    # which would truncate the surname sweep below SWEEP_MAX_FAILED_FRACTION
    # and look like a healthy partial sweep. If you ever change fetch_one to
    # re-raise a typed error, switch to ThreadPoolExecutor + as_completed
    # (see scraper/sweep.py:run for the pattern) before merging.
    def fetch_one(surname: str) -> list[ListRow] | None:
        try:
            html = client.get(SEARCH_PATH, params={"last": surname})
            return parse_list_page(html)
        except Exception as e:
            log.warning("list fetch failed for surname=%s: %s", surname, e)
            return None

    failed = 0
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        for rows in pool.map(fetch_one, surnames):
            if rows is None:
                failed += 1
                continue
            for r in rows:
                if r.inmate_number not in seen:
                    seen.add(r.inmate_number)
                    aggregated.append(r)
    return aggregated, failed


def _fetch_one(
    client: HcsoClient,
    inmate_id: str,
    previous: dict[str, Inmate],
    list_row: ListRow | None = None,
) -> tuple[Inmate | None, bool, bool]:
    """Fetch and parse one detail page.

    Returns ``(inmate, detail_named, detail_had_photo)`` — the two booleans
    reflect what the *detail parser* produced, before any list-row name
    fallback or disk-cached photo carry-forward is applied, so callers can
    measure detail-page health distinct from the list-side path.
    """
    try:
        html = client.get(DETAIL_PATH, params={"id": inmate_id})
    except Exception as e:
        log.warning("detail fetch failed for id=%s: %s", inmate_id, e)
        return None, False, False
    inm, photo_bytes, photo_url = parse_detail_page(html, inmate_id)
    # WAF / geo-block check. Per the 2026-05-19 Claude.ai HCSO verification,
    # valid inmate-detail pages from HCSO are 91-230 KB. HCSO's WAF returns
    # truncated/blocked responses well under 5 KB to automated callers, and
    # the parser silently produces an empty Inmate from them. When the page
    # is tiny AND the parser found nothing AND we already have this inmate
    # in `previous`, return None so the carry-forward path in `run()`
    # preserves the previous-good record (cached photo, prior bio + charges)
    # instead of overwriting it with empty data this cycle. For NEW inmates
    # (not in previous) we fall through so the list_row fallback can still
    # rescue an interstitial response into a minimal Inmate; better a name
    # than nothing for a newly-booked record.
    if (
        len(html) < 5000
        and not inm.last_name
        and not inm.first_name
        and not inm.charges
        and not photo_bytes
        and not photo_url
        and inmate_id in previous
    ):
        log.warning(
            "detail page for id=%s parsed to empty Inmate (%d bytes); "
            "treating as WAF/geo-block, returning None to trigger carry-forward",
            inmate_id, len(html),
        )
        return None, False, False
    detail_named = bool(inm.last_name or inm.first_name)
    detail_had_photo = bool(photo_bytes or photo_url)

    # If the page provided a direct photo URL, fetch it (more reliable than
    # base64). Fall back to inline bytes if the URL fetch fails.
    if photo_url and not photo_bytes:
        try:
            photo_bytes = client.get_bytes(photo_url)
        except Exception as e:
            log.warning("photo URL fetch failed for id=%s url=%s: %s", inmate_id, photo_url, e)

    if list_row is not None:
        if not inm.last_name and list_row.last_name:
            inm.last_name = list_row.last_name
        if not inm.first_name and list_row.first_name:
            inm.first_name = list_row.first_name
        if not inm.booking_date and list_row.admit_date:
            inm.booking_date = list_row.admit_date

    photo_path = PHOTOS_DIR / f"{inm.inmate_number}.jpg"
    # Save fresh bytes if we got them AND they decoded; otherwise fall through
    # to the disk-cached photo from a prior successful sweep. Previously the
    # second branch was an `elif`, which meant a corrupt-bytes failure on one
    # cycle would discard a previously-good cached photo from the snapshot.
    if photo_bytes and downscale_and_save(photo_bytes, photo_path):
        inm.photo_filename = photo_path.name
    elif photo_path.exists():
        inm.photo_filename = photo_path.name

    inm.first_seen_utc = (
        previous[inmate_id].first_seen_utc
        if inmate_id in previous and previous[inmate_id].first_seen_utc
        else utcnow_iso()
    )
    inm.last_seen_utc = utcnow_iso()
    return inm, detail_named, detail_had_photo


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
