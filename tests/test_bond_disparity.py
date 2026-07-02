"""Coverage for the Bond Disparity Index aggregation (web/shape/bond.py).

T2 acceptance gates: the n >= 5 suppression floor is enforced, quartile math
matches statistics.quantiles, and the page renders with zero qualifying
statutes.
"""

from __future__ import annotations

import statistics

from scraper.models import Charge, Inmate
from web.shape import BOND_DISPARITY_MIN_N, RosterIndexes, _bond_disparity


def _inmates_with_bonds(code: str, amounts: list[int], start: int = 1) -> list[Inmate]:
    return [
        Inmate(
            inmate_number=str(start + i),
            last_name="DOE",
            first_name="JOHN",
            charges=[Charge(orc_code=code, description="THEFT F5", bond_amount=f"${a:,}.00")],
        )
        for i, a in enumerate(amounts)
    ]


def test_suppression_floor_enforced():
    below = _inmates_with_bonds("2913.02", [100, 200, 300, 400])  # n=4: suppressed
    at_floor = _inmates_with_bonds("2925.11", [100, 200, 300, 400, 500], start=10)  # n=5: shown
    idx = RosterIndexes(below + at_floor, {})
    rows = _bond_disparity(idx, {})
    assert [r["code"] for r in rows] == ["2925.11"]
    assert rows[0]["n"] == BOND_DISPARITY_MIN_N


def test_quartile_math_matches_statistics_quantiles():
    amounts = [100, 200, 300, 400, 500]
    idx = RosterIndexes(_inmates_with_bonds("2913.02", amounts), {})
    (row,) = _bond_disparity(idx, {})
    q1, med, q3 = statistics.quantiles(sorted(amounts), n=4)
    assert row["q1"] == round(q1) == 150
    assert row["median"] == round(med) == 300
    assert row["q3"] == round(q3) == 450
    assert row["min"] == 100
    assert row["max"] == 500
    assert row["spread"] == round(q3 / q1, 1) == 3.0


def test_ranked_by_spread_descending():
    tight = _inmates_with_bonds("2913.02", [1000, 1000, 1000, 1000, 1000])  # spread 1.0
    wide = _inmates_with_bonds("2925.11", [100, 200, 500, 2000, 10000], start=10)
    idx = RosterIndexes(tight + wide, {})
    rows = _bond_disparity(idx, {})
    assert [r["code"] for r in rows] == ["2925.11", "2913.02"]
    assert rows[1]["spread"] == 1.0


def test_zero_qualifying_statutes():
    idx = RosterIndexes(_inmates_with_bonds("2913.02", [100]), {})
    assert _bond_disparity(idx, {}) == []


def test_zero_and_missing_bonds_do_not_count_toward_floor():
    inmates = _inmates_with_bonds("2913.02", [100, 200, 300, 400])
    inmates.append(
        Inmate(
            inmate_number="99",
            last_name="ROE",
            first_name="JANE",
            charges=[Charge(orc_code="2913.02", description="THEFT F5", bond_amount="")],
        )
    )
    idx = RosterIndexes(inmates, {})
    # 4 parseable bonds + 1 empty: still below the floor of 5.
    assert _bond_disparity(idx, {}) == []


def test_page_renders_with_zero_qualifying_statutes(tmp_path, monkeypatch):
    import json as _json

    inmate = Inmate(
        inmate_number="1234567",
        last_name="Doe",
        first_name="John",
        booking_date="05/20/25",
        charges=[Charge(description="Test charge F5", orc_code="2913.02", bond_amount="$1,000.00")],
    )
    from scraper.models import Snapshot

    snapshot = Snapshot(generated_utc="2025-05-20T12:00:00Z", inmate_count=1, inmates=[inmate])
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "current.json").write_text(snapshot.model_dump_json(indent=2))
    (data_dir / "changelog.json").write_text("[]")
    (data_dir / "waf_block_log.json").write_text(_json.dumps([]))
    monkeypatch.chdir(tmp_path)

    from web.build import build

    out = tmp_path / "docs"
    build(out)

    html = (out / "bond-disparity" / "index.html").read_text(encoding="utf-8")
    assert "Bond Disparity Index" in html
    assert "No statute currently has" in html
    assert 'content="noindex, noarchive"' in html
