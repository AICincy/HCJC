"""Unit tests for the pure helpers in web/classify.py.

classify.py holds the ORC tier/chapter/category reference data plus a set of
stateless formatting/parsing helpers consumed by templates. It had no test
file; these lock in the string-munging contracts (date parsing, bond parsing,
ordinals, initials, slugs) that templates depend on.
"""
from datetime import datetime

from web.classify import (
    _approx_age,
    _avatar_initials,
    _booking_seq,
    _chap_slug,
    _codes_ohio_url,
    _display_date,
    _expand_race,
    _expand_sex,
    _offense_for_code,
    _parse_bond_amount,
    _parse_book_date,
    _pct_ordinal,
    _rfc822,
    _short_month_label,
)


def test_parse_book_date_two_and_four_digit_years():
    assert _parse_book_date("5/14/26") == datetime(2026, 5, 14)
    assert _parse_book_date("05/14/2026") == datetime(2026, 5, 14)
    assert _parse_book_date("") is None
    assert _parse_book_date(None) is None
    assert _parse_book_date("not a date") is None


def test_parse_bond_amount():
    assert _parse_bond_amount("$50,000.00") == 50000
    assert _parse_bond_amount("BOND $500") == 500
    assert _parse_bond_amount("no cash") is None
    assert _parse_bond_amount(None) is None


def test_display_date_string_and_sentinel():
    assert _display_date("5/14/26") == "May 14, 2026"
    assert _display_date("") == ""
    assert _display_date("1/1/70") == ""  # >15y sentinel guard


def test_short_month_label():
    assert _short_month_label("May 2026") == "May '26"
    assert _short_month_label("") == ""
    assert _short_month_label("undated") == "undated"  # no year -> passthrough


def test_avatar_initials():
    assert _avatar_initials("JOHN DOE") == "JD"
    assert _avatar_initials("MADONNA") == "MA"
    assert _avatar_initials("X") == "X"
    assert _avatar_initials("") == "?"
    assert _avatar_initials("   ") == "?"


def test_expand_race_and_sex():
    assert _expand_sex("M") == "Male"
    assert _expand_sex("m") == "Male"  # case-insensitive
    assert _expand_sex("") == "—"
    assert _expand_sex("Z") == "Z"  # unknown passthrough (upper)
    assert _expand_race("") == "—"


def test_pct_ordinal_english_suffix_rules():
    assert _pct_ordinal(0.50) == "50th"
    assert _pct_ordinal(0.01) == "1st"
    assert _pct_ordinal(0.02) == "2nd"
    assert _pct_ordinal(0.03) == "3rd"
    assert _pct_ordinal(0.11) == "11th"  # teens exception
    assert _pct_ordinal(0.13) == "13th"
    assert _pct_ordinal(1.0) == "100th"
    assert _pct_ordinal(None) == "0th"
    assert _pct_ordinal(0) == "0th"


def test_pct_ordinal_caps_at_100():
    assert _pct_ordinal(1.5) == "100th"


def test_rfc822():
    assert _rfc822("2026-05-14T17:16:37Z") == "Thu, 14 May 2026 17:16:37 +0000"
    assert _rfc822("") == ""
    assert _rfc822("garbage") == ""


def test_chap_slug():
    assert _chap_slug("Homicide & Assault") == "homicide-assault"
    assert _chap_slug("") == ""
    assert _chap_slug("---") == ""


def test_codes_ohio_url():
    assert _codes_ohio_url("2903.02") == "https://codes.ohio.gov/ohio-revised-code/section-2903.02"
    assert _codes_ohio_url("") == ""
    assert _codes_ohio_url("ORC") == ""  # no digits


def test_offense_for_code_chapter_extraction():
    out = _offense_for_code("2903.02")
    assert out is not None and "cls" in out and "label" in out
    assert _offense_for_code(None) is None
    # Unknown chapter falls back to the 'other' category rather than None.
    assert _offense_for_code("9999.99") is not None


def test_booking_seq_year_and_sequence():
    # First 2 digits year, remainder sequence; <8 digits or non-digit -> "".
    assert _booking_seq("26002740") != ""
    assert _booking_seq("123") == ""
    assert _booking_seq("abcdefgh") == ""
    assert _booking_seq(None) == ""


def test_approx_age_none_paths():
    assert _approx_age(None) is None
    assert _approx_age("") is None
    assert _approx_age("not a date") is None
    assert isinstance(_approx_age("5/14/90"), int)
