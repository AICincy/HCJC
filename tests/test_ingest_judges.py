"""Fail-closed tests for scraper/ingest_court_content.ingest_judges.

Judges corpus: ~/workspace/firecrawl-zips/structured/judges.json (30 true
profiles + 5 auxiliary records) -> data/court_judges.json.

The corpus itself lives outside the repo, so these tests build records
in-memory and exercise the validation/quarantine rules directly.
"""

import json

import pytest

from scraper.ingest_court_content import (
    _atomic_write,
    _classify_bio,
    _clean_judge_name,
    _is_auxiliary_record,
    _normalize_fax,
    ingest_judges,
)


def _rec(name="Test Judge", **kw):
    base = {
        "name": name,
        "court": "Common Pleas",
        "page_title": f"Common Pleas Court Judge {name}",
        "url": "https://hamiltoncountycourts.org/index.php/common-pleas-court-judge-test/",
        "courtroom": "100",
        "bailiff": "Test Bailiff",
        "law_clerk": "",
        "phones": ["513-946-1000"],
        "fax": "",
        "email": "",
        "bio": "Judge Test Judge serves the people of Hamilton County.",
    }
    base.update(kw)
    return base


def _thirty():
    return [_rec(name=f"Judge {i:02d}") for i in range(30)]


def test_count_band_accepts_30(tmp_path):
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(_thirty()), encoding="utf-8")
    ds = ingest_judges(src, operator="test")
    assert len(ds["judges"]) == 30
    assert ds["_provenance"]["counts"]["total"] == 30


def test_count_band_aborts_on_29(tmp_path):
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(_thirty()[:29]), encoding="utf-8")
    with pytest.raises(ValueError, match="J-2 count band FAIL"):
        ingest_judges(src, operator="test")


def test_count_band_aborts_on_31(tmp_path):
    recs = _thirty() + [_rec(name="Extra Judge")]
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(recs), encoding="utf-8")
    with pytest.raises(ValueError, match="J-2 count band FAIL"):
        ingest_judges(src, operator="test")


def test_auxiliary_records_excluded():
    aux = [
        _rec(
            name="Municipal Judge Assignments",
            page_title="Municipal Judge Assignments",
            url="https://hamiltoncountycourts.org/index.php/municipal-judge-assignments/",
        ),
        _rec(
            name="Janaya Trotter Bratton",
            page_title="Municipal Court Judge Janaya Trotter Bratton - Civil Cases",
            url="https://hamiltoncountycourts.org/index.php/civil-cases/",
        ),
        _rec(name="Janaya Trotter Bratton", page_title="Municipal Court Judge Janaya Trotter Bratton - Criminal Cases"),
        _rec(
            name="Janaya Trotter Bratton", page_title="Municipal Court Judge Janaya Trotter Bratton - Civil Case Forms"
        ),
        _rec(name="Samantha Silverstein", page_title="Municipal Court Judge Samantha Silverstein - Civil Case Forms"),
    ]
    assert all(_is_auxiliary_record(r) for r in aux)


def test_auxiliary_exclusion_keeps_true_profiles(tmp_path):
    recs = _thirty() + [
        _rec(name="Municipal Judge Assignments", page_title="Municipal Judge Assignments"),
        _rec(name="Janaya Trotter Bratton", page_title="Municipal Court Judge Janaya Trotter Bratton - Civil Cases"),
    ]
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(recs), encoding="utf-8")
    ds = ingest_judges(src, operator="test")
    assert len(ds["judges"]) == 30
    assert ds["_provenance"]["counts"]["auxiliary_excluded"] == 2


def test_true_profile_not_flagged_auxiliary():
    rec = _rec(name="Janaya Trotter Bratton", page_title="Municipal Court Judge Janaya Trotter Bratton")
    assert not _is_auxiliary_record(rec)


def test_all_caps_name_normalization():
    assert _clean_judge_name("MUNICIPAL COURT JUDGE ATHENA STEFANOU") == "Athena Stefanou"
    assert _clean_judge_name("MUNICIPAL COURT JUDGE DANIELLE COLLIVER") == "Danielle Colliver"
    assert _clean_judge_name("MUNICIPAL COURT JUDGE R. BERNARD MUNDY") == "R. Bernard Mundy"
    assert _clean_judge_name("MUNICIPAL COURT JUDGE RODNEY J. HARRIS") == "Rodney J. Harris"


