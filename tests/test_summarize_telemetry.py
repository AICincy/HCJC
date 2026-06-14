"""Tests for the offline summary logic in scripts/summarize_telemetry.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import scripts.summarize_telemetry as st


def _ts(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_trailing_block_streak_counts_only_trailing_blocks():
    entries = [
        {"event": "blocked"},
        {"event": "recovered"},
        {"event": "blocked"},
        {"event": "blocked"},
    ]
    assert st._trailing_block_streak(entries) == 2


def test_trailing_block_streak_zero_when_last_is_recovery():
    assert st._trailing_block_streak([{"event": "blocked"}, {"event": "recovered"}]) == 0


def test_summarize_reports_blocked_state_and_counts():
    entries = [
        {"event": "blocked", "timestamp_utc": "2026-05-19T14:00:00Z"},
        {"event": "recovered", "timestamp_utc": "2026-05-19T16:00:00Z"},
        {"event": "blocked", "timestamp_utc": "2026-05-20T09:00:00Z"},
    ]
    lines = st.summarize(entries, _ts(8.0))
    blob = "\n".join(lines)
    assert "current state        : BLOCKED" in blob
    assert "block records        : 2" in blob
    assert "recovery records     : 1" in blob
    assert "first blocked        : 2026-05-19T14:00:00" in blob


def test_summarize_reports_ok_when_last_is_recovery():
    entries = [
        {"event": "blocked", "timestamp_utc": "2026-05-19T14:00:00Z"},
        {"event": "recovered", "timestamp_utc": "2026-05-19T16:00:00Z"},
    ]
    blob = "\n".join(st.summarize(entries, _ts(0.5)))
    assert "current state        : ok" in blob


def test_generated_utc_tolerates_missing_file(tmp_path):
    assert st._generated_utc(tmp_path / "nope.json") == ""
