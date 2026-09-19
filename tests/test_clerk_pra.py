import json

from scraper.clerk_pra import (
    build_packet,
    full_name,
    known_case_numbers,
    render_letter,
    sanitize_filename_part,
)


def _inmate(number="2316160", last="ADAMS", first="CHEVALIER", dob="11/15/85"):
    return {
        "inmate_number": number,
        "last_name": last,
        "first_name": first,
        "middle_name": "",
        "date_of_birth": dob,
        "booking_date": "7/21/25",
        "charges": [
            {
                "common_pleas_case": "",
                "municipal_case": "25/CRA/12436/B",
                "other_case": "",
            }
        ],
    }


def test_sanitize_filename_part():
    assert sanitize_filename_part("2316160") == "2316160"
    assert sanitize_filename_part("O'Brien-Smith") == "O_BRIEN_SMITH"
    assert sanitize_filename_part("") == "UNKNOWN"
    assert sanitize_filename_part("x" * 100) == "X" * 40


def test_full_name_formats():
    assert full_name(_inmate()) == "ADAMS, CHEVALIER"
    assert full_name(_inmate(last="SMITH", first="JOHN", dob="")) == "SMITH, JOHN"
    assert full_name({"last_name": "", "first_name": "", "middle_name": ""}) == ""


def test_known_case_numbers_dedups_and_orders():
    inmate = _inmate()
    inmate["charges"].append({"common_pleas_case": "B 25 0001", "municipal_case": "25/CRA/12436/B", "other_case": ""})
    assert known_case_numbers(inmate) == ["25/CRA/12436/B", "B 25 0001"]


def test_render_letter_contains_required_elements():
    letter = render_letter(_inmate(), "2026-09-19", "2026-09-19T23:00:00Z")
    assert "Ohio Revised Code 149.43" in letter
    assert "Hamilton County Clerk of Courts" in letter
    assert "1000 Main Street" in letter
    assert "ADAMS, CHEVALIER" in letter
    assert "11/15/85" in letter
    assert "25/CRA/12436/B" in letter
    assert "[YOUR FULL NAME]" in letter
    assert "[YOUR SIGNATURE]" in letter
    assert "not affiliated" in letter


def test_render_letter_missing_dob_uses_placeholder():
    letter = render_letter(_inmate(dob=""), "2026-09-19", "2026-09-19T23:00:00Z")
    assert "[date of birth not in roster]" in letter


def test_render_letter_no_cases_asks_name_search():
    inmate = _inmate()
    inmate["charges"] = []
    letter = render_letter(inmate, "2026-09-19", "2026-09-19T23:00:00Z")
    assert "no case number" in letter


def test_build_packet_writes_letters_manifest_readme(tmp_path):
    folder = build_packet(
        [_inmate(), _inmate(number="2", last="DOE", first="JANE")],
        "2026-09-19",
        "2026-09-19",
        tmp_path,
    )
    assert folder == tmp_path / "2026-09-19"
    letters = sorted(p.name for p in folder.glob("*.md") if p.name != "README.md")
    assert letters == ["2316160_ADAMS_CHEVALIER.md", "2_DOE_JANE.md"]
    assert (folder / "README.md").read_text(encoding="utf-8").startswith("# Clerk PRA packet")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"2316160", "2"}
    entry = manifest["2316160"]
    assert entry["full_name"] == "ADAMS, CHEVALIER"
    assert entry["known_case_numbers"] == ["25/CRA/12436/B"]
    assert entry["letter_file"] == "2316160_ADAMS_CHEVALIER.md"
    assert entry["status"] == "draft-ready-to-send"
    assert entry["clerk_response"] is None
    assert entry["generated_utc"].endswith("Z")


def test_build_packet_skips_nameless_entries(tmp_path):
    folder = build_packet(
        [{"inmate_number": "9", "last_name": "", "first_name": ""}, _inmate()],
        "2026-09-19",
        "2026-09-19",
        tmp_path,
    )
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"2316160"}


def test_build_packet_limit(tmp_path):
    folder = build_packet([_inmate(), _inmate(number="2")], "2026-09-19", "2026-09-19", tmp_path, limit=1)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
