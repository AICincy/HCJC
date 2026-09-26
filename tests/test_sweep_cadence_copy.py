"""Templates must describe the live sweep cadence, not retired 15/30-minute copy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "web" / "templates"
SWEEP_YML = ROOT / ".github" / "workflows" / "sweep.yml"

CADENCE_TEMPLATES = (
    "index.html",
    "archive.html",
    "court.html",
    "data.html",
    "inmate.html",
    "visit.html",
)


def test_sweep_yml_is_twice_hourly() -> None:
    text = SWEEP_YML.read_text(encoding="utf-8")
    assert "cron: '7,37 * * * *'" in text


def test_roster_templates_do_not_claim_15_or_30_minute_sweep() -> None:
    for name in CADENCE_TEMPLATES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        assert "15-minute" not in text, name
        assert "every 15 minutes" not in text, name
        assert "30-minute cron" not in text, name


def test_bond_disparity_methodology_matches_orc_selection() -> None:
    text = (TEMPLATES / "bond-disparity.html").read_text(encoding="utf-8")
    assert "first charge that has a valid ORC code" in text
    assert "first-listed charge" not in text
