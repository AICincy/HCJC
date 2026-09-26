"""Court calendars, upcoming dockets, case grouping, and charge status summaries."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from scraper.models import Inmate, Snapshot
from web.classify import _charge_tier, _parse_book_date, _parse_md_yy, _primary_tier, case_category, case_year

from .common import _cached_offenses, _now_naive_est


def _upcoming_courts(snapshot: Snapshot, days_ahead: int = 14) -> list[dict]:
    """Group upcoming court dates across the roster into a [{date, weekday,
    items: [{inmate, charge}]}] list, day by day, for the stats calendar."""
    now = _now_naive_est()
    horizon = now + timedelta(days=days_ahead + 1)
    by_day: dict[datetime, list[dict]] = {}
    for inm in snapshot.inmates:
        for c in inm.charges:
            d = _parse_book_date((c.court_date or "").strip())
            if d is None:
                continue
            if d < (now - timedelta(days=1)) or d > horizon:
                continue
            key = d.replace(hour=0, minute=0, second=0, microsecond=0)
            by_day.setdefault(key, []).append({"inmate": inm, "charge": c})
    out = []
    for d in sorted(by_day.keys()):
        rows = by_day[d]
        out.append(
            {
                "date": d,
                "dnum": d.day,
                "dmon": d.strftime("%b %a"),
                "count": len(rows),
                "entries": rows[:6],
                "more": max(0, len(rows) - 6),
            }
        )
    return out


_SLIPPAGE_TIER_ORDER = ["F1", "F2", "F3", "F4", "F5", "F", "M1", "M2", "M3", "M4", "MM", "M"]


def _court_slippage(
    inmates: list[Inmate], now: datetime | None = None, offenses: dict | None = None
) -> dict:
    if now is None:
        now = _now_naive_est()
    if offenses is None:
        offenses = _cached_offenses()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_past: list[int] = []
    by_tier: dict[str, int] = defaultdict(int)
    for inm in inmates:
        earliest: datetime | None = None
        for c in inm.charges:
            dt = _parse_md_yy((c.court_date or "").strip())
            if dt is not None and (earliest is None or dt < earliest):
                earliest = dt
        if earliest is None or earliest >= today:
            continue
        days_past.append((today - earliest).days)
        t = _primary_tier(inm, offenses)
        if t:
            label = t["label"]
        else:
            labels = {(ct or {}).get("label") for ct in (_charge_tier(c, offenses) for c in inm.charges)}
            label = "F" if "F" in labels else ("M" if "M" in labels else "other")
        by_tier[label] += 1
    tiers = [{"label": lbl, "count": by_tier[lbl]} for lbl in _SLIPPAGE_TIER_ORDER if lbl in by_tier]
    tiers += [{"label": lbl, "count": n} for lbl, n in sorted(by_tier.items()) if lbl not in _SLIPPAGE_TIER_ORDER]
    return {
        "total": len(days_past),
        "median_days": round(statistics.median(days_past)) if days_past else 0,
        "tiers": tiers,
    }


def _next_court_date(inmate: Inmate) -> str:
    dates = []
    for c in inmate.charges:
        d = (c.court_date or "").strip()
        if not d:
            continue
        dt = _parse_md_yy(d)
        if dt:
            dates.append((dt, d))
    if not dates:
        return ""
    today = _now_naive_est()
    future = sorted(d for d in dates if d[0] >= today)
    if future:
        return future[0][1]
    return sorted(dates, reverse=True)[0][1]


def _next_court_date_is_past(inmate: Inmate) -> bool:
    raw = _next_court_date(inmate)
    if not raw:
        return False
    dt = _parse_md_yy(raw)
    return dt is not None and dt < _now_naive_est()


def _court_calendar(inmates: list[Inmate]) -> dict:
    today = _now_naive_est().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)
    month_end = today + timedelta(days=30)

    buckets: dict[str, list[dict]] = {"today": [], "tomorrow": [], "this_week": [], "this_month": []}
    for inm in inmates:
        soonest: tuple[datetime, str] | None = None
        for c in inm.charges:
            d = (c.court_date or "").strip()
            if not d:
                continue
            dt = _parse_md_yy(d)
            if not dt or dt < today:
                continue
            if soonest is None or dt < soonest[0]:
                soonest = (dt, d)
        if not soonest:
            continue
        dt, date_text = soonest
        entry = {"inmate": inm, "date_text": date_text, "parsed_date": dt}
        if dt < tomorrow:
            buckets["today"].append(entry)
        elif dt < tomorrow + timedelta(days=1):
            buckets["tomorrow"].append(entry)
        elif dt < week_end:
            buckets["this_week"].append(entry)
        elif dt < month_end:
            buckets["this_month"].append(entry)

    for k in buckets:
        buckets[k].sort(key=lambda e: (e["parsed_date"], e["inmate"].full_name))
    return buckets


def _clean_case_number(cn: str | None) -> str:
    """Tidy a case number for display and linking.

    City municipal cases from HCSO start with a slash (``/26/CRB/19119``).
    That leading slash is required by courtclerk.org and must be kept.
    Trailing whitespace is stripped. Charge suffixes stay visible in the
    label; the clerk URL builder drops them.
    """
    return (cn or "").strip()


def _case_numbers(inmate: Inmate) -> list[str]:
    seen, out = set(), []
    for c in inmate.charges:
        for v in (c.common_pleas_case, c.municipal_case, c.other_case):
            v = (v or "").strip()
            if v and v not in seen:
                seen.add(v)
                out.append(v)
    return out


_CASE_CAT_ORDER = ("criminal", "traffic", "civil", "other")
_CASE_CAT_LABEL = {"criminal": "Criminal", "traffic": "Traffic", "civil": "Civil", "other": "Other"}


def _cases_grouped(inmate: Inmate) -> list[dict]:
    buckets: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for cn in _case_numbers(inmate):
        buckets[case_category(cn)][case_year(cn)].append(cn)
    out: list[dict] = []
    for cat in _CASE_CAT_ORDER:
        years = buckets.get(cat)
        if not years:
            continue
        ordered = sorted(years.keys(), key=lambda y: (y is None, -(y or 0)))
        year_rows = [{"year": (y if y is not None else "-"), "cases": years[y]} for y in ordered]
        out.append(
            {
                "key": cat,
                "label": _CASE_CAT_LABEL[cat],
                "cases_n": sum(len(years[y]) for y in years),
                "years": year_rows,
            }
        )
    return out


def _charge_status_summary(inmate: Inmate) -> str:
    pending = disposed = 0
    for c in inmate.charges:
        d = (c.disposition or "").strip()
        if not d or d.upper() in ("PENDING", "OPEN"):
            pending += 1
        else:
            disposed += 1
    parts = []
    if pending:
        parts.append(f"{pending} pending")
    if disposed:
        parts.append(f"{disposed} disposed")
    return " · ".join(parts)
