"""Common shaping utilities and index classes."""

from __future__ import annotations

import functools
import sys
from collections import defaultdict
from datetime import datetime, timezone

from scraper import orc as orc_mod
from scraper.models import Inmate
from web.classify import _parse_bond_amount, _primary_chapter


@functools.lru_cache(maxsize=1)
def _cached_offenses() -> dict:
    return orc_mod.load_offenses()


def _strftime_nopad(dt, fmt: str) -> str:
    """strftime that honors %-d / %-m on Windows by mapping to %#d / %#m.
    POSIX systems pass the format through unchanged. Keeps date rendering
    portable between the GitHub Actions Linux runner and Windows dev boxes.
    """
    if sys.platform == "win32":
        fmt = fmt.replace("%-", "%#")
    return dt.strftime(fmt)


def _now_naive_est() -> datetime:
    """Return current wall-clock time in America/New_York (EST/EDT) as a naive datetime.
    Used to generate consistent relative labels (e.g. '3 hours ago') during site build
    regardless of the runner timezone.
    """
    utc_now = datetime.now(timezone.utc)
    # Fixed -0400/-0500 offset arithmetic is sufficient for static site display.
    # Ohio is Eastern Time; simple -5h offset works as a naive baseline.
    return utc_now - timedelta(hours=5)


# Pre-computed indexes for O(1) lookup (C1: eliminate O(n²) per-inmate scans)
# ---------------------------------------------------------------------------


class RosterIndexes:
    """Pre-built indexes over the full inmate roster.

    Built once in O(n) during ``build()``; passed to per-inmate helpers so
    they do O(1) dict lookups instead of scanning all_inmates each time.
    """

    __slots__ = ("by_chapter", "by_code", "bonds_by_code")

    def __init__(self, inmates: list[Inmate], offenses: dict | None = None) -> None:
        by_chapter: dict[str, list[Inmate]] = defaultdict(list)
        by_code: dict[str, list[Inmate]] = defaultdict(list)
        bonds_by_code: dict[str, list[int]] = defaultdict(list)

        for inm in inmates:
            chap = _primary_chapter(inm)
            if chap:
                by_chapter[chap["label"]].append(inm)
            has_first_charge = False
            seen_codes_for_inmate = set()
            for c in inm.charges:
                code = orc_mod.normalize_code((c.orc_code or "").strip())
                if not code or code.upper() == "NONE":
                    continue
                if code not in seen_codes_for_inmate:
                    by_code[code].append(inm)
                    seen_codes_for_inmate.add(code)
                if not has_first_charge:
                    v = _parse_bond_amount(c.bond_amount)
                    if v is not None and v > 0:
                        bonds_by_code[code].append(v)
                    has_first_charge = True

        for vals in bonds_by_code.values():
            vals.sort()

        self.by_chapter = dict(by_chapter)
        self.by_code = dict(by_code)
        self.bonds_by_code = dict(bonds_by_code)


from datetime import timedelta
