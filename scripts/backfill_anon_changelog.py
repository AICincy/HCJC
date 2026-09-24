#!/usr/bin/env python3
"""Backfill recent anonymized changelog tags from Git history.

The anonymized changelog keeps identifiers for seven days. Within that window,
the repository history can still contain a historical data/current.json snapshot
for the booking or release event. This script uses those snapshots to restore
missing tier/category tags without introducing any new identifying fields.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.sweep import _anon_enrichment, _load_anon_offenses
from scraper.store import _atomic_write_text

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CURRENT_PATH = ROOT / "data" / "current.json"
ANON_CHANGELOG_PATH = ROOT / "data" / "anon_changelog.json"
ORC_OFFENSES_PATH = ROOT / "data" / "orc_offenses.json"
DEFAULT_DAYS = 7


@dataclass(frozen=True)
class HistoricalSnapshot:
    generated_utc: datetime
    inmates: dict


def _parse_utc(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _snapshot_commits(since: datetime) -> list[str]:
    since_arg = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    output = _run_git(
        "log",
        "--all",
        "--since",
        since_arg,
        "--format=%H",
        "--",
        "data/current.json",
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _load_snapshots(since: datetime) -> list[HistoricalSnapshot]:
    snapshots: list[HistoricalSnapshot] = []
    seen_generated: set[str] = set()
    for commit in _snapshot_commits(since):
        try:
            raw = _run_git("show", f"{commit}:data/current.json")
            payload = json.loads(raw)
            generated = _parse_utc(payload.get("generated_utc", ""))
            inmates = payload.get("inmates", [])
            if generated is None or not isinstance(inmates, list):
                continue
            if generated.isoformat() in seen_generated:
                continue
            seen_generated.add(generated.isoformat())
            by_id = {
                str(row.get("inmate_number")): row
                for row in inmates
                if isinstance(row, dict) and row.get("inmate_number")
            }
            from scraper.models import Inmate, Snapshot

            snapshot = Snapshot.model_validate(payload)
            typed = {inm.inmate_number: inm for inm in snapshot.inmates}
            snapshots.append(HistoricalSnapshot(generated, typed))
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
            log.warning("skipping unreadable historical snapshot %s: %s", commit, exc)
    snapshots.sort(key=lambda snap: snap.generated_utc)
    return snapshots


def _best_historical_record(
    snapshots: list[HistoricalSnapshot],
    event: dict,
) -> dict | None:
    event_time = _parse_utc(event.get("timestamp_utc", ""))
    inmate_number = str(event.get("inmate_number") or "")
    if event_time is None or not inmate_number:
        return None

    before: tuple[float, object] | None = None
    after: tuple[float, object] | None = None
    for snapshot in snapshots:
        inmate = snapshot.inmates.get(inmate_number)
        if inmate is None:
            continue
        delta = abs((snapshot.generated_utc - event_time).total_seconds())
        if snapshot.generated_utc <= event_time:
            if before is None or delta < before[0]:
                before = (delta, inmate)
        if snapshot.generated_utc >= event_time:
            if after is None or delta < after[0]:
                after = (delta, inmate)

    if event.get("event") == "released":
        candidate = before or after
    elif event.get("event") == "booked":
        candidate = after or before
    else:
        if before and after:
            candidate = before if before[0] <= after[0] else after
        else:
            candidate = before or after
    return candidate[1] if candidate else None


def _recent_full_rows(rows: list[dict], cutoff: datetime) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        stamp = _parse_utc(row.get("timestamp_utc", ""))
        if stamp is not None and stamp >= cutoff and row.get("inmate_number"):
            out.append(row)
    return out


def backfill(days: int = DEFAULT_DAYS, *, dry_run: bool = False) -> dict[str, int]:
    if not ANON_CHANGELOG_PATH.exists():
        return {"updated": 0, "unresolved": 0, "eligible": 0}

    try:
        rows = json.loads(ANON_CHANGELOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"cannot read {ANON_CHANGELOG_PATH}: {exc}") from exc
    if not isinstance(rows, list):
        raise SystemExit(f"{ANON_CHANGELOG_PATH} is not a JSON array")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    eligible = _recent_full_rows(rows, cutoff)
    snapshots = _load_snapshots(cutoff - timedelta(days=1))
    offenses = _load_anon_offenses(ORC_OFFENSES_PATH)

    updated = 0
    unresolved = 0
    for row in eligible:
        if row.get("tier") is not None and row.get("category") is not None:
            continue
        inmate = _best_historical_record(snapshots, row)
        if inmate is None:
            unresolved += 1
            continue
        enrichment = _anon_enrichment({}, {inmate.inmate_number: inmate}, offenses)[inmate.inmate_number]
        changed = False
        if row.get("tier") is None and enrichment.get("tier") is not None:
            row["tier"] = enrichment["tier"]
            changed = True
        if row.get("category") is None and enrichment.get("category") is not None:
            row["category"] = enrichment["category"]
            changed = True
        if changed:
            updated += 1

    if not dry_run:
        _atomic_write_text(ANON_CHANGELOG_PATH, json.dumps(rows, indent=2))

    return {"updated": updated, "unresolved": unresolved, "eligible": len(eligible)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill recent anon-changelog tier/category tags from git history.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    result = backfill(args.days, dry_run=args.dry_run)
    log.warning(
        "anon backfill: eligible=%d updated=%d unresolved=%d dry_run=%s",
        result["eligible"],
        result["updated"],
        result["unresolved"],
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
