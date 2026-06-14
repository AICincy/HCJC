"""Timeline markers, days-in-custody calculation, and ISO booking date."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scraper.models import Inmate
from web.classify import _parse_book_date
from .common import _now_naive_est, _strftime_nopad


def _timeline_markers(inmate: Inmate) -> dict | None:
    """Markers for the time-in-custody timeline: Booked, each court date,
    Today, and projected release. Returns {markers, start, end, total_days}
    or None if there's no booking date to anchor on."""
    booked = _parse_book_date((inmate.booking_date or "").strip())
    if booked is None:
        return None
    now = _now_naive_est()
    release = _parse_book_date((inmate.projected_release_date or "").strip())
    courts: list[tuple[datetime, str, str]] = []
    for c in inmate.charges:
        d = _parse_book_date((c.court_date or "").strip())
        if d is None:
            continue
        courts.append((d, c.description or "", c.orc_code or ""))
    courts.sort(key=lambda t: t[0])
    if release:
        end = release
    elif courts:
        end = courts[-1][0] + timedelta(days=30)
    else:
        end = now + timedelta(days=90)
    if end < now:
        end = now + timedelta(days=30)
    start = booked
    total = max(timedelta(days=1), end - start)

    def _pct(d: datetime) -> float:
        v = (d - start).total_seconds() / total.total_seconds() * 100.0
        return max(0.0, min(100.0, v))

    raw: list[dict] = []
    raw.append({"x": _pct(booked), "label": "Booked", "date": inmate.booking_date or "", "kind": "booked", "sub": ""})
    # Collapse charges that share a court date into one marker so their labels
    # don't stack on the same x and overlap (REQ-007).
    by_date: dict[datetime, list[str]] = {}
    for d, desc, _code in courts:
        by_date.setdefault(d, []).append(desc or "")
    for d in sorted(by_date):
        descs = by_date[d]
        sub = descs[0].lower()[:40] if len(descs) == 1 else f"{len(descs)} hearings"
        raw.append(
            {
                "x": _pct(d),
                "label": "Court",
                "date": _strftime_nopad(d, "%-m/%-d/%y") if hasattr(d, "strftime") else "",
                "kind": "court",
                "sub": sub,
            }
        )
    raw.append({"x": _pct(now), "label": "Today", "date": _strftime_nopad(now, "%b %-d, %Y"), "kind": "now", "sub": ""})
    if release:
        raw.append(
            {
                "x": _pct(release),
                "label": "Projected release",
                "date": inmate.projected_release_date or "",
                "kind": "release",
                "sub": "",
            }
        )
    raw.sort(key=lambda m: m["x"])
    last_x = -1e9
    side = "below"
    for m in raw:
        # Markers closer than 12% alternate above/below to avoid label overlap;
        # a well-separated marker resets to below.
        if m["x"] - last_x < 12.0:
            side = "above" if side == "below" else "below"
        else:
            side = "below"
        m["side"] = side
        last_x = m["x"]
    return {
        "markers": raw,
        "now_x": _pct(now),
        "start": booked,
        "end": end,
        "total_days": max(1, (end - start).days),
    }


def _days_in_custody(inmate: Inmate) -> int | None:
    bd = _parse_book_date(inmate.booking_date or "")
    if bd is None:
        return None
    days = (datetime.now(timezone.utc) - bd.replace(tzinfo=timezone.utc)).days
    # Reject sentinel dates from upstream (e.g. epoch-era "1/1/70") that yield
    # tens of thousands of days. Nobody is in pretrial custody for 15+ years;
    # show no days-ago count rather than a nonsense one.
    if days < 0 or days > 5475:  # 15 * 365
        return None
    return days


def _iso_booking_date(inmate: Inmate) -> str | None:
    """ISO-8601 (YYYY-MM-DD) form of an inmate's booking_date.

    Returns None when booking_date is empty or unparseable; the JSON-LD
    template suppresses the `dateCreated` key in that case so schema.org
    consumers see "no booking date known" rather than a malformed string.
    HCSO sentinel dates like "1/1/70" parse to a real 1970-01-01 ISO
    string, which is acceptable for schema.org (it's a real date even
    if it's a sentinel); downstream filtering of sentinels is unchanged.
    """
    dt = _parse_book_date(inmate.booking_date)
    return dt.date().isoformat() if dt is not None else None
