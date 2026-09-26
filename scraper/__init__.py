"""JCStream scraper: hcso.org -> structured JSON."""

from __future__ import annotations

import logging

__version__ = "0.1.0"

# HCSO detail pages put a booking-photo <img> at img[2] with
# data:image/png;base64 and an empty payload. The parser correctly skips
# that slot and records empty_photo_observed once. Repeating the INFO lines
# every sweep makes every run look like a parser miss.
_QUIET_PHOTO_FRAGMENTS = (
    "empty photo payload skipped",
    "investigate HTML drift",
    "skipping duplicate empty_photo_observed",
)


class _KnownEmptyPhotoFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(frag in msg for frag in _QUIET_PHOTO_FRAGMENTS)


def _install_empty_photo_log_filter() -> None:
    filt = _KnownEmptyPhotoFilter()
    for name in ("scraper.parsers", "scraper.store"):
        logger = logging.getLogger(name)
        if not any(isinstance(existing, _KnownEmptyPhotoFilter) for existing in logger.filters):
            logger.addFilter(filt)


_install_empty_photo_log_filter()
