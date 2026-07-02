"""Coverage for the court-date slippage aggregate (web/shape/court.py).

The T6 acceptance fixture: sentinel dates, past dates, today, and future
dates must produce the hand-computed counts, with the today boundary taken
from the injected Eastern-time ``now``.
"""

from __future__ import annotations

from datetime import datetime

from scraper.models import Charge, Inmate
from web.shape import _court_slippage

# Noon Eastern on 2026-06-15; the today boundary is midnight that day.
NOW = datetime(2026, 6, 15, 12, 0, 0)


def _inm(number: str, court_dates: list[str], desc: str = "THEFT F5") -> Inmate:
    return Inmate(
        inmate_number=number,
        last_name="DOE",
        first_name="JOHN",
        charges=[Charge(court_date=d, description=desc) for d in court_dates],
    )


def test_hand_computed_fixture():
    inmates = [
        _inm("1", ["06/01/26"]),  # 14 days past
        _inm("2", ["06/10/26"], desc="MURDER F1"),  # 5 days past
        _inm("3", ["06/12/26"]),  # 3 days past
        _inm("4", ["06/15/26"]),  # today: not past (strictly-before rule)
        _inm("5", ["06/20/26"]),  # future
        _inm("6", ["1/1/70"]),  # epoch sentinel: excluded entirely
        _inm("7", [""]),  # no date
        _inm("8", []),  # no charges
    ]
    s = _court_slippage(inmates, now=NOW)
    assert s["total"] == 3
    assert s["median_days"] == 5
    assert s["tiers"] == [{"label": "F1", "count": 1}, {"label": "F5", "count": 2}]


def test_earliest_date_governs():
    # One charge already passed, another upcoming: the earliest (past) date
    # counts the person as slipped, measured from that earliest date.
    inm = _inm("1", ["06/13/26", "07/01/26"])
    s = _court_slippage([inm], now=NOW)
    assert s["total"] == 1
    assert s["median_days"] == 2


def test_sentinel_not_treated_as_earliest():
    # A sentinel alongside a real future date must not flag the person.
    inm = _inm("1", ["1/1/70", "06/20/26"])
    s = _court_slippage([inm], now=NOW)
    assert s["total"] == 0


def test_empty_roster():
    s = _court_slippage([], now=NOW)
    assert s == {"total": 0, "median_days": 0, "tiers": []}


def test_even_count_median_rounds():
    inmates = [
        _inm("1", ["06/01/26"]),  # 14
        _inm("2", ["06/10/26"]),  # 5
    ]
    s = _court_slippage(inmates, now=NOW)
    assert s["total"] == 2
    assert s["median_days"] == round((14 + 5) / 2)


def test_untiered_inmate_grouped_as_other():
    inm = _inm("1", ["06/01/26"], desc="HOLD")
    s = _court_slippage([inm], now=NOW)
    assert s["tiers"] == [{"label": "other", "count": 1}]


def test_fallback_venue_tier():
    inm = Inmate(
        inmate_number="1",
        last_name="DOE",
        first_name="JOHN",
        charges=[Charge(court_date="06/01/26", description="HOLD", common_pleas_case="B 2601234")],
    )
    s = _court_slippage([inm], now=NOW)
    assert s["tiers"] == [{"label": "F", "count": 1}]


def test_venue_fallback_tiers_group_under_f_and_m():
    # No degree suffix and no ORC mapping: the tier comes from the case
    # venue (Common Pleas -> F, Municipal -> M), not the ladder.
    felony = Inmate(
        inmate_number="1",
        last_name="DOE",
        first_name="JOHN",
        charges=[Charge(court_date="06/01/26", description="HOLD", common_pleas_case="B2601234")],
    )
    misd = Inmate(
        inmate_number="2",
        last_name="ROE",
        first_name="JANE",
        charges=[Charge(court_date="06/01/26", description="HOLD", municipal_case="C26001")],
    )
    s = _court_slippage([felony, misd], now=NOW)
    assert s["tiers"] == [{"label": "F", "count": 1}, {"label": "M", "count": 1}]
