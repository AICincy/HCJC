import json
from pathlib import Path

from scraper.orc import codes_without_titles, normalize_code, title_for

REPO = Path(__file__).resolve().parents[1]


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
    raw = json.loads((REPO / "data" / "orc_offenses.json").read_text(encoding="utf-8"))
    assert "offenses" in raw
    assert isinstance(raw["offenses"], dict)
    assert len(raw["offenses"]) >= 50


def test_all_offenses_have_valid_degree():
    raw = json.loads((REPO / "data" / "orc_offenses.json").read_text(encoding="utf-8"))
    valid_degrees = set(raw["_degree_order"])
    for code, entry in raw["offenses"].items():
        assert "title" in entry, f"{code} missing 'title'"
        assert "degree" in entry, f"{code} missing 'degree'"
        assert entry["title"], f"{code} has empty title"
        assert entry["degree"] in valid_degrees, f"{code} has invalid degree {entry['degree']!r}"


def test_extract_degree_unknown_criminal_defaults_to_question_mark():
    from scraper.update_orc_offenses import extract_degree

    # Unknown criminal degree must be "?" (explicitly unknown), not a guess.
    _, degree = extract_degree("SOME UNRECOGNIZED OFFENSE", is_criminal=True)
    assert degree == "?"
    # Non-criminal (traffic/minor misdemeanor) still defaults to MM.
    _, degree = extract_degree("SOME UNRECOGNIZED OFFENSE", is_criminal=False)
    assert degree == "MM"
