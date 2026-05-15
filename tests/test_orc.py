import json
from pathlib import Path

from scraper.orc import codes_without_titles, normalize_code, title_for


def test_normalize_code_strips_section_prefix():
    assert normalize_code("2903.11") == "2903.11"
    assert normalize_code("ORC 2903.11") == "2903.11"
    assert normalize_code("R.C. 2925.11(A)") == "2925.11"
    assert normalize_code("2903.211") == "2903.211"


def test_normalize_code_handles_garbage():
    assert normalize_code("") == ""
    assert normalize_code("not a code") == ""


def test_title_for_known_codes():
    assert title_for("2903.11") == "Felonious assault"
    assert title_for("2925.11") == "Possession of drugs"
    assert title_for("2919.25") == "Domestic violence"
    assert title_for("4511.19") == "Operating a vehicle under the influence (OVI / DUI)"


def test_title_for_unknown_returns_empty():
    assert title_for("9999.99") == ""


def test_codes_without_titles_dedupes_and_filters():
    missing = codes_without_titles(["2903.11", "2903.11", "9999.99", "", "junk"])
    assert missing == ["9999.99"]


def test_offense_file_is_well_formed():
    raw = json.loads(Path("data/orc_offenses.json").read_text(encoding="utf-8"))
    assert "offenses" in raw
    assert isinstance(raw["offenses"], dict)
    assert len(raw["offenses"]) >= 50
