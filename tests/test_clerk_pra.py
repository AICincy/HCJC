import json

import pytest

from scraper.clerk_pra import (
    build_packet,
    case_types,
    full_name,
    known_case_numbers,
    main,
    normalize_folder_date,
    recipient_block,
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
    # Municipal-only case routes to the Municipal division, not Room 315.
    assert "1000 Sycamore Street" in letter
    assert "Municipal Criminal/Traffic Division" in letter
    assert "ADAMS, CHEVALIER" in letter
    assert "11/15/85" in letter
    assert "25/CRA/12436/B" in letter
    assert "[YOUR FULL NAME]" in letter
    assert "[YOUR SIGNATURE]" in letter
    assert "not affiliated" in letter


def test_render_letter_common_pleas_routes_to_room_315():
    inmate = _inmate()
    inmate["charges"] = [{"common_pleas_case": "B 2603812", "municipal_case": "", "other_case": ""}]
    letter = render_letter(inmate, "2026-09-19", "2026-09-19T23:00:00Z")
    assert "1000 Main Street, Room 315" in letter
    assert "Criminal Division" in letter
    assert "1000 Sycamore" not in letter


def test_render_letter_mixed_cases_includes_routing_note():
    inmate = _inmate()
    inmate["charges"] = [
        {"common_pleas_case": "B 2603812", "municipal_case": "", "other_case": ""},
        {"common_pleas_case": "", "municipal_case": "25/CRA/12436/B", "other_case": ""},
    ]
    letter = render_letter(inmate, "2026-09-19", "2026-09-19T23:00:00Z")
    assert "1000 Main Street, Room 315" in letter
    assert "Routing note" in letter
    assert "1000 Sycamore Street" in letter


def test_case_types_classification():
    assert case_types(["B 2603812"]) == {"common_pleas"}
    assert case_types(["25/CRA/12436/B"]) == {"municipal"}
    assert case_types(["B 2603812", "25/CRA/12436/B"]) == {"common_pleas", "municipal"}
    assert case_types(["XYZ 123"]) == {"other"}
    assert case_types([]) == set()


def test_recipient_block_routing():
    attn, street, city, note = recipient_block(["B 2603812"])
    assert "Room 315" in street
    assert note == ""
    attn, street, city, note = recipient_block(["25/CRA/12436/B"])
    assert "Sycamore" in street
    assert note == ""
    attn, street, city, note = recipient_block(["B 2603812", "25/CRA/12436/B"])
    assert "Room 315" in street
    assert "forward" in note


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
    assert set(manifest) == {"packet", "requests"}
    packet = manifest["packet"]
    assert packet["folder_date"] == "2026-09-19"
    assert packet["letter_count"] == 2
    assert packet["legal_basis"] == "Ohio Revised Code 149.43"
    assert packet["legal_basis_verified_utc"] == "2026-09-20"
    assert "common_pleas" in packet["recipients"]
    assert "municipal" in packet["recipients"]
    assert packet["status"] == "draft-ready-to-send"
    requests = manifest["requests"]
    assert set(requests) == {"2316160", "2"}
    entry = requests["2316160"]
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
    assert set(manifest["requests"]) == {"2316160"}
    assert manifest["packet"]["letter_count"] == 1


def test_normalize_folder_date_accepts_human_variants():
    assert normalize_folder_date("2026-09-22") == "2026-09-22"
    assert normalize_folder_date("2026-9-2") == "2026-09-02"
    assert normalize_folder_date("  2026-09-22\n") == "2026-09-22"


def test_normalize_folder_date_rejects_garbage():
    for bad in ("", "09/22/2026", "2026-13-01", "2026-02-30", "yesterday", "2026-09-22x"):
        with pytest.raises(ValueError):
            normalize_folder_date(bad)


def _roster_file(tmp_path):
    path = tmp_path / "current.json"
    path.write_text(
        json.dumps({"generated_utc": "2026-09-22T23:00:00Z", "inmates": [_inmate()]}),
        encoding="utf-8",
    )
    return path


def test_main_normalizes_unpadded_dispatch_date(tmp_path):
    out = tmp_path / "pra"
    roster = _roster_file(tmp_path)
    assert main(["--date", "2026-9-22", "--out", str(out), "--roster", str(roster)]) == 0
    assert (out / "2026-09-22" / "manifest.json").exists()


def test_main_rejects_bad_date_and_missing_roster(tmp_path):
    out = tmp_path / "pra"
    roster = _roster_file(tmp_path)
    assert main(["--date", "09/22/2026", "--out", str(out), "--roster", str(roster)]) == 2
    assert main(["--out", str(out), "--roster", str(tmp_path / "nope.json")]) == 2


def test_build_packet_limit(tmp_path):
    folder = build_packet([_inmate(), _inmate(number="2")], "2026-09-19", "2026-09-19", tmp_path, limit=1)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["requests"]) == 1
    # The surviving entry must be the first inmate, not an arbitrary one.
    assert set(manifest["requests"]) == {"2316160"}
