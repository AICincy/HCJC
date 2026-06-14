"""Sweep orchestrator package.

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
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..client import make_client
from ..models import Inmate, utcnow_iso
from ..store import (
    WAF_BLOCK_LOG_PATH,
    SnapshotCorruptError,
    diff,
    load_changelog,
    load_current_or_raise,
    save_anon_changelog,
    save_changelog,
    save_current,
)
from ..sweep_guards import (
    SWEEP_BOOTSTRAP_FLOOR,
    SWEEP_MIN_ROSTER_FRACTION,
    check_detail_watchdog,
    prune_photos,
    roster_stale_hours,
    sweep_looks_healthy,
)

# Import modularized components to expose them at the scraper.sweep namespace.
# This preserves compatibility with the test suite and external imports/mocks.
from ..photos import downscale_and_save
from .evidence import (
    WafBackoffTracker,
    _BlockObservation,
    _record_block_evidence,
    _record_recovery_if_blocked,
    _record_egress_evidence,
    _prev_generated_utc,
)
from .list import (
    _sweep_list,
    _fetch_list_page,
    _redact_headers,
    _forensic_sample,
)
from .details import (
    _fetch_details,
    _fetch_one,
    _fetch_detail_with_retry,
    _fetch_photo_bytes_from_url,
    _apply_list_row_fallback,
    _attach_photo_filename,
    _set_seen_timestamps,
    _plan_detail_fetch,
    _carry_forward_known,
)

log = logging.getLogger("jcstream.sweep")

SEARCH_PATH = "/justice-center-services/inmate-search/"
DETAIL_PATH = "/justice-center-services/inmate-search/inmate-detail/"
PHOTOS_DIR = Path("data/photos")
CURRENT_PATH = Path("data/current.json")
CHANGELOG_PATH = Path("data/changelog.json")
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


SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60
MIN_SWEEP_INTERVAL_S = 20 * 60  # 20 minutes

# Back-compat aliases: prefer scraper.sweep_guards in new code.
_sweep_looks_healthy = sweep_looks_healthy
_check_detail_watchdog = check_detail_watchdog


def _prune_photos(active_ids: set[str]) -> None:
    prune_photos(PHOTOS_DIR, active_ids)


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
    changelog = load_changelog(paths.changelog_path)
    changelog.extend(events)
    save_changelog(paths.changelog_path, changelog)
    enrichment: dict[str, dict] = {}
    offenses_path = paths.orc_offenses_path
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
            ent = offenses.get("offenses", {}).get(code) if isinstance(offenses, dict) else None
            if isinstance(ent, dict):
                tier = ent.get("degree")
                category = ent.get("title")
        enrichment[inm.inmate_number] = {
            "tier": tier,
            "category": category,
        }
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
        log.error(
            "refusing sweep: data/current.json is unreadable (%s); last-good file kept in place for inspection",
            e,
        )
        log.error("sweep %s aborted (corrupt snapshot)", sweep_id)
        return 1
    log.info("loaded %d previously-known inmates", len(previous))

    takedowns_path = paths.takedowns_path
    takedowns_set = set()
    if takedowns_path.exists():
        try:
            t_data = json.loads(takedowns_path.read_text(encoding="utf-8"))
            if isinstance(t_data, list):
                takedowns_set = {str(x) for x in t_data}
            elif isinstance(t_data, dict):
                takedowns_set = {str(x) for x in t_data.keys()}
        except (json.JSONDecodeError, OSError) as e:
            log.warning("failed to load data/takedowns.json (non-fatal): %s", e)

    if takedowns_set:
        original_prev_len = len(previous)
        previous = {iid: inm for iid, inm in previous.items() if iid not in takedowns_set}
        if len(previous) < original_prev_len:
            log.info("filtered out %d expunged inmates from previous database", original_prev_len - len(previous))

    current: dict[str, Inmate] = {}
    seen_ids: set[str] = set()
    roster_ok = False
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

            _record_recovery_if_blocked(len(seen_ids), paths.waf_block_log_path)

            to_fetch = _plan_detail_fetch(seen_ids, previous, refresh_known)

            log.info("will fetch %d detail pages (refresh_known=%s)", len(to_fetch), refresh_known)

            _carry_forward_known(current, seen_ids, previous, to_fetch)

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
                current_path=paths.current_path,
                photos_dir=paths.photos_dir,
            )
            watchdog_ok = check_detail_watchdog(n_detail_attempts, n_detail_named, n_detail_with_photo)
            if not watchdog_ok:
                roster_ok = False

        clean_finish = True
    except KeyboardInterrupt:
        log.warning("interrupted; persisting %d partial inmates", len(current))
        raise
    except Exception:
        log.exception("unhandled exception in sweep main loop")
        log.error("sweep %s failed with unhandled exception", sweep_id)
        raise
    finally:
        save_ok = False
        if not dry_run and roster_ok:
            try:
                save_current(paths.current_path, current.values())
                save_ok = True
            except OSError as e:
                log.error("save_current failed (%s); skipping changelog and prune", e)

            if save_ok and clean_finish:
                _save_changelog_and_anon(previous, current, paths)
            elif save_ok:
                log.warning("skipping diff/changelog append: sweep did not finish cleanly")
            if save_ok and seen_ids:
                prune_photos(paths.photos_dir, seen_ids)

    if dry_run:
        log.info("dry-run; not writing")
    log.info(
        "sweep %s completed (roster_ok=%s, clean=%s, seen=%d, current=%d)",
        sweep_id,
        roster_ok,
        clean_finish,
        len(seen_ids),
        len(current),
    )
    return 0


def _read_surnames(path: Path) -> list[str]:
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
