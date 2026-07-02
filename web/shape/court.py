"""Court calendars, upcoming dockets, case grouping, and charge status summaries."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from scraper.models import Inmate, Snapshot
from web.classify import _parse_book_date, _parse_md_yy, _primary_tier, case_category, case_year

from .common import _now_naive_est


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


def _court_slippage(inmates: list[Inmate], now: datetime | None = None) -> dict:
    """Aggregate count of people still on the roster whose earliest listed
    court date has already passed.

    Aggregate-only by design: totals, a severity-tier breakdown, and the
    median days past, never a per-person list. The today boundary is
    midnight Eastern via ``_now_naive_est`` (injectable for tests); epoch
    sentinel dates ("1/1/70") are excluded by ``_parse_md_yy``. A passed
    court date can reflect a continuance, a capias, or HCSO data lag - the
    roster does not distinguish them, so this measures slippage of the
    listed date, not confirmed missed hearings.
    """
    if now is None:
        now = _now_naive_est()
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
        t = _primary_tier(inm)
        by_tier[t["label"] if t else "other"] += 1
    tiers = [{"label": lbl, "count": by_tier[lbl]} for lbl in _SLIPPAGE_TIER_ORDER if lbl in by_tier]
    tiers += [{"label": lbl, "count": n} for lbl, n in sorted(by_tier.items()) if lbl not in _SLIPPAGE_TIER_ORDER]
    return {
        "total": len(days_past),
        "median_days": round(statistics.median(days_past)) if days_past else 0,
        "tiers": tiers,
    }


def _next_court_date(inmate: Inmate) -> str:
    """Earliest upcoming (or any) court date among the charges, as printed by HCSO."""
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


def _court_calendar(inmates: list[Inmate]) -> dict:
    """Group inmates by their next upcoming court date into today / tomorrow /
    this week / next 30 days buckets. Each bucket entry is
    {inmate, date_text, parsed_date}. Sorted by date within each bucket.

    HCSO court dates are printed in local (Eastern) time; we compare on
    naive midnight of the build server's date, which can shift a single
    record by at most a few hours at the day boundary. Acceptable for a
    "today's docket" surface; not used for any decision-critical logic.
    """
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
    """Tidy a case number for display and linking. HCSO sometimes drops the
    leading court-prefix letter, leaving a stray leading slash ("/25/CRA/17789");
    strip leading/trailing slashes and whitespace so it reads "25/CRA/17789".
    Internal separators and any co-defendant suffix (".../B") are preserved."""
    return (cn or "").strip().strip("/").strip()


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
    """Group this inmate's case numbers by category then by year (newest first).

    Returns [{key, label, cases_n, years: [{year, cases: [num, ...]}]}] in a
    fixed category order. Years sort descending; unknown year sorts last. Each
    case number is left raw so the template deep-links it via cck_case_summary
    (the working courtclerk.org link).
    """
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
    """e.g. '3 pending · 1 disposed' across the charge rows."""
    pending = disposed = 0
    for c in inmate.charges:
        d = (c.disposition or "").strip()
        if not d or d.upper() in ("PENDING", "OPEN", ""):
            pending += 1
        else:
            disposed += 1
    parts = []
    if pending:
        parts.append(f"{pending} pending")
    if disposed:
        parts.append(f"{disposed} disposed")
    return " · ".join(parts)
