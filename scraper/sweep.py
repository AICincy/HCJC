"""Sweep orchestrator.

Each invocation:

  1. Iterates the configured surnames; for each, GETs the list page and parses
     rows currently in HCSO custody.
  2. Fetches the detail page for any inmate id we don't already know about, or
     whose record is older than ``--max-detail-age-hours``.
  3. Extracts + downscales the inline booking photo.
  4. Writes data/current.json and appends to data/changelog.json.
  5. Removes photos belonging to released inmates.

Designed to fit a ~25-minute budget at Crawl-delay: 10s, so it can run as a
30-minute cron in GitHub Actions.
"""

from __future__ import annotations

import argparse
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


# ===== Sentry telemetry (error monitoring only) =====
# The sweep is the only path that should ship telemetry: the build and the
# test suite stay offline. Initialization is gated on JCSTREAM_SENTRY_DSN so
# local dev and any Actions run without the secret keep working unchanged
# (sentry_sdk's capture_* APIs are no-ops when the SDK was never initialized,
# so the instrumentation points below are safe to call unconditionally).
def _init_sentry() -> None:
    """Initialize sentry-sdk if JCSTREAM_SENTRY_DSN is set; otherwise no-op.

    Error monitoring only: traces_sample_rate=0 means no performance/tracing
    spans are emitted, and no profiling / session-replay integrations are
    enabled. The SDK falls through silently when the env var is absent so the
    GH Actions runner without the secret keeps exiting 0 on a healthy sweep.
    """
    dsn = os.environ.get("JCSTREAM_SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk  # noqa: WPS433 (intentional optional dep)
    except ImportError:
        log.info("JCSTREAM_SENTRY_DSN is set but sentry-sdk is not installed; skipping")
        return
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.0,
        # Don't ship local var values that could include inmate names/photos.
        send_default_pii=False,
    )
    log.info("sentry-sdk initialized for sweep telemetry")


def _sentry_capture_message(message: str, level: str = "info", **tags) -> None:
    """Capture a Sentry message. Safe to call when the SDK isn't initialized."""
    try:
        import sentry_sdk
    except ImportError:
        return
    with sentry_sdk.push_scope() as scope:
        for k, v in tags.items():
            scope.set_tag(k, v)
        sentry_sdk.capture_message(message, level=level)


def _sentry_capture_exception(exc: BaseException) -> None:
    """Capture an exception. Safe to call when the SDK isn't initialized."""
    try:
        import sentry_sdk
    except ImportError:
        return
    sentry_sdk.capture_exception(exc)


def _sentry_set_tag(key: str, value: str) -> None:
    """Set a tag on the current Sentry isolation scope.

    Sentry 2.x maintains a per-task isolation scope by default, so calling
    this inside a worker callback tags only that worker's events. No-op
    when the SDK isn't installed/initialized.
    """
    try:
        import sentry_sdk
    except ImportError:
        return
    sentry_sdk.set_tag(key, value)

SEARCH_PATH = "/justice-center-services/inmate-search/"
DETAIL_PATH = "/justice-center-services/inmate-search/inmate-detail/"
PHOTOS_DIR = Path("data/photos")
CURRENT_PATH = Path("data/current.json")
CHANGELOG_PATH = Path("data/changelog.json")

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


