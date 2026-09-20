"""Case-number display cleaning: HCSO drops the court-prefix letter, leaving a
stray leading slash ("/25/CRA/17789"); the display must read "25/CRA/17789"."""

from __future__ import annotations

from web.shape import _clean_case_number


def test_strips_leading_slash():
    assert _clean_case_number("/25/CRA/17789") == "25/CRA/17789"
    assert _clean_case_number("/26/CRB/1812") == "26/CRB/1812"


def test_preserves_full_and_suffixed_numbers():
    assert _clean_case_number("C/26/CRB/9272/A") == "C/26/CRB/9272/A"
    assert _clean_case_number("B 2403956") == "B 2403956"
    assert _clean_case_number("25/CRB/8420/B") == "25/CRB/8420/B"


def test_trims_whitespace_and_empty():
    assert _clean_case_number("  /24/CRB/19558  ") == "24/CRB/19558"
    assert _clean_case_number("") == ""
    assert _clean_case_number(None) == ""
