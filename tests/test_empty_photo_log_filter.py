"""HCSO empty booking-photo slots must not look like HTML drift."""

from __future__ import annotations

import logging

from scraper import _KnownEmptyPhotoFilter


def test_filter_drops_known_empty_photo_noise() -> None:
    filt = _KnownEmptyPhotoFilter()
    record = logging.LogRecord(
        name="scraper.parsers",
        level=logging.INFO,
        pathname="parsers.py",
        lineno=1,
        msg="empty photo payload skipped for id=14317042 field=img[2]@src data:image/png;base64 payload_length=0",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is False


def test_filter_drops_false_drift_line() -> None:
    filt = _KnownEmptyPhotoFilter()
    record = logging.LogRecord(
        name="scraper.parsers",
        level=logging.INFO,
        pathname="parsers.py",
        lineno=1,
        msg=(
            "detail page id=14317042 parsed (bio=8 name=True charges=3) but no photo extracted "
            "(imgs=5 non-data=4 data=1). If HCSO has a photo here, the alt/class/274px "
            "hooks and the size+extension fallback all missed it - investigate HTML drift."
        ),
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is False


def test_filter_keeps_unrelated_parser_info() -> None:
    filt = _KnownEmptyPhotoFilter()
    record = logging.LogRecord(
        name="scraper.parsers",
        level=logging.INFO,
        pathname="parsers.py",
        lineno=1,
        msg="detail page produced no structured fields for id=1",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