def test_normal_case_name_untouched():
    assert _clean_judge_name("Alan C. Triggs") == "Alan C. Triggs"
    assert _clean_judge_name("Common Pleas Court Judge Alan C. Triggs") == "Alan C. Triggs"


def test_fax_normalization():
    assert _normalize_fax("(513) 946-5864") == "513-946-5864"
    assert _normalize_fax("513-946-5844") == "513-946-5844"
    assert _normalize_fax("") == ""
    assert _normalize_fax(None) == ""


def test_fax_bad_format_fails():
    with pytest.raises(ValueError, match="J-4 fax format FAIL"):
        _normalize_fax("946-5864")


def test_bio_quarantine_empty_omitted():
    bio, status = _classify_bio({"bio": "   ", "court": "Municipal"})
    assert status == "omitted"
    assert bio == ""


def test_bio_quarantine_truncated_omitted():
    # Silverstein-style: cut mid-word at the extraction cap
    raw = ("Judge Silverstein was elected to the bench. " * 20)[:600].rstrip()
    assert len(raw) == 600
    bio, status = _classify_bio({"bio": raw, "court": "Municipal"})
    assert status == "omitted"


def test_bio_quarantine_markdown_stripped():
    raw = "[![jtb-sm](https://example.com/photo.jpg)](https://example.com/page)"
    bio, status = _classify_bio({"bio": raw, "court": "Municipal"})
    assert status == "omitted"  # image-only, nothing left after strip
    raw2 = "[Click Here](https://us02web.zoom.us/j/123) to join the Zoom meeting."
    bio2, status2 = _classify_bio({"bio": raw2, "court": "Common Pleas"})
    assert status2 == "needs_review"
    assert "zoom.us" not in bio2  # link URL stripped, text kept


def test_bio_quarantine_triggs_discrepancy():
    raw = "Judge Triggs was elected to the Hamilton County Municipal Court for the term beginning January 3, 2018."
    bio, status = _classify_bio({"bio": raw, "court": "Common Pleas"})
    assert status == "needs_review"


def test_bio_quarantine_form_list():
    raw = (
        "- [Guilty Plea Misdemeanor](https://example.com/a.pdf) - [Guilty Plea Reagan Tokes](https://example.com/b.pdf)"
    )
    bio, status = _classify_bio({"bio": raw, "court": "Common Pleas"})
    assert status == "needs_review"


def test_bio_quarantine_clean():
    raw = "Judge Test Judge was elected in 2020 and serves the people of Hamilton County."
    bio, status = _classify_bio({"bio": raw, "court": "Common Pleas"})
    assert status == "clean"
    assert bio == raw


def test_atomic_write_replaces_atomically(tmp_path):
    target = tmp_path / "court_judges.json"
    _atomic_write(target, {"a": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    _atomic_write(target, {"a": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2}
    # No temp files left behind
    assert list(tmp_path.glob("*.tmp")) == []


def test_provenance_block(tmp_path):
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(_thirty()), encoding="utf-8")
    ds = ingest_judges(src, operator="track-c-test")
    prov = ds["_provenance"]
    assert prov["schema_version"] == "1.0"
    assert "judges.json" in prov["source"]
    assert prov["crawl_date"] == "2026-09-20"
    assert prov["ingested_utc"]
    assert prov["ingested_by"] == "track-c-test"
    assert prov["max_age_days"] == 365
    assert prov["counts"]["bio_clean"] == 30


def test_invalid_court_fails(tmp_path):
    recs = _thirty()
    recs[0]["court"] = "Probate"
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(recs), encoding="utf-8")
    with pytest.raises(ValueError, match="J-3 court vocab FAIL"):
        ingest_judges(src, operator="test")


def test_invalid_email_fails(tmp_path):
    recs = _thirty()
    recs[0]["email"] = "not-an-email"
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(recs), encoding="utf-8")
    with pytest.raises(ValueError, match="J-4 email format FAIL"):
        ingest_judges(src, operator="test")


def test_missing_phones_fails(tmp_path):
    recs = _thirty()
    recs[0]["phones"] = []
    src = tmp_path / "judges.json"
    src.write_text(json.dumps(recs), encoding="utf-8")
    with pytest.raises(ValueError, match="J-4 phones FAIL"):
        ingest_judges(src, operator="test")
