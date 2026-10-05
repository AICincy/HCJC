#!/usr/bin/env python3
"""Backfill recent anonymized changelog tags from history and the live roster.

The anonymized changelog keeps identifiers for seven days. The preferred source
is the best historical data/current.json snapshot for the event; when history is
incomplete, the current working-tree roster is used for records that are still
present. Released events remain history-only because the current roster no
longer contains those inmates. The repair only fills missing tier/category tags
and never adds new identifying fields.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.store import SnapshotCorruptError, _anonymize_event, _atomic_write_text, _load_takedowns
from scraper.sweep import _anon_enrichment, _load_anon_offenses

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
            if not isinstance(payload, dict):
                continue
            generated = _parse_utc(payload.get("generated_utc", ""))
            inmates = payload.get("inmates", [])
            if generated is None or not isinstance(inmates, list):
                continue
            if generated.isoformat() in seen_generated:
                continue
            seen_generated.add(generated.isoformat())
            from scraper.models import Snapshot

            snapshot = Snapshot.model_validate(payload)
            typed = {inm.inmate_number: inm for inm in snapshot.inmates}
            snapshots.append(HistoricalSnapshot(generated, typed))
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
            log.warning("skipping unreadable historical snapshot %s: %s", commit, exc)
    snapshots.sort(key=lambda snap: snap.generated_utc)
    return snapshots


def _load_current_snapshot() -> HistoricalSnapshot | None:
    """Load the live roster as a recovery fallback when Git history is sparse."""
    try:
        raw = CURRENT_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return None
        generated = _parse_utc(payload.get("generated_utc", ""))
        if generated is None:
            return None
        from scraper.models import Snapshot

        snapshot = Snapshot.model_validate(payload)
        return HistoricalSnapshot(
            generated,
            {inm.inmate_number: inm for inm in snapshot.inmates},
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log.warning("skipping unreadable live roster %s: %s", CURRENT_PATH, exc)
        return None


def _best_current_record(
    snapshot: HistoricalSnapshot | None,
    event: dict,
) -> dict | None:
    """Return a live-roster record for events whose subject should still be present."""
    if snapshot is None or event.get("event") == "released":
        return None
    inmate_number = str(event.get("inmate_number") or "")
    if not inmate_number:
        return None
    return snapshot.inmates.get(inmate_number)


def _best_recovery_record(
    snapshots: list[HistoricalSnapshot],
    current: HistoricalSnapshot | None,
    event: dict,
) -> tuple[dict | None, str | None]:
    """Choose the safest recovery source for an eligible event."""
    if event.get("event") != "released":
        live = _best_current_record(current, event)
        if live is not None:
            return live, "live"
    historical = _best_historical_record(snapshots, event)
    if historical is not None:
        return historical, "history"
    return None, None


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


def _apply_takedowns(rows: list[dict]) -> int:
    """Anonymize retained rows whose inmate number is currently sealed."""
    sealed = _load_takedowns(ANON_CHANGELOG_PATH.parent)
    changed = 0
    for index, row in enumerate(rows):
        inmate_number = str(row.get("inmate_number") or "")
        if inmate_number not in sealed:
            continue
        rows[index] = _anonymize_event(
            {
                "event": row.get("event"),
                "timestamp_utc": row.get("timestamp_utc"),
                "primary_tier": row.get("tier"),
                "primary_category": row.get("category"),
            }
        )
        changed += 1
    return changed


def backfill(days: int = DEFAULT_DAYS, *, dry_run: bool = False) -> dict[str, int]:
    if not ANON_CHANGELOG_PATH.exists():
        return {
            "updated": 0,
            "unresolved": 0,
            "eligible": 0,
            "historical_recovery": 0,
            "live_fallback": 0,
            "takedown_anonymized": 0,
        }

    try:
        rows = json.loads(ANON_CHANGELOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"cannot read {ANON_CHANGELOG_PATH}: {exc}") from exc
    if not isinstance(rows, list):
        raise SystemExit(f"{ANON_CHANGELOG_PATH} is not a JSON array")

    takedown_anonymized = _apply_takedowns(rows)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    eligible = _recent_full_rows(rows, cutoff)
    snapshots = _load_snapshots(cutoff - timedelta(days=1))
    current = _load_current_snapshot()
    offenses = _load_anon_offenses(ORC_OFFENSES_PATH)

    updated = 0
    unresolved = 0
    live_fallback = 0
    historical_recovery = 0
    for row in eligible:
        if row.get("tier") is not None and row.get("category") is not None:
            continue
        inmate, source = _best_recovery_record(snapshots, current, row)
        if inmate is None:
            unresolved += 1
            continue
        if source == "live":
            live_fallback += 1
        elif source == "history":
            historical_recovery += 1
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

    return {
        "updated": updated,
        "unresolved": unresolved,
        "eligible": len(eligible),
        "historical_recovery": historical_recovery,
        "live_fallback": live_fallback,
        "takedown_anonymized": takedown_anonymized,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill recent anon-changelog tier/category tags from history and the live roster.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        result = backfill(args.days, dry_run=args.dry_run)
    except SnapshotCorruptError as exc:
        log.error("refusing anon backfill: %s", exc)
        return 1
    log.warning(
        "anon backfill: eligible=%d updated=%d unresolved=%d history=%d live=%d takedown_anonymized=%d dry_run=%s",
        result["eligible"],
        result["updated"],
        result["unresolved"],
        result["historical_recovery"],
        result["live_fallback"],
        result["takedown_anonymized"],
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
