from types import SimpleNamespace

from scraper.case_match import (
    match_cases_to_inmates,
    normalize_dob,
    normalize_name_part,
    split_defendant_name,
)


def _inmate(number, last, first, dob="", charges=None):
    return SimpleNamespace(
        inmate_number=number,
        last_name=last,
        first_name=first,
        date_of_birth=dob,
        charges=charges or [],
    )


def _charge(cp="", mun="", other=""):
    return {
        "common_pleas_case": cp,
        "municipal_case": mun,
        "other_case": other,
    }


def _record(name, dob="", case_number="B 24 1234", key="B241234"):
    return {
        "case_number": case_number,
        "case_number_key": key,
        "defendant_name": name,
        "defendant_dob": dob,
    }


def test_split_defendant_name_comma_form():
    assert split_defendant_name("SMITH, JOHN") == ("SMITH", "JOHN")


def test_split_defendant_name_drops_middle():
    assert split_defendant_name("SMITH, JOHN MICHAEL") == ("SMITH", "JOHN")


def test_split_defendant_name_no_comma():
    assert split_defendant_name("JOHN SMITH") == ("SMITH", "JOHN")


def test_split_defendant_name_punctuation_stripped():
    assert split_defendant_name("O'BRIEN-SMITH, MARY-JO") == ("OBRIENSMITH", "MARYJO")


def test_split_defendant_name_empty():
    assert split_defendant_name("") == ("", "")
    assert split_defendant_name("SMITH") == ("SMITH", "")


def test_normalize_name_part():
    assert normalize_name_part("o'brien") == "OBRIEN"
    assert normalize_name_part("") == ""


def test_normalize_dob_two_digit_year():
    assert normalize_dob("11/15/85") == "1985-11-15"
    assert normalize_dob("1/5/05") == "2005-01-05"


def test_normalize_dob_four_digit_year():
    assert normalize_dob("01/15/1985") == "1985-01-15"


def test_normalize_dob_rejects_garbage():
    assert normalize_dob("") is None
    assert normalize_dob("NA") is None
    assert normalize_dob("n/a") is None
    assert normalize_dob("1985-01-15") is None
    assert normalize_dob("13/45/99") is None
    assert normalize_dob("02/30/2000") is None


def test_match_name_and_dob():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985")]
    out = match_cases_to_inmates([_record("SMITH, JOHN", "01/15/1985")], inmates)
    assert list(out) == ["1"]
    assert out["1"][0]["dob_verified"] is True


def test_match_dob_formats_interoperate():
    inmates = [_inmate("1", "SMITH", "JOHN", "11/15/85")]
    out = match_cases_to_inmates([_record("SMITH, JOHN", "11/15/1985")], inmates)
    assert list(out) == ["1"]
    assert out["1"][0]["dob_verified"] is True


def test_match_wrong_dob_no_match():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985")]
    out = match_cases_to_inmates([_record("SMITH, JOHN", "06/06/1990")], inmates)
    assert out == {}


def test_match_disambiguates_same_name_by_dob():
    inmates = [
        _inmate("1", "SMITH", "JOHN", "01/15/1985"),
        _inmate("2", "SMITH", "JOHN", "03/03/1992"),
    ]
    out = match_cases_to_inmates([_record("SMITH, JOHN", "03/03/1992")], inmates)
    assert list(out) == ["2"]


def test_match_name_only_when_unique_roster_name():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985")]
    out = match_cases_to_inmates([_record("SMITH, JOHN")], inmates)
    assert list(out) == ["1"]
    assert out["1"][0]["dob_verified"] is False


def test_match_name_only_ambiguous_without_dob():
    inmates = [
        _inmate("1", "SMITH", "JOHN", "01/15/1985"),
        _inmate("2", "SMITH", "JOHN", "03/03/1992"),
    ]
    out = match_cases_to_inmates([_record("SMITH, JOHN")], inmates)
    assert out == {}


def test_match_submission_dob_unverifiable_against_dobless_roster():
    inmates = [_inmate("1", "SMITH", "JOHN", "")]
    out = match_cases_to_inmates([_record("SMITH, JOHN", "01/15/1985")], inmates)
    assert out == {}


def test_match_no_name_match():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985")]
    out = match_cases_to_inmates([_record("DOE, JANE", "01/15/1985")], inmates)
    assert out == {}


def test_match_skips_non_dict_records():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985")]
    out = match_cases_to_inmates(["junk", None, _record("SMITH, JOHN", "01/15/1985")], inmates)
    assert list(out) == ["1"]


def test_match_case_on_booking_flag():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985", [_charge(mun="25/CRA/12436/B")])]
    on = match_cases_to_inmates([_record("SMITH, JOHN", "01/15/1985", "25/CRA/12436/B", "25CRA12436B")], inmates)
    assert on["1"][0]["case_on_booking"] is True
    off = match_cases_to_inmates([_record("SMITH, JOHN", "01/15/1985", "B 99 0001", "B990001")], inmates)
    assert off["1"][0]["case_on_booking"] is False


def test_match_legacy_record_without_case_key():
    inmates = [_inmate("1", "SMITH", "JOHN", "01/15/1985", [_charge(cp="B 24 1234")])]
    rec = _record("SMITH, JOHN", "01/15/1985")
    del rec["case_number_key"]
    out = match_cases_to_inmates([rec], inmates)
    assert out["1"][0]["case_on_booking"] is True
