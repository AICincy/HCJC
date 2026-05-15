"""Match Cincinnati Open Data dispatch/arrest calls to HCSO inmate bookings.

A CFS row with an arrest/citation/offense-report disposition is the dispatch
event for an arrest. The corresponding HCSO booking is created some
minutes-to-hours later, and HCSO records only the booking *date* (no time),
so we anchor the booking at midnight and accept any dispatch from the prior
evening through the booking day plus an overnight — i.e. roughly
``booking_midnight - 12h`` to ``booking_midnight + 36h``.

We do not match by name (the CFS rows are not name-indexed). The match is
probabilistic; we surface candidates without claiming certainty.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable

from .models import Inmate

log = logging.getLogger(__name__)

WINDOW_BEFORE = timedelta(hours=12)   # prior-evening dispatch -> next-day booking
WINDOW_AFTER = timedelta(hours=36)    # booking-day + overnight
MAX_CANDIDATES_PER_INMATE = 4
ARREST_PREFIXES = ("ARR", "CIT", "301")  # disposition codes that end in a booking-ish outcome


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).rstrip("Z"))
    except ValueError:
        return None


def _parse_booking_date(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _is_arrest_disposition(row: dict) -> bool:
    d = (row.get("disposition_text") or "").strip().upper()
    return any(d.startswith(p) for p in ARREST_PREFIXES)


def candidates_for(inmate: Inmate, cfs_rows: list[dict]) -> list[dict]:
    booking_dt = _parse_booking_date(inmate.booking_date)
    if booking_dt is None:
        return []
    lo, hi = booking_dt - WINDOW_BEFORE, booking_dt + WINDOW_AFTER
    matches: list[tuple[timedelta, dict]] = []
    for row in cfs_rows:
        if (row.get("agency") or "CPD") != "CPD":
            continue
        if not _is_arrest_disposition(row):
            continue
        created = _parse_iso(row.get("create_time_incident", ""))
        if created is None or not (lo <= created <= hi):
            continue
        matches.append((abs(created - booking_dt), row))
    matches.sort(key=lambda t: t[0])
    return [row for _, row in matches[:MAX_CANDIDATES_PER_INMATE]]


def attach_candidates(inmates: Iterable[Inmate], cfs_rows: list[dict]) -> dict[str, list[dict]]:
    """Return a mapping ``inmate_number -> [cfs_row, ...]`` (only those with matches)."""
    inmates = list(inmates)
    out: dict[str, list[dict]] = {}
    for inm in inmates:
        cands = candidates_for(inm, cfs_rows)
        if cands:
            out[inm.inmate_number] = cands
    log.info("CFS matcher: %d/%d inmates have candidate dispatch calls (%d CFS rows scanned)",
             len(out), len(inmates), len(cfs_rows))
    return out
