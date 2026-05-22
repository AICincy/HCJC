"""Municipal-code charges (Cincinnati / suburb codes, mayor's courts) must not
deep-link to the Ohio Revised Code; real ORC sections still do."""
from __future__ import annotations

from web.build import _statute_url

_OFFENSES = {
    "506.6": {"title": "Cincinnati Municipal Code: general offenses", "degree": "M1"},
    "503.52": {"title": "Cincinnati Municipal Code: vicious dogs", "degree": "M1"},
    "910.3": {"title": "Cincinnati Municipal Code", "degree": "M4"},
    "2903.13": {"title": "Assault", "degree": "M1"},
    "959.131": {"title": "Cruelty to companion animals", "degree": "M1"},
}


def test_municipal_codes_get_no_orc_link():
    assert _statute_url("506.6", _OFFENSES) == ""
    assert _statute_url("503.52", _OFFENSES) == ""
    assert _statute_url("910.3", _OFFENSES) == ""


def test_real_orc_codes_keep_link():
    assert _statute_url("2903.13", _OFFENSES) == "https://codes.ohio.gov/ohio-revised-code/section-2903.13"
    # 959 is a real ORC chapter (offenses relating to domestic animals), not CMC.
    assert _statute_url("959.131", _OFFENSES).endswith("section-959.131")


def test_unknown_code_defaults_to_orc_link():
    # No title entry: treat as ORC (keep the link) rather than silently drop it.
    assert _statute_url("2925.11", _OFFENSES).endswith("section-2925.11")
