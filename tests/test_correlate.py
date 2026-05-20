"""Tests for scraper.correlate._parse_cfs_dt return-shape change.

Locks the (datetime, has_time) tuple contract so a future caller can't
silently regress to the old hour-zero sentinel and mis-classify a real
midnight-UTC event as date-only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from scraper.correlate import _parse_cfs_dt


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
