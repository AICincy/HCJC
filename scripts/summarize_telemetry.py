"""Summarize JCStream sweep telemetry for quick local triage.

Reads the durable WAF-block evidence log (data/waf_block_log.json) and the
current snapshot timestamp, and prints a one-screen health summary: whether
retrieval is currently blocked, the trailing block streak, how stale the roster
is, and block/recovery counts.

    python -m scripts.summarize_telemetry

Offline; no network. Exit 0 always; this is a report, not a gate.
"""
from __future__ import annotations

import json
from pathlib import Path

from scraper.store import WAF_BLOCK_LOG_PATH, load_block_log
from scraper.sweep_guards import ROSTER_STALE_ALARM_HOURS, roster_stale_hours

CURRENT_PATH = Path("data/current.json")


def _generated_utc(path: Path = CURRENT_PATH) -> str:
    try:
        return json.loads(path.read_text()).get("generated_utc", "") or ""
    except (OSError, ValueError):
        return ""


def _trailing_block_streak(entries: list[dict]) -> int:
    streak = 0
    for rec in reversed(entries):
        if rec.get("event") == "blocked":
            streak += 1
        else:
            break
    return streak


def summarize(entries: list[dict], generated_utc: str) -> list[str]:
    """Build the report lines from the block log and snapshot timestamp."""
    blocked = [r for r in entries if r.get("event") == "blocked"]
    recovered = [r for r in entries if r.get("event") == "recovered"]
    last = entries[-1] if entries else None
    currently_blocked = bool(last) and last.get("event") == "blocked"
    stale = roster_stale_hours(generated_utc)

    lines = [
        f"roster generated_utc : {generated_utc or 'unknown'}",
        f"roster stale hours   : {round(stale, 1) if stale is not None else 'unknown'}"
        f" (alarm at {ROSTER_STALE_ALARM_HOURS}h)",
        f"current state        : {'BLOCKED' if currently_blocked else 'ok'}",
        f"trailing block streak: {_trailing_block_streak(entries)}",
        f"block records        : {len(blocked)}",
        f"recovery records     : {len(recovered)}",
    ]
    if blocked:
        lines.append(f"first blocked        : {(blocked[0].get('timestamp_utc') or '?')[:19]}")
    if last:
        lines.append(f"last event           : {last.get('event')} @ {(last.get('timestamp_utc') or '?')[:19]}")
    return lines


def main() -> int:
    entries = load_block_log()
    if not entries:
        print(f"No WAF-block evidence yet ({WAF_BLOCK_LOG_PATH}). Retrieval has not logged a block.")
        return 0
    print("\n".join(summarize(entries, _generated_utc())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
