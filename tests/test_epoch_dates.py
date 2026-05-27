"""Regression tests for the HCSO epoch-0 ('1/1/70') sentinel date handling.

HCSO emits 1/1/70 when it has no real booking date; the site must never show
1970. Covers the parser guard, the changelog note, and the render filter.
"""
from __future__ import annotations

from web.build import _clean_event_note
from web.classify import _display_date, _parse_book_date


def test_parse_book_date_rejects_epoch_sentinel():
    assert _parse_book_date("1/1/70") is None
    assert _parse_book_date("01/01/1970") is None
    assert _parse_book_date("5/16/2026") is not None
    d = _parse_book_date("5/16/26")
    assert d is not None and d.year == 2026


def test_display_date_blanks_epoch_sentinel():
    assert _display_date("1/1/70") == ""
    assert _display_date("01/01/1970") == ""
    assert _display_date("5/16/2026") != ""


def test_clean_event_note_scrubs_sentinel():
    assert _clean_event_note("booked 1/1/70") == "booked date not reported"
    assert _clean_event_note("booked 01/01/1970") == "booked date not reported"
    assert _clean_event_note("booked 5/16/2026") == "booked 5/16/2026"
    assert _clean_event_note(None) == ""
