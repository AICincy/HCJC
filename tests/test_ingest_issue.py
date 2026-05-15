from scraper.ingest_issue import build_case_record, parse_issue_body, upsert

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

### Source URL (the courtclerk.org case_summary.php link)

https://www.courtclerk.org/data/case_summary.php?casenumber=B%2024%201234

### Confirmation

- [x] I confirm this data was retrieved from courtclerk.org by my own browser, not by any automated tool.
- [x] I confirm this data contains only verbatim docket information, no personal commentary or speculation.
"""


def test_parse_extracts_each_section():
    s = parse_issue_body(SAMPLE_BODY)
    assert s["case number"] == "B 24 1234"
    assert s["defendant name (last, first)"] == "SMITH, JOHN"
    assert s["defendant date of birth (mm/dd/yyyy)"] == "01/15/1985"
    assert s["judge"] == "Hon. Jane Doe"
    assert "2903.11" in s["charges (one per line — orc code, then description)"]
    # GitHub's _No response_ placeholder is stripped
    assert s["filed date (mm/dd/yyyy)"] == ""
    assert s["notes (verbatim docket entries only)"] == ""


def test_build_case_record_populates_all_fields():
    record = build_case_record(
        parse_issue_body(SAMPLE_BODY),
        issue_number=42,
        issue_url="https://github.com/AICincy/JCStream/issues/42",
        submitter="someuser",
    )
    assert record["case_number"] == "B 24 1234"
    assert record["defendant_name"] == "SMITH, JOHN"
    assert record["defendant_dob"] == "01/15/1985"
    assert record["judge"] == "Hon. Jane Doe"
    assert "2903.11" in record["charges_raw"]
    assert record["source_url"].startswith("https://www.courtclerk.org/")
    assert record["issue_number"] == 42
    assert record["submitter"] == "someuser"
    assert record["ingested_utc"].endswith("Z")


def test_upsert_replaces_same_case_number():
    initial = [{"case_number": "B 24 1234", "submitter": "old"}]
    new = {"case_number": "B 24 1234", "submitter": "new"}
    result = upsert(initial, new)
    assert len(result) == 1
    assert result[0]["submitter"] == "new"


def test_upsert_appends_new_case_number():
    initial = [{"case_number": "B 24 1234"}]
    result = upsert(initial, {"case_number": "B 24 9999"})
    assert len(result) == 2
