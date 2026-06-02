"""Municipal-code charges (Cincinnati / suburb codes, mayor's courts) must not
deep-link to the Ohio Revised Code; real ORC sections still do."""

from __future__ import annotations

from web.build import _statute_url
from web.classify import _orc_chapters

_OFFENSES = {
    "506.6": {"title": "Cincinnati Municipal Code: general offenses", "degree": "M1"},
    "503.52": {"title": "Cincinnati Municipal Code: vicious dogs", "degree": "M1"},
    "910.3": {"title": "Cincinnati Municipal Code: public order", "degree": "M4"},
    "0000.00": {"title": "Booking hold (no ORC code on file)", "degree": ""},
    "2903.13": {"title": "Assault", "degree": "M1"},
    "959.131": {"title": "Cruelty to companion animals", "degree": "M1"},
    "4507.76": {"title": "Code not found in Ohio Revised Code (HCSO data artifact)", "degree": "MM"},
}


def test_municipal_codes_get_no_orc_link():
    assert _statute_url("506.6", _OFFENSES) == ""
    assert _statute_url("503.52", _OFFENSES) == ""
    assert _statute_url("910.3", _OFFENSES) == ""


def test_real_orc_codes_keep_link():
    assert _statute_url("2903.13", _OFFENSES) == "https://codes.ohio.gov/ohio-revised-code/section-2903.13"
    # 959 is a real ORC chapter (offenses relating to domestic animals), not CMC.
    assert _statute_url("959.131", _OFFENSES).endswith("section-959.131")


def test_placeholder_hold_codes_get_no_orc_link():
    # "no ORC code on file" titles must not link to a bogus ORC section.
    assert _statute_url("0000.00", _OFFENSES) == ""


def test_untitled_code_in_known_orc_chapter_links():
    # 2925.99 has no title entry, but chapter 2925 is a known ORC chapter
    # (2903.13/959.131 etc. seed the whitelist via _statute_url's caller; here
    # we pass the precomputed set explicitly).
    chaps = _orc_chapters(_OFFENSES)
    assert _statute_url("2903.99", _OFFENSES, chaps).endswith("section-2903.99")


def test_untitled_code_in_unknown_chapter_suppressed():
    # 777.01: untitled and chapter 777 is not a known ORC chapter -> no link.
    chaps = _orc_chapters(_OFFENSES)
    assert _statute_url("777.01", _OFFENSES, chaps) == ""


def test_hcso_data_artifact_gets_no_orc_link():
    assert _statute_url("4507.76", _OFFENSES) == ""
