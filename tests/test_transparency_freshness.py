"""Unit tests for the Track A honest-freshness work (2026-09-20).

Covers the new detail-denial derivation in web.transparency
(detail_denial_context), the denial-aware scorecard status, the A2 freshness
clock (last_healthy_sweep_utc, with generated_utc fallback), and the
save_current clock-preservation behavior. Pure functions preferred; no site
build, no ledger writes.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.models import Inmate
from scraper.store import save_current
from web.transparency import compute_transparency_metrics, detail_denial_context

NOW = datetime(2026, 9, 20, 16, 0, 0, tzinfo=timezone.utc)


def _ts(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _block(ts: str) -> dict:
    return {"event": "blocked", "timestamp_utc": ts}


def _recovered(ts: str) -> dict:
    return {"event": "recovered", "timestamp_utc": ts}


def _detail_block(ts: str, inmate_id: str = "1", mode: str = "http_403") -> dict:
    return {
        "event": "detail_page_waf_block",
        "timestamp_utc": ts,
        "inmate_id": inmate_id,
        "failure_mode": mode,
    }


def _detail_degraded(ts: str, fraction: float = 1.0, attempts: int = 188) -> dict:
    return {
        "event": "detail_degraded",
        "timestamp_utc": ts,
        "detail_attempts": attempts,
        "detail_failures": int(attempts * fraction),
        "failure_fraction": fraction,
    }


def _photo(ts: str) -> dict:
    return {"event": "empty_photo_observed", "timestamp_utc": ts, "inmate_id": "1"}


def _inm(n: str) -> Inmate:
    return Inmate(
        inmate_number=n,
        booking_number="B" + n,
        last_name="DOE",
        first_name="JOHN",
        booking_date="05/20/25",
    )


# ----- detail_denial_context -------------------------------------------------


def test_detail_context_empty_ledger_is_healthy():
    d = detail_denial_context([], now=NOW)
    assert d["status"] == "HEALTHY"
    assert d["open"] is False
    assert d["since_utc"] is None
    assert d["total_block_events"] == 0
    assert d["total_degraded_events"] == 0
    assert d["last_failure_utc"] is None


def test_detail_context_trailing_blocks_are_degraded():
    entries = [_detail_block(_ts(5)), _detail_block(_ts(2), inmate_id="2")]
    d = detail_denial_context(entries, now=NOW)
    assert d["status"] == "DEGRADED"
    assert d["open"] is True
    assert d["since_utc"] == _ts(5)
    assert d["last_failure_utc"] == _ts(2)
    assert d["total_block_events"] == 2


def test_detail_context_full_systemic_failure_is_blocked():
    entries = [_detail_block(_ts(3)), _detail_degraded(_ts(1), fraction=1.0)]
    d = detail_denial_context(entries, now=NOW)
    assert d["status"] == "BLOCKED"
    assert d["open"] is True
    # "Since" prefers the first per-inmate block of the open period.
    assert d["since_utc"] == _ts(3)


def test_detail_context_partial_systemic_failure_is_degraded():
    d = detail_denial_context([_detail_degraded(_ts(1), fraction=0.5)], now=NOW)
    assert d["status"] == "DEGRADED"
    assert d["open"] is True
    assert d["since_utc"] == _ts(1)


def test_detail_context_window_expires_stale_evidence():
    entries = [_detail_block(_ts(30)), _detail_degraded(_ts(26), fraction=1.0)]
    d = detail_denial_context(entries, now=NOW)
    assert d["status"] == "HEALTHY"
    assert d["open"] is False
    assert d["since_utc"] is None
    # Totals still count all-time evidence even when the window expired.
    assert d["total_block_events"] == 1
    assert d["total_degraded_events"] == 1


def test_detail_context_ignores_photo_observations():
    d = detail_denial_context([_photo(_ts(1))], now=NOW)
    assert d["status"] == "HEALTHY"
    assert d["open"] is False


# ----- compute_transparency_metrics: denial-aware status ---------------------


def test_detail_only_denial_blocks_scorecard_with_fresh_roster():
    # D2 regression: the roster list is fresh but detail retrieval is fully
    # denied. The scorecard must read BLOCKED, never FRESH.
    entries = [_detail_block(_ts(3)), _detail_degraded(_ts(1), fraction=1.0)]
    m = compute_transparency_metrics(entries, _ts(0.5), now=NOW)
    assert m["status"] == "BLOCKED"
    assert m["roster_denial_open"] is False
    assert m["detail_denial_open"] is True
    assert m["detail_status"] == "BLOCKED"
    assert m["detail_denial_since_utc"] == _ts(3)
    assert m["total_detail_block_events"] == 1
    assert m["total_detail_degraded_events"] == 1
    assert m["last_detail_failure_utc"] == _ts(1)


def test_roster_denial_still_blocks_without_detail_evidence():
    entries = [_block(_ts(5))]
    m = compute_transparency_metrics(entries, _ts(0.5), now=NOW)
    assert m["status"] == "BLOCKED"
    assert m["roster_denial_open"] is True
    assert m["detail_denial_open"] is False
    assert m["detail_status"] == "HEALTHY"


def test_stale_without_any_open_denial():
    entries = [_block(_ts(30)), _recovered(_ts(29))]
    m = compute_transparency_metrics(entries, _ts(10), now=NOW)
    assert m["status"] == "STALE"
    assert m["roster_denial_open"] is False
    assert m["detail_denial_open"] is False


def test_fresh_when_nothing_denied_and_clock_recent():
    m = compute_transparency_metrics([], _ts(0.5), now=NOW)
    assert m["status"] == "FRESH"


# ----- A2 freshness clock -----------------------------------------------------


def test_freshness_hours_uses_last_healthy_sweep_utc():
    # Roster vintage is 1h old but the last fully healthy sweep was 30h ago:
    # the clock must report the healthy sweep, not the roster write.
    m = compute_transparency_metrics([], _ts(1), now=NOW, last_healthy_sweep_utc=_ts(30))
    assert m["freshness_hours"] == 30.0
    assert m["roster_age_hours"] == 1.0
    assert m["last_healthy_sweep_utc"] == _ts(30)
    assert m["status"] == "STALE"


def test_freshness_hours_falls_back_to_generated_utc():
    # Snapshots written before the field existed carry "": fall back so the
    # metric stays defined during migration.
    m = compute_transparency_metrics([], _ts(2), now=NOW, last_healthy_sweep_utc="")
    assert m["freshness_hours"] == 2.0
    assert m["last_healthy_sweep_utc"] is None


def test_freshness_hours_none_when_no_timestamps():
    m = compute_transparency_metrics([], None, now=NOW)
    assert m["freshness_hours"] is None
    assert m["roster_age_hours"] is None
    assert m["status"] == "FRESH"


# ----- save_current clock preservation ---------------------------------------


def test_save_current_writes_explicit_healthy_stamp(tmp_path: Path):
    path = tmp_path / "current.json"
    save_current(path, [_inm("1")], last_healthy_sweep_utc="2026-09-19T02:45:00Z")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["last_healthy_sweep_utc"] == "2026-09-19T02:45:00Z"


def test_save_current_preserves_clock_when_not_healthy(tmp_path: Path):
    path = tmp_path / "current.json"
    save_current(path, [_inm("1")], last_healthy_sweep_utc="2026-09-19T02:45:00Z")
    # A degraded sweep passes None: the previous stamp must survive.
    save_current(path, [_inm("1")], last_healthy_sweep_utc=None)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["last_healthy_sweep_utc"] == "2026-09-19T02:45:00Z"


def test_save_current_defaults_clock_empty_without_prior_file(tmp_path: Path):
    path = tmp_path / "current.json"
    save_current(path, [_inm("1")])
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["last_healthy_sweep_utc"] == ""
