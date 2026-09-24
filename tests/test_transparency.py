"""Coverage for web/transparency.py and the /transparency/ page render.

The hand-computed fixture below is the acceptance gate for T4: the metrics
the page publishes (and the JSON mirror that feeds filing exhibits) must
match arithmetic done by hand on a known blocked/recovered sequence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scraper.models import Charge, Inmate, Snapshot
from web.transparency import compute_transparency_metrics


@pytest.fixture(autouse=True)
def _no_orc_offenses_rewrite(monkeypatch):
    """Hermeticity: web.build.build() calls update_orc_offenses(), which reads
    the real repo's data/current.json and conditionally rewrites the committed
    data/orc_offenses.json via absolute ROOT_DIR paths. Neutralize it; the
    fixture snapshots written by these tests are complete on their own."""
    monkeypatch.setattr("scraper.update_orc_offenses.update_orc_offenses", lambda: None)


NOW = datetime(2026, 6, 2, 5, 0, 0, tzinfo=timezone.utc)


def _blocked(ts: str) -> dict:
    return {"event": "blocked", "timestamp_utc": ts}


def _recovered(ts: str) -> dict:
    return {"event": "recovered", "timestamp_utc": ts}


def _photo(ts: str) -> dict:
    return {"event": "empty_photo_observed", "timestamp_utc": ts, "inmate_id": "1"}


# ----- compute_transparency_metrics -----------------------------------------


def test_empty_ledger_fresh_roster():
    m = compute_transparency_metrics([], "2026-06-02T04:30:00Z", now=NOW)
    assert m["status"] == "FRESH"
    assert m["total_block_events"] == 0
    assert m["first_block_utc"] is None
    assert m["last_block_utc"] is None
    assert m["current_streak"] == 0
    assert m["longest_streak"] == 0
    assert m["denied_hours_total"] == 0.0
    assert m["days_since_last_block"] is None
    assert m["freshness_hours"] == 0.5


def test_empty_ledger_missing_generated_utc():
    m = compute_transparency_metrics([], None, now=NOW)
    assert m["status"] == "FRESH"
    assert m["freshness_hours"] is None


def test_hand_computed_fixture():
    # Period 1: blocked 00:00 and 01:00 on 5/30, recovered 03:00 -> 3.0 denied hours.
    # Period 2: blocked 6/2 00:00, still open at NOW (05:00) -> 5.0 denied hours.
    entries = [
        _blocked("2026-05-30T00:00:00Z"),
        _blocked("2026-05-30T01:00:00Z"),
        _recovered("2026-05-30T03:00:00Z"),
        _blocked("2026-06-02T00:00:00Z"),
    ]
    m = compute_transparency_metrics(entries, "2026-06-01T00:00:00Z", now=NOW)
    assert m["total_block_events"] == 3
    assert m["first_block_utc"] == "2026-05-30T00:00:00Z"
    assert m["last_block_utc"] == "2026-06-02T00:00:00Z"
    assert m["current_streak"] == 1
    assert m["longest_streak"] == 2
    assert m["denied_hours_total"] == 8.0
    assert m["days_since_last_block"] == 0
    # Roster 29h stale with an open denial period -> BLOCKED.
    assert m["freshness_hours"] == 29.0
    assert m["status"] == "BLOCKED"


def test_stale_without_open_block():
    entries = [
        _blocked("2026-05-30T00:00:00Z"),
        _recovered("2026-05-30T02:00:00Z"),
    ]
    m = compute_transparency_metrics(entries, "2026-06-01T00:00:00Z", now=NOW)
    assert m["status"] == "STALE"
    assert m["current_streak"] == 0
    assert m["denied_hours_total"] == 2.0
    assert m["days_since_last_block"] == 3


def test_fresh_after_recovery():
    entries = [
        _blocked("2026-05-30T00:00:00Z"),
        _recovered("2026-05-30T02:00:00Z"),
    ]
    m = compute_transparency_metrics(entries, "2026-06-02T04:30:00Z", now=NOW)
    assert m["status"] == "FRESH"


def test_photo_events_are_ignored():
    base = [
        _blocked("2026-05-30T00:00:00Z"),
        _recovered("2026-05-30T03:00:00Z"),
    ]
    interleaved = [
        _photo("2026-05-29T00:00:00Z"),
        base[0],
        _photo("2026-05-30T01:00:00Z"),
        _photo("2026-05-30T02:00:00Z"),
        base[1],
        _photo("2026-06-01T00:00:00Z"),
    ]
    assert compute_transparency_metrics(interleaved, "2026-06-02T04:30:00Z", now=NOW) == (
        compute_transparency_metrics(base, "2026-06-02T04:30:00Z", now=NOW)
    )


def test_recovered_without_prior_block_is_harmless():
    m = compute_transparency_metrics([_recovered("2026-05-30T00:00:00Z")], "2026-06-02T04:30:00Z", now=NOW)
    assert m["total_block_events"] == 0
    assert m["denied_hours_total"] == 0.0
    assert m["current_streak"] == 0


def test_unparseable_timestamp_counts_event_but_skips_duration():
    entries = [
        {"event": "blocked", "timestamp_utc": "not-a-date"},
        _recovered("2026-05-30T03:00:00Z"),
    ]
    m = compute_transparency_metrics(entries, "2026-06-02T04:30:00Z", now=NOW)
    assert m["total_block_events"] == 1
    assert m["longest_streak"] == 1
    assert m["denied_hours_total"] == 0.0


# ----- page render + JSON mirror ---------------------------------------------


def _write_minimal_site_inputs(tmp_path: Path, block_log: list[dict]) -> None:
    inmate = Inmate(
        inmate_number="1234567",
        booking_number="B001",
        last_name="Doe",
        first_name="John",
        booking_date="05/20/25",
        charges=[Charge(description="Test charge F5", orc_code="2913.02")],
    )
    snapshot = Snapshot(
        generated_utc="2025-05-20T12:00:00Z",
        inmate_count=1,
        inmates=[inmate],
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "current.json").write_text(snapshot.model_dump_json(indent=2))
    (data_dir / "changelog.json").write_text("[]")
    (data_dir / "waf_block_log.json").write_text(json.dumps(block_log))


def test_build_renders_transparency_page_and_mirror(tmp_path, monkeypatch):
    _write_minimal_site_inputs(tmp_path, [_blocked("2026-05-30T00:00:00Z")])
    monkeypatch.chdir(tmp_path)

    from web.build import build

    out = tmp_path / "docs"
    build(out)

    html = (out / "transparency" / "index.html").read_text(encoding="utf-8")
    assert "Access Transparency Scorecard" in html
    # Snapshot generated_utc is far in the past and the block is unrecovered.
    assert 'class="status-pill status-pill-blocked">Blocked</span>' in html
    assert "2026-05-30T00:00:00Z" in html
    assert 'content="noindex, noarchive"' in html

    mirror = json.loads((out / "data" / "transparency_metrics.json").read_text(encoding="utf-8"))
    assert mirror["status"] == "BLOCKED"
    assert mirror["total_block_events"] == 1
    assert mirror["current_streak"] == 1

    sums = (out / "data" / "SHA256SUMS").read_text(encoding="utf-8")
    assert "transparency_metrics.json" in sums


def test_build_renders_transparency_page_without_ledger(tmp_path, monkeypatch):
    _write_minimal_site_inputs(tmp_path, [])
    monkeypatch.chdir(tmp_path)

    from web.build import build

    out = tmp_path / "docs"
    build(out)

    html = (out / "transparency" / "index.html").read_text(encoding="utf-8")
    assert "none recorded" in html
    mirror = json.loads((out / "data" / "transparency_metrics.json").read_text(encoding="utf-8"))
    assert mirror["total_block_events"] == 0
    # Deterministic build: anchored to data vintage (Option B audit fix 2026-09-24),
    # so empty ledger with vintage matching now is FRESH. STALE only occurs when
    # last_healthy_sweep_utc lags behind generated_utc by >= alarm threshold.
    assert mirror["status"] == "FRESH"
    # Computed UTC must be anchored to data vintage, not wall-clock, for reproducible builds.
    assert mirror["computed_utc"] == "2025-05-20T12:00:00Z"
    assert mirror["roster_generated_utc"] == "2025-05-20T12:00:00Z"
