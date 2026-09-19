import pytest

from scraper.case_match import normalize_case_number
from scraper.ingest_issue import (
    CasesFileError,
    build_case_record,
    confirmations_checked,
    load_cases,
    parse_issue_body,
    upsert,
    valid_source_url,
    validate_record,
)
from scraper.ingest_issue import (
    normalize_case_number as _reexported,
)

SAMPLE_BODY = """\
### Case number

B 24 1234

### Defendant name (Last, First)

SMITH, JOHN

### Defendant date of birth (MM/DD/YYYY)

01/15/1985

### Filed date (MM/DD/YYYY)

_No response_

### Judge

Hon. Jane Doe

### Charges (one per line — ORC code, then description)

2903.11 — Felonious assault
2925.11 — Possession of drugs

### Notes (verbatim docket entries only)

_No response_

### Next hearing (MM/DD/YYYY)

06/02/2026

### Disposition

Bound over to grand jury

### Source URL (the courtclerk.org case_summary.php link)

https://www.courtclerk.org/data/case_summary.php?casenumber=B%2024%201234

### Confirmation

- [x] I confirm this data was retrieved from courtclerk.org by my own browser, not by any automated tool.
- [x] I confirm this data contains only verbatim docket information, no personal commentary or speculation.
"""


def _sections():
    return parse_issue_body(SAMPLE_BODY)


def _record(**kwargs):
    return build_case_record(
        _sections(),
        issue_number=kwargs.get("issue_number", 42),
        issue_url=kwargs.get("issue_url", "https://github.com/AICincy/HCJC/issues/42"),
        submitter=kwargs.get("submitter", "someuser"),
    )


def test_parse_extracts_each_section():
    s = _sections()
    assert s["case number"] == "B 24 1234"
    assert s["defendant name (last, first)"] == "SMITH, JOHN"
    assert s["defendant date of birth (mm/dd/yyyy)"] == "01/15/1985"
    assert s["judge"] == "Hon. Jane Doe"
    assert "2903.11" in s["charges (one per line — orc code, then description)"]
    assert s["next hearing (mm/dd/yyyy)"] == "06/02/2026"
    assert s["disposition"] == "Bound over to grand jury"
    # GitHub's _No response_ placeholder is stripped
    assert s["filed date (mm/dd/yyyy)"] == ""
    assert s["notes (verbatim docket entries only)"] == ""


def test_build_case_record_populates_all_fields():
    record = _record()
    assert record["schema_version"] == 1
    assert record["case_number"] == "B 24 1234"
    assert record["case_number_key"] == "B241234"
    assert record["defendant_name"] == "SMITH, JOHN"
    assert record["defendant_dob"] == "01/15/1985"
    assert record["judge"] == "Hon. Jane Doe"
    assert "2903.11" in record["charges_raw"]
    assert record["next_hearing"] == "06/02/2026"
    assert record["disposition"] == "Bound over to grand jury"
    assert record["source_url"].startswith("https://www.courtclerk.org/")
    assert record["issue_number"] == 42
    assert record["submitter"] == "someuser"
    assert record["ingested_utc"].endswith("Z")


def test_normalize_case_number_collapses_variants():
    assert normalize_case_number("B 24 1234") == "B241234"
    assert normalize_case_number("B24-1234") == "B241234"
    assert normalize_case_number("b 24/1234") == "B241234"
    assert normalize_case_number("25/CRA/00123") == "25CRA00123"
    assert _reexported("B 24 1234") == "B241234"  # same function via ingest_issue


def test_confirmations_checked_requires_both_boxes():
    assert confirmations_checked(_sections()) is True
    unchecked = dict(_sections())
    unchecked["confirmation"] = unchecked["confirmation"].replace("- [x]", "- [ ]", 1)
    assert confirmations_checked(unchecked) is False
    assert confirmations_checked({}) is False


def test_valid_source_url_accepts_only_clerk_case_summary():
    good = "https://www.courtclerk.org/data/case_summary.php?casenumber=B%2024%201234"
    assert valid_source_url(good) is True
    assert valid_source_url("http://www.courtclerk.org/data/case_summary.php?x=1") is False
    assert valid_source_url("https://evil.com/data/case_summary.php?x=1") is False
    assert valid_source_url("https://www.courtclerk.org/records-search/") is False
    assert valid_source_url("https://www.courtclerk.org/data/crim_name_results.php?lname=X") is False
    assert valid_source_url("") is False
    assert valid_source_url("not a url") is False


def test_validate_record_accepts_clean_submission():
    assert validate_record(_record(), _sections()) == []


def test_validate_record_rejects_bad_url():
    sections = dict(_sections())
    sections["source url (the courtclerk.org case_summary.php link)"] = "https://evil.example/x"
    problems = validate_record(build_case_record(sections, 1, "", ""), sections)
    assert any("Source URL" in p for p in problems)


def test_validate_record_rejects_unchecked_confirmation():
    sections = dict(_sections())
    sections["confirmation"] = "- [ ] nope"
    problems = validate_record(build_case_record(sections, 1, "", ""), sections)
    assert any("Confirmation" in p for p in problems)


def test_validate_record_rejects_missing_case_number():
    sections = dict(_sections())
    sections["case number"] = ""
    problems = validate_record(build_case_record(sections, 1, "", ""), sections)
    assert any("Case number" in p for p in problems)


def test_upsert_replaces_format_variants():
    initial = [{"case_number": "B 24 1234", "case_number_key": "B241234", "submitter": "old"}]
    new = {"case_number": "B24-1234", "case_number_key": "B241234", "submitter": "new"}
    result = upsert(initial, new)
    assert len(result) == 1
    assert result[0]["submitter"] == "new"


def test_upsert_appends_new_case_number():
    initial = [{"case_number": "B 24 1234", "case_number_key": "B241234"}]
    result = upsert(initial, {"case_number": "B 24 9999", "case_number_key": "B249999"})
    assert len(result) == 2


def test_fields_are_length_capped():
    sections = dict(_sections())
    sections["judge"] = "J" * 500
    sections["notes (verbatim docket entries only)"] = "N" * 99999
    record = build_case_record(sections, 1, "", "")
    assert len(record["judge"]) == 120
    assert len(record["notes"]) == 20000


def test_load_cases_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_cases() == []


def test_load_cases_corrupt_file_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "courtclerk_cases.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(CasesFileError):
        load_cases()


def test_load_cases_non_list_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "courtclerk_cases.json").write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(CasesFileError):
        load_cases()
