"""Comprehensive tests for scraper.correlate.

Covers: _parse_cfs_dt, _category_overlap, correlate(), and run().
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scraper.correlate import (
    MIN_CONFIDENCE,
    _category_overlap,
    _parse_cfs_dt,
    correlate,
    run,
)


def test_parse_cfs_dt_returns_has_time_true_for_full_iso():
    row = {"event_datetime": "2026-05-15T18:23:00.000"}
    result = _parse_cfs_dt(row)
    assert result is not None
    dt, has_time = result
    assert dt == datetime(2026, 5, 15, 18, 23, 0, tzinfo=timezone.utc)
    assert has_time is True


def test_parse_cfs_dt_returns_has_time_true_for_legit_midnight_utc():
    # The whole point of the refactor: a row that genuinely happens at
    # midnight UTC must NOT be classified as "Socrata defaulted to midnight."
    row = {"event_datetime": "2026-05-15T00:00:00.000"}
    result = _parse_cfs_dt(row)
    assert result is not None
    dt, has_time = result
    assert dt == datetime(2026, 5, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert has_time is True  # T-separator present, so we trust the time


def test_parse_cfs_dt_returns_has_time_false_for_date_only():
    # Socrata returning just a date (no T-separator) defaults to midnight
    # but has_time signals the caller not to trust the hour.
    row = {"incident_date": "2026-05-15"}
    result = _parse_cfs_dt(row)
    assert result is not None
    dt, has_time = result
    assert dt == datetime(2026, 5, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert has_time is False


def test_parse_cfs_dt_tries_keys_in_order():
    row = {
        "incident_date": "2026-05-10",  # date-only, would be picked second
        "event_datetime": "2026-05-15T18:23:00.000",  # picked first
    }
    result = _parse_cfs_dt(row)
    assert result is not None
    dt, has_time = result
    assert dt.day == 15  # event_datetime won
    assert has_time is True


def test_parse_cfs_dt_returns_none_when_no_field_matches():
    assert _parse_cfs_dt({}) is None
    assert _parse_cfs_dt({"event_datetime": ""}) is None
    assert _parse_cfs_dt({"event_datetime": "not a date"}) is None


# ----- _category_overlap ---------------------------------------------------

def test_category_overlap_exact_match():
    score = _category_overlap("THEFT SHOPLIFTING", "THEFT SHOPLIFTING ARREST")
    assert score > 0.5


def test_category_overlap_no_match():
    assert _category_overlap("MURDER HOMICIDE", "TRAFFIC VIOLATION SPEEDING") == 0.0


def test_category_overlap_empty_inputs():
    assert _category_overlap("", "something") == 0.0
    assert _category_overlap("something", "") == 0.0
    assert _category_overlap("", "") == 0.0


def test_category_overlap_stopwords_ignored():
    score = _category_overlap("of the", "of the a an")
    assert score == 0.0


def test_category_overlap_partial():
    score = _category_overlap("ASSAULT DOMESTIC VIOLENCE", "DOMESTIC DISPUTE CALL")
    assert 0.0 < score < 1.0


# ----- correlate() end-to-end ----------------------------------------------

def _make_current(booking_date: str, charge_desc: str, inmate_number: str = "100") -> dict:
    return {
        "inmates": [{
            "inmate_number": inmate_number,
            "booking_date": booking_date,
            "charges": [{"description": charge_desc}],
        }],
    }


def _make_cfs(dt_str: str, disposition: str = "", incident_type_id: str = "") -> dict:
    return {
        "event_datetime": dt_str,
        "disposition_text": disposition,
        "incident_type_id": incident_type_id,
    }


def test_correlate_returns_candidates_for_matching_pair():
    current = _make_current("5/15/26", "THEFT SHOPLIFTING")
    cfs_rows = [_make_cfs("2026-05-15T00:30:00", disposition="THEFT SHOPLIFTING ARREST")]
    result = correlate(current, cfs_rows, "cfs_recent")
    assert len(result) >= 1
    assert result[0].inmate_number == "100"
    assert result[0].confidence >= MIN_CONFIDENCE


def test_correlate_returns_empty_for_no_overlap():
    current = _make_current("5/15/26", "MURDER")
    cfs_rows = [_make_cfs("2026-05-20T12:00:00", disposition="TRAFFIC STOP")]
    result = correlate(current, cfs_rows, "cfs_recent")
    assert result == []


def test_correlate_skips_inmates_without_charges():
    current = {"inmates": [{"inmate_number": "100", "booking_date": "5/15/26", "charges": []}]}
    result = correlate(current, [_make_cfs("2026-05-15T12:00:00")], "cfs_recent")
    assert result == []


def test_correlate_skips_inmates_without_booking_date():
    current = {"inmates": [{"inmate_number": "100", "booking_date": "", "charges": [{"description": "THEFT"}]}]}
    result = correlate(current, [_make_cfs("2026-05-15T12:00:00")], "cfs_recent")
    assert result == []


def test_correlate_filters_by_time_window():
    current = _make_current("5/15/26", "THEFT SHOPLIFTING")
    far_away = _make_cfs("2026-05-17T12:00:00", disposition="THEFT SHOPLIFTING")
    result = correlate(current, [far_away], "cfs_recent")
    assert result == []


# ----- run() ---------------------------------------------------------------

def test_run_no_data_returns_zero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run(write=False) == 0


def test_run_with_matching_data_writes_output(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    current = {
        "generated_utc": "2026-05-15T12:00:00Z",
        "inmate_count": 1,
        "inmates": [{
            "inmate_number": "200",
            "booking_date": "5/15/26",
            "charges": [{"description": "THEFT SHOPLIFTING UNDER 1000"}],
        }],
    }
    (data_dir / "current.json").write_text(json.dumps(current), encoding="utf-8")

    cfs = [{"event_datetime": "2026-05-15T00:15:00", "disposition_text": "THEFT SHOPLIFTING"}]
    (data_dir / "cfs_recent.json").write_text(json.dumps({"rows": cfs}), encoding="utf-8")

    count = run(write=True)
    assert count >= 1
    out = json.loads((data_dir / "dispatch_correlations.json").read_text(encoding="utf-8"))
    assert out["count"] >= 1
    assert out["pairs"][0]["inmate_number"] == "200"