def run(
    surnames: list[str],
    *,
    max_surnames: int | None,
    refresh_known: bool,
    dry_run: bool,
) -> int:
    if max_surnames is not None:
        surnames = surnames[:max_surnames]

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
                # guard checks. Both can fire on the same cycle; emit both so
                # the alert payload accurately reflects what tripped (see
                # scraper/sweep_guards.sweep_looks_healthy for the thresholds).
                # No PII: only aggregate counts are tagged.
                failed_fraction = (n_failed / len(surnames)) if surnames else 0.0
                if failed_fraction > SWEEP_MAX_FAILED_FRACTION and len(previous) >= SWEEP_BOOTSTRAP_FLOOR:
                    _sentry_capture_message(
                        "sweep.degraded.surname_errors",
                        level="warning",
                        prev_count=str(len(previous)),
                        seen_count=str(len(seen_ids)),
                        n_failed=str(n_failed),
                        n_surnames=str(len(surnames)),
                        failed_fraction=f"{failed_fraction:.3f}",
                    )
                if (
                    len(previous) >= SWEEP_BOOTSTRAP_FLOOR
                    and len(seen_ids) < SWEEP_MIN_ROSTER_FRACTION * len(previous)
                ):
                    roster_fraction = (len(seen_ids) / len(previous)) if previous else 0.0
                    _sentry_capture_message(
                        "sweep.degraded.roster_floor",
                        level="warning",
                        prev_count=str(len(previous)),
                        seen_count=str(len(seen_ids)),
                        roster_fraction=f"{roster_fraction:.3f}",
                    )
                return 0

            # Decide which detail pages to fetch.
            to_fetch: list[str] = []
            for inmate_id in sorted(seen_ids):
                if inmate_id not in previous:
                    to_fetch.append(inmate_id)
                elif refresh_known:
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
                    try:
                        inm, detail_named, detail_had_photo = fut.result()
                    except Exception as e:
                        # One worker raising shouldn't terminate the pool - the
                        # other detail fetches and the final write still run.
                        # Count it as an attempt with neither name nor photo so
                        # the watchdog reflects the failure.
                        log.warning("detail fetch worker raised: %s", e)
                        continue
                    if inm is not None:
                        current[inm.inmate_number] = inm
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
                        # snapshot until the natural 30-minute retry, rather
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
            # Surface the watchdog to Sentry whenever it does anything visible:
            # the hard-BLOCK path (watchdog_ok=False) AND the WARN-only path
            # when the soft floors trip at sample size. The WARN-only path
            # is informational but worth knowing about; the BLOCK path is the
            # one that flips roster_ok and keeps the last-good roster.
            if not watchdog_ok:
                _sentry_capture_message(
                    "sweep.detail_watchdog_tripped",
                    level="warning",
                    blocked="true",
                    attempts=str(n_detail_attempts),
                    named=str(n_detail_named),
                    with_photo=str(n_detail_with_photo),
                )
                roster_ok = False
            elif n_detail_attempts >= DETAIL_WATCHDOG_MIN_SAMPLE:
                name_rate = n_detail_named / n_detail_attempts
                photo_rate = n_detail_with_photo / n_detail_attempts
                if name_rate < DETAIL_WATCHDOG_NAME_FLOOR or photo_rate < DETAIL_WATCHDOG_PHOTO_FLOOR:
                    _sentry_capture_message(
                        "sweep.detail_watchdog_tripped",
                        level="warning",
                        blocked="false",
                        attempts=str(n_detail_attempts),
                        named=str(n_detail_named),
                        with_photo=str(n_detail_with_photo),
                        name_rate=f"{name_rate:.3f}",
                        photo_rate=f"{photo_rate:.3f}",
                    )
        clean_finish = True
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
    except Exception as e:
        # Anything else escaping the sweep body is unexpected: ship it to
        # Sentry so we can see it, then re-raise. `roster_ok` stays True only
        # if we already cleared the list-sweep guard; the `finally` will use
        # that to decide whether to persist the partial roster.
        log.exception("unhandled exception in sweep main loop")
        _sentry_capture_exception(e)
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
    skipped = False
    if photos_dir.exists():
        existing = list(photos_dir.glob("*.jpg"))
        if existing:
            doomed = [f for f in existing if f.stem not in active_ids]
            if doomed and len(doomed) / len(existing) > PHOTO_PRUNE_MAX_FRACTION:
                skipped = True
                _sentry_capture_message(
                    "sweep.photo_prune.skipped",
                    level="info",
                    doomed=str(len(doomed)),
                    existing=str(len(existing)),
                    fraction=f"{len(doomed) / len(existing):.3f}",
                )
    # prune_photos itself logs and bails on its own (same threshold check); we
    # always call it so the actual delete behavior stays owned by sweep_guards.
    prune_photos(photos_dir, active_ids)
    # `skipped` is intentionally unused beyond the capture above — left as a
    # readable variable for future maintainers.
    del skipped


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
        # Tag the per-surname scope so any captured exception in this worker
        # carries the letter context (HCSO's list page is one-letter-at-a-time,
        # so the letter is enough to triage a regression without leaking PII).
        _sentry_set_tag("sweep.surname_letter", surname)
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
    inm, photo_bytes = parse_detail_page(html, inmate_id)
    detail_named = bool(inm.last_name or inm.first_name)
    detail_had_photo = bool(photo_bytes)

    # Fall back to the list-row name when the detail page heading isn't
    # parseable. The list page reliably renders Last/First as separate cells.
    if list_row is not None:
        if not inm.last_name and list_row.last_name:
            inm.last_name = list_row.last_name
        if not inm.first_name and list_row.first_name:
            inm.first_name = list_row.first_name
        if not inm.booking_date and list_row.admit_date:
            inm.booking_date = list_row.admit_date

    photo_path = PHOTOS_DIR / f"{inm.inmate_number}.jpg"
    if photo_bytes:
        if downscale_and_save(photo_bytes, photo_path):
            inm.photo_filename = photo_path.name
    elif photo_path.exists():
        # We've previously stored a photo for this person; keep it.
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

    # Telemetry is initialized at the CLI entry, not at import time, so
    # ``python -m scraper.sweep --dry-run`` from a contributor's laptop and
    # the pytest suite (which never reaches main()) both stay offline by
    # construction. See _init_sentry() for the env-gating contract.
    _init_sentry()

    surnames = _read_surnames(args.surnames)
    log.info("loaded %d surnames from %s", len(surnames), args.surnames)
    started = time.monotonic()
    try:
        rc = run(
            surnames,
            max_surnames=args.max_surnames,
            refresh_known=args.refresh_known,
            dry_run=args.dry_run,
        )
    except Exception as e:
        # Last-resort net for an exception that escaped run()'s own try/except
        # (e.g. raised during `load_current_or_raise` before the main try-block).
        _sentry_capture_exception(e)
        raise
    log.info("sweep finished in %.1fs (rc=%d)", time.monotonic() - started, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
