"""Coverage for the pure helpers in web/shape.py.

These exercise the view-model layer that web/build.py registers as Jinja
globals - the templates consume their output directly, so a regression here
silently corrupts rendered pages.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import pytest

from scraper.models import ChangeEvent, Charge, Inmate, Snapshot
from web import shape
from web.shape import court as shape_court

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


def _bond_charge(*, code: str, desc: str, bond: str) -> Charge:
    return Charge(orc_code=code, description=desc, bond_amount=bond)


def _freeze_now(monkeypatch: pytest.MonkeyPatch, frozen: datetime) -> None:
    """Pin now() used by court bucketing to keep tests deterministic."""
    monkeypatch.setattr(shape_court, "_now_naive_est", lambda: frozen)


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
    # A past date plus a future date - past must NOT be picked, even though
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


def _evt(
    num: str, when: str, *, event: Literal["booked", "released", "updated"] = "updated", name: str = "DOE JOHN"
) -> ChangeEvent:
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


# ---------------------------------------------------------------------------
# _bond_context
# ---------------------------------------------------------------------------


def test_bond_context_returns_none_when_target_has_no_orc_code():
    target = _inm("1", "DOE", "JOHN", charges=[_bond_charge(code="", desc="THEFT M1", bond="$100")])
    assert shape._bond_context(target, [target], offenses={}) is None


def test_bond_context_returns_percentiles_and_my_percentile():
    offenses = {"2913.02": {"title": "Theft", "degree": "M1"}}
    target = _inm("1", "DOE", "JOHN", charges=[_bond_charge(code="2913.02", desc="THEFT M1", bond="$300")])
    peers = [
        _inm(str(i), "PEER", f"P{i}", charges=[_bond_charge(code="2913.02", desc="THEFT M1", bond=bond)])
        for i, bond in zip(range(2, 7), ("$100", "$200", "$300", "$400", "$500"), strict=True)
    ]
    out = shape._bond_context(target, [target, *peers], offenses=offenses)
    assert out == {
        "code": "2913.02",
        "title": "Theft",
        "min": 100,
        "max": 500,
        "p25": 200,
        "p50": 300,
        "p75": 400,
        "p90": 500,
        "peer_count": 5,
        "my_bond": 300,
        "my_percentile": 0.4,
    }


def test_bond_context_picks_most_severe_degree_even_without_target_bond():
    offenses = {
        "2913.02": {"title": "Theft", "degree": "M1"},
        "2903.11": {"title": "Assault", "degree": "F2"},
    }
    target = _inm(
        "1",
        "DOE",
        "JOHN",
        charges=[
            _bond_charge(code="2913.02", desc="THEFT M1", bond="$300"),
            _bond_charge(code="2903.11", desc="ASSAULT F2", bond=""),
        ],
    )
    peers = [
        _inm(str(i), "PEER", f"P{i}", charges=[_bond_charge(code="2903.11", desc="ASSAULT F2", bond=bond)])
        for i, bond in zip(range(2, 7), ("$100", "$200", "$300", "$400", "$500"), strict=True)
    ]
    out = shape._bond_context(target, [target, *peers], offenses=offenses)
    assert out is not None
    assert out["code"] == "2903.11"
    assert out["title"] == "Assault"
    assert out["peer_count"] == 5
    assert out["my_bond"] is None
    assert out["my_percentile"] is None


# ---------------------------------------------------------------------------
# Ported helpers from build.py
# ---------------------------------------------------------------------------


def test_clean_event_note():
    assert shape._clean_event_note("booked 1/1/70") == "booked date not reported"
    assert shape._clean_event_note("released 01/01/1970") == "released date not reported"
    assert shape._clean_event_note("updated 5/14/26") == "updated 5/14/26"


def test_iso_booking_date():
    inm = _inm("1", "DOE", "JOHN")
    inm.booking_date = "5/12/26"
    assert shape._iso_booking_date(inm) == "2026-05-12"

    inm.booking_date = ""
    assert shape._iso_booking_date(inm) is None


def test_card_data_attrs_sort_keys():
    inm = _inm("1", "DOE", "JOHN", charges=[Charge(orc_code="2903.13", description="ASSAULT F4")])
    d = shape._card_data_attrs(inm)
    assert d["degree"] == "F4"
    assert d["custody"] == ""  # no booking date -> unsortable, empty attr

    # %-m/%-d is glibc-only (ValueError on Windows); build the unpadded HCSO date manually.
    bd = datetime.now(timezone.utc) - timedelta(days=3)
    inm.booking_date = f"{bd.month}/{bd.day}/{bd.year % 100:02d}"
    d = shape._card_data_attrs(inm)
    assert d["custody"] == 3  # _days_in_custody compares in UTC, so this is exact

    no_tier = _inm("2", "ROE", "JANE", charges=[Charge(orc_code="", description="")])
    assert shape._card_data_attrs(no_tier)["degree"] == "UNK"


def test_distinct_chapters():
    inm1 = _inm("1", "DOE", "JOHN", charges=[Charge(orc_code="2903.13", description="ASSAULT")])
    inm2 = _inm("2", "SMITH", "JANE", charges=[Charge(orc_code="2925.11", description="DRUGS")])
    res = shape._distinct_chapters([inm1, inm2])
    assert res == [("drugs", "Drugs", 1), ("violence-homicide", "Violence / Homicide", 1)]


def test_roster_stale_context(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    import json

    from scraper.store import WAF_BLOCK_LOG_PATH

    (tmp_path / "data").mkdir(exist_ok=True)
    log_data = [{"timestamp_utc": "2026-06-03T10:00:00Z", "event": "blocked"}]
    Path(WAF_BLOCK_LOG_PATH).write_text(json.dumps(log_data), encoding="utf-8")

    snapshot = Snapshot(generated_utc="2026-06-03T18:00:00Z", inmates=[], inmate_count=0)
    ctx = shape._roster_stale_context(snapshot)
    assert ctx["ever_blocked"] is True
    assert ctx["since"] == "2026-06-03"


def test_prepare_render_data(monkeypatch):
    import web.history
    monkeypatch.setattr(web.history, "_update_history", lambda *args: {"trend": "up"})

    snapshot = Snapshot(generated_utc="2026-06-03T18:00:00Z", inmates=[], inmate_count=0)
    events = [
        ChangeEvent(
            event="booked",
            inmate_number="1",
            name="DOE",
            timestamp_utc="2026-06-03T17:00:00Z",
            note="booked 5/14/26",
        )
    ]

    rd = shape._prepare_render_data(snapshot, events)
    assert rd["recent_booked"] == 0
    assert rd["recent_booked_ids"] == set()
    assert rd["recent_released_24h"] == []

    now = datetime.now(timezone.utc)
    events = [
        ChangeEvent(
            event="booked",
            inmate_number="7",
            name="DOE JOHN",
            timestamp_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            note=f"booked {now.month}/{now.day}/{now.year % 100:02d}",
        ),
        ChangeEvent(
            event="released",
            inmate_number="8",
            name="ROE JANE",
            timestamp_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            note="released",
        ),
    ]
    rd = shape._prepare_render_data(snapshot, events)
    assert rd["recent_booked_ids"] == {"7"}
    assert [e.inmate_number for e in rd["recent_released_24h"]] == ["8"]


def test_warn_about_unmapped_orcs(caplog):
    inm = _inm("1", "DOE", "JOHN", charges=[Charge(orc_code="9999.99")])
    import logging

    with caplog.at_level(logging.INFO):
        shape._warn_about_unmapped_orcs([inm], offenses={})
    assert any("ORC titles missing" in r.message for r in caplog.records)
