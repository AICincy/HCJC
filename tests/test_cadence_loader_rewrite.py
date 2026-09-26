"""Loader rewrite and roster_stale.oldest_detail_utc stay wired."""

from __future__ import annotations

from scraper.models import Inmate, Snapshot
from web.shape import _rewrite_retired_cadence, _roster_stale_context


def test_inmate_template_rewrite() -> None:
    src = "observed on its own ~15-minute sweeps. They are"
    out = _rewrite_retired_cadence(src, "inmate.html")
    assert "hourly sweeps" in out
    assert "15-minute" not in out


def test_data_template_rewrite() -> None:
    src = (
        "rebuilt by GitHub Actions on a best-effort schedule (cron every 15 minutes). "
        "<dd>15-minute sweep</dd> "
        "(~8 days of activity at 15-min sweep cadence)"
    )
    out = _rewrite_retired_cadence(src, "data.html")
    assert "(hourly, best-effort)" in out
    assert "<dd>hourly sweep</dd>" in out
    assert "at hourly sweep cadence" in out
    assert "15-minute" not in out
    assert "15-min" not in out


def test_other_templates_untouched() -> None:
    src = "typically within 30 minutes. on its own ~15-minute sweeps"
    assert _rewrite_retired_cadence(src, "visit.html") == src


def test_roster_stale_exposes_oldest_detail_utc() -> None:
    snapshot = Snapshot(
        generated_utc="2026-09-26T12:00:00Z",
        inmate_count=2,
        inmates=[
            Inmate(
                inmate_number="1",
                last_name="A",
                first_name="A",
                last_detail_fetch_utc="2026-09-26T11:00:00Z",
            ),
            Inmate(
                inmate_number="2",
                last_name="B",
                first_name="B",
                last_detail_fetch_utc="2026-09-26T10:00:00Z",
            ),
        ],
    )
    ctx = _roster_stale_context(snapshot)
    assert ctx["oldest_detail_utc"] == "2026-09-26T10:00:00Z"
