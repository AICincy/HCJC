"""Coverage for the pure helpers in web/shape.py.

These exercise the view-model layer that web/build.py registers as Jinja
globals — the templates consume their output directly, so a regression here
silently corrupts rendered pages.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scraper.models import ChangeEvent, Charge, Inmate
from web import shape

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _inm(num: str, last: str, first: str, charges=None) -> Inmate:
    return Inmate(
        inmate_number=num,
        last_name=last,
        first_name=first,
        charges=charges or [],
    )


def _charge_on(dt: datetime, *, code: str = "2913.02", desc: str = "THEFT M1") -> Charge:
    return Charge(orc_code=code, description=desc, court_date=dt.strftime("%m/%d/%y"))


def _freeze_now(monkeypatch: pytest.MonkeyPatch, frozen: datetime) -> None:
    """Pin `datetime.now()` inside web.shape so bucketing is deterministic.

    web/shape.py does `from datetime import datetime`, so the binding to
    monkeypatch is `shape.datetime`. Subclassing avoids breaking other
    constructor calls (timedelta arithmetic, .replace(), comparisons).
    """

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: D401 - mirrors stdlib signature
            return frozen

    monkeypatch.setattr(shape, "datetime", _FrozenDateTime)


# ---------------------------------------------------------------------------
# _court_calendar
# ---------------------------------------------------------------------------

NOW = datetime(2026, 5, 14, 10, 0, 0)  # Thu 2026-05-14 (matches CLAUDE.md date)


def test_court_calendar_empty_input_returns_empty_buckets(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    out = shape._court_calendar([])
    assert out == {"today": [], "tomorrow": [], "this_week": [], "this_month": []}


def test_court_calendar_skips_inmate_with_no_charges(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[])
    out = shape._court_calendar([inm])
    assert all(out[k] == [] for k in ("today", "tomorrow", "this_week", "this_month"))


def test_court_calendar_skips_inmate_with_only_past_date(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    past = NOW - timedelta(days=5)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(past)])
    out = shape._court_calendar([inm])
    assert all(out[k] == [] for k in ("today", "tomorrow", "this_week", "this_month"))


def test_court_calendar_today_bucket(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW)])
    out = shape._court_calendar([inm])
    assert len(out["today"]) == 1
    assert out["today"][0]["inmate"] is inm
    assert out["today"][0]["date_text"] == NOW.strftime("%m/%d/%y")
    # parsed_date is midnight of the matching day.
    assert out["today"][0]["parsed_date"] == datetime(NOW.year, NOW.month, NOW.day)
    assert out["tomorrow"] == [] and out["this_week"] == [] and out["this_month"] == []


def test_court_calendar_tomorrow_bucket(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW + timedelta(days=1))])
    out = shape._court_calendar([inm])
    assert len(out["tomorrow"]) == 1
    assert out["tomorrow"][0]["inmate"] is inm
    assert out["today"] == [] and out["this_week"] == [] and out["this_month"] == []


def test_court_calendar_this_week_bucket_3_days(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW + timedelta(days=3))])
    out = shape._court_calendar([inm])
    assert len(out["this_week"]) == 1
    assert out["this_week"][0]["inmate"] is inm
    assert out["today"] == [] and out["tomorrow"] == [] and out["this_month"] == []


def test_court_calendar_this_month_bucket_15_days(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW + timedelta(days=15))])
    out = shape._court_calendar([inm])
    assert len(out["this_month"]) == 1
    assert out["this_month"][0]["inmate"] is inm
    assert out["today"] == [] and out["tomorrow"] == [] and out["this_week"] == []


def test_court_calendar_excludes_dates_beyond_30_day_window(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    inm = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW + timedelta(days=60))])
    out = shape._court_calendar([inm])
    assert all(out[k] == [] for k in ("today", "tomorrow", "this_week", "this_month"))


def test_court_calendar_uses_earliest_future_date_across_charges(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    # Three future dates on one inmate; earliest (3 days) wins.
    charges = [
        _charge_on(NOW + timedelta(days=20)),
        _charge_on(NOW + timedelta(days=3)),
        _charge_on(NOW + timedelta(days=10)),
    ]
    inm = _inm("1", "DOE", "JOHN", charges=charges)
    out = shape._court_calendar([inm])
    assert len(out["this_week"]) == 1
    assert out["this_week"][0]["parsed_date"] == datetime(
        (NOW + timedelta(days=3)).year,
        (NOW + timedelta(days=3)).month,
        (NOW + timedelta(days=3)).day,
    )
    assert out["this_month"] == []


def test_court_calendar_ignores_past_dates_when_picking_earliest(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    # A past date plus a future date — past must NOT be picked, even though
    # it's the chronologically earliest.
    charges = [
        _charge_on(NOW - timedelta(days=5)),
        _charge_on(NOW + timedelta(days=4)),
    ]
    inm = _inm("1", "DOE", "JOHN", charges=charges)
    out = shape._court_calendar([inm])
    assert len(out["this_week"]) == 1
    assert out["today"] == [] and out["tomorrow"] == [] and out["this_month"] == []


def test_court_calendar_bucket_sorted_by_date_then_name(monkeypatch):
    _freeze_now(monkeypatch, NOW)
    # Same bucket (this_week), three inmates.
    # Two share a date (day+3); one is day+5. Expected order:
    #   1. day+3 with name BANKS JANE (earlier alphabetically)
    #   2. day+3 with name DOE JOHN
    #   3. day+5 with name AYALA JOHN
    a = _inm("1", "DOE", "JOHN", charges=[_charge_on(NOW + timedelta(days=3))])
    b = _inm("2", "BANKS", "JANE", charges=[_charge_on(NOW + timedelta(days=3))])
    c = _inm("3", "AYALA", "JOHN", charges=[_charge_on(NOW + timedelta(days=5))])
    out = shape._court_calendar([a, b, c])
    names = [e["inmate"].full_name for e in out["this_week"]]
    assert names == ["BANKS JANE", "DOE JOHN", "AYALA JOHN"]


# ---------------------------------------------------------------------------
# _events_for_inmate
# ---------------------------------------------------------------------------

def _evt(num: str, when: str, *, event: str = "updated", name: str = "DOE JOHN") -> ChangeEvent:
    return ChangeEvent(event=event, inmate_number=num, name=name, timestamp_utc=when)


def test_events_for_inmate_empty_event_list_returns_empty():
    assert shape._events_for_inmate([], "12345") == []


def test_events_for_inmate_empty_inmate_number_returns_empty():
    # The guard at the top of the function: an empty inmate_number short-circuits
    # so we don't accidentally match every event whose inmate_number is also "".
    events = [_evt("12345", "2026-05-14T10:00:00Z")]
    assert shape._events_for_inmate(events, "") == []


def test_events_for_inmate_filters_other_inmates():
    e1 = _evt("12345", "2026-05-14T10:00:00Z")
    e2 = _evt("99999", "2026-05-14T11:00:00Z")
    e3 = _evt("12345", "2026-05-14T12:00:00Z")
    out = shape._events_for_inmate([e1, e2, e3], "12345")
    assert out == [e1, e3]


def test_events_for_inmate_sorts_oldest_first():
    later = _evt("12345", "2026-05-14T12:00:00Z")
    earlier = _evt("12345", "2026-05-14T08:00:00Z")
    middle = _evt("12345", "2026-05-14T10:00:00Z")
    out = shape._events_for_inmate([later, earlier, middle], "12345")
    assert out == [earlier, middle, later]


def test_events_for_inmate_handles_missing_timestamp():
    # ChangeEvent.timestamp_utc is `str` with no shape validator; "" is a
    # valid (if pathological) value. The sort key falls back to "" so a
    # missing-timestamp event sorts before any populated one.
    no_ts = _evt("12345", "")
    has_ts = _evt("12345", "2026-05-14T10:00:00Z")
    out = shape._events_for_inmate([has_ts, no_ts], "12345")
    assert out == [no_ts, has_ts]


def test_events_for_inmate_returns_multiple_matches_in_order():
    e1 = _evt("12345", "2026-05-10T10:00:00Z", event="booked")
    e2 = _evt("12345", "2026-05-12T10:00:00Z", event="updated")
    e3 = _evt("12345", "2026-05-14T10:00:00Z", event="released")
    # Mix in another inmate's noise and shuffle input order.
    noise = _evt("99999", "2026-05-13T10:00:00Z")
    out = shape._events_for_inmate([e3, noise, e1, e2], "12345")
    assert out == [e1, e2, e3]
    assert [e.event for e in out] == ["booked", "updated", "released"]
