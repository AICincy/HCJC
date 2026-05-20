"""Per-inmate / per-snapshot view-model helpers registered as Jinja globals
in web/build.py. Each function returns dicts / lists / scalars that templates
consume directly — no further computation in the .html files. Imports
classify.py for the pure helpers + reference data; no circular dep.

This module's contract is the env.globals[] keys at the bottom of build.py:
adding a helper here requires registering it there with the same name.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from scraper import orc as orc_mod
from scraper.models import ChangeEvent, Inmate, Snapshot
from web.classify import (
    _CLS_RANK,
    _DEGREE_RE,
    _MIN_MONTH_SIZE,
    _chap_slug,
    _charge_tier,
    _offense_for_code,
    _parse_bond_amount,
    _parse_book_date,
    _parse_md_yy,
    _primary_degree,
    _primary_tier,
)


def _strftime_nopad(dt, fmt: str) -> str:
    """strftime that honors %-d / %-m on Windows by mapping to %#d / %#m.
    POSIX systems pass the format through unchanged. Keeps date rendering
    portable between the GitHub Actions Linux runner and Windows dev boxes.
    """
    if sys.platform == "win32":
        fmt = fmt.replace("%-", "%#")
    return dt.strftime(fmt)


def _related_inmates(target: Inmate, all_inmates: list[Inmate], limit: int = 6) -> list[Inmate]:
    """Other inmates in custody whose primary ORC chapter matches the target's."""
    target_chap = _primary_chapter(target)
    if not target_chap:
        return []
    target_label = target_chap["label"]
    out: list[Inmate] = []
    for inm in all_inmates:
        if inm.inmate_number == target.inmate_number:
            continue
        chap = _primary_chapter(inm)
        if chap and chap["label"] == target_label:
            out.append(inm)
            if len(out) >= limit:
                break
    return out

def _crimes_of_month(group: list[Inmate]) -> list[dict]:
    """Return [{label, cls, count}] for the month's crimes by primary offense
    category, sorted by count descending then label. Used in each month-section
    header (top few inline, the rest behind a 'show all' toggle)."""
    counts: dict[tuple[str, str], int] = {}
    for inm in group:
        chap = _primary_chapter(inm)
        if not chap:
            continue
        key = (chap["label"], chap["cls"])
        counts[key] = counts.get(key, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0]))
    return [{"label": k[0], "cls": k[1], "count": v} for k, v in items]

def _recent_booked_inmates(snapshot: Snapshot, n: int = 6) -> list[Inmate]:
    """Most-recently-booked inmates by HCSO booking_date (descending), N max."""
    arr = list(snapshot.inmates)
    arr.sort(key=lambda i: _parse_book_date(i.booking_date) or datetime.min, reverse=True)
    return arr[:n]

def _bond_context(target: Inmate, all_inmates: list[Inmate], offenses: dict | None = None) -> dict | None:
    """Percentile distribution of bond amounts across current peers charged
    under the target inmate's most-severe ORC section. Returns None when there
    aren't enough peers to draw a meaningful distribution (<5)."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    # Pick the target's most-severe ORC code (lowest degree rank) with a bond.
    order = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    primary = None
    primary_idx = 99
    my_bond = None
    for c in target.charges:
        code = orc_mod.normalize_code((c.orc_code or "").strip())
        if not code or code.upper() == "NONE":
            continue
        m = _DEGREE_RE.search((c.description or "").strip())
        deg = m.group(1) if m else orc_mod.degree_for(code, offenses)
        idx = order.index(deg) if deg in order else 99
        if idx < primary_idx:
            primary, primary_idx = c, idx
            my_bond = _parse_bond_amount(c.bond_amount)
    if not primary:
        return None
    primary_code = orc_mod.normalize_code((primary.orc_code or "").strip())
    if not primary_code:
        return None
    # Collect peer bond amounts (any positive bond, exclude $0 / NONE / blank).
    peers: list[int] = []
    for inm in all_inmates:
        if inm.inmate_number == target.inmate_number:
            continue
        for c in inm.charges:
            if orc_mod.normalize_code((c.orc_code or "").strip()) != primary_code:
                continue
            v = _parse_bond_amount(c.bond_amount)
            if v is not None and v > 0:
                peers.append(v)
                break  # one bond per peer for this stat
    if len(peers) < 5:
        return None
    peers.sort()
    def _pct(p: float) -> int:
        idx = max(0, min(len(peers) - 1, int(round((len(peers) - 1) * p))))
        return peers[idx]
    p10, p25, p50, p75, p90 = (_pct(x) for x in (0.10, 0.25, 0.50, 0.75, 0.90))
    my_percentile = None
    if my_bond is not None and my_bond > 0:
        below = sum(1 for v in peers if v < my_bond)
        my_percentile = below / len(peers)
    return {
        "code": primary_code,
        "title": orc_mod.title_for(primary_code, offenses),
        "min": peers[0], "max": peers[-1],
        "p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90,
        "peer_count": len(peers),
        "my_bond": my_bond,
        "my_percentile": my_percentile,
    }

def _upcoming_courts(snapshot: Snapshot, days_ahead: int = 14) -> list[dict]:
    """Group upcoming court dates across the roster into a [{date, weekday,
    items: [{inmate, charge}]}] list, day by day, for the stats calendar."""
    now = datetime.now()
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
        out.append({
            "date": d,
            "dnum": d.day,
            "dmon": d.strftime("%b %a"),
            "count": len(rows),
            "entries": rows[:6],
            "more": max(0, len(rows) - 6),
        })
    return out

def _tier_breakdown(snapshot: Snapshot, offenses: dict | None = None) -> dict[str, int]:
    """Per-tier (F1..MM, UNK) counts: each inmate's most-severe degree."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    counts: dict[str, int] = {t: 0 for t in ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]}
    counts["UNK"] = 0
    for inm in snapshot.inmates:
        deg = _primary_degree(inm, offenses)
        if deg in counts:
            counts[deg] += 1
        else:
            counts["UNK"] += 1
    return counts

def _top_offenses_with_orc(snapshot: Snapshot, top_n: int = 12, offenses: dict | None = None) -> list[dict]:
    """Top-N ORC sections on the roster, with title + degree + count + share."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    counts: dict[str, int] = {}
    for inm in snapshot.inmates:
        seen: set[str] = set()
        for c in inm.charges:
            code = orc_mod.normalize_code((c.orc_code or "").strip())
            if not code or code.upper() == "NONE" or code in seen:
                continue
            seen.add(code)
            counts[code] = counts.get(code, 0) + 1
    n = max(1, len(snapshot.inmates))
    rows = []
    for code, count in sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]:
        title = orc_mod.title_for(code, offenses) or ""
        deg = orc_mod.degree_for(code, offenses) or "UNK"
        rows.append({
            "code": code,
            "title": title,
            "degree": deg,
            "count": count,
            "pct": 100.0 * count / n,
        })
    return rows

def _all_top_offenses(snapshot: Snapshot, offenses: dict | None = None) -> list[dict]:
    """Like _top_offenses_with_orc but unbounded — used for the statute page."""
    return _top_offenses_with_orc(snapshot, top_n=10_000, offenses=offenses)

def _timeline_markers(inmate: Inmate) -> dict | None:
    """Markers for the time-in-custody timeline: Booked, each court date,
    Today, and projected release. Returns {markers, start, end, total_days}
    or None if there's no booking date to anchor on."""
    booked = _parse_book_date((inmate.booking_date or "").strip())
    if booked is None:
        return None
    now = datetime.now()
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
    for d, desc, _code in courts:
        raw.append({
            "x": _pct(d),
            "label": "Court",
            "date": _strftime_nopad(d, "%-m/%-d/%y") if hasattr(d, "strftime") else "",
            "kind": "court",
            "sub": (desc or "").lower()[:48],
        })
    raw.append({"x": _pct(now), "label": "Today", "date": _strftime_nopad(now, "%b %-d, %Y"), "kind": "now", "sub": ""})
    if release:
        raw.append({"x": _pct(release), "label": "Projected release", "date": inmate.projected_release_date or "", "kind": "release", "sub": ""})
    raw.sort(key=lambda m: m["x"])
    last_x = -1e9
    side = "below"
    for m in raw:
        # Markers closer than 12% alternate above/below to avoid label
        # overlap; a well-separated marker resets to below.
        if m["x"] - last_x >= 12.0:
            side = "below"
        elif side == "below":
            side = "above"
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

def _similar_by_statute(target: Inmate, all_inmates: list[Inmate], offenses: dict | None = None, limit: int = 6) -> list[Inmate]:
    """Other inmates in custody charged under the target's most-severe ORC base
    code. Falls back to chapter-level match when fewer than 3 peers exist."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    order = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    primary_code = None
    primary_idx = 99
    for c in target.charges:
        code = orc_mod.normalize_code((c.orc_code or "").strip())
        if not code or code.upper() == "NONE":
            continue
        m = _DEGREE_RE.search((c.description or "").strip())
        deg = m.group(1) if m else orc_mod.degree_for(code, offenses)
        idx = order.index(deg) if deg in order else 99
        if idx < primary_idx:
            primary_code = code
            primary_idx = idx
    if not primary_code:
        return []
    out: list[Inmate] = []
    for inm in all_inmates:
        if inm.inmate_number == target.inmate_number:
            continue
        if any(orc_mod.normalize_code((c.orc_code or "").strip()) == primary_code for c in inm.charges):
            out.append(inm)
            if len(out) >= limit:
                break
    if len(out) >= 3:
        return out
    # Fallback: chapter-level match through the existing related lookup.
    return _related_inmates(target, all_inmates, limit=limit)

def _statute_held_inmates(snapshot: Snapshot, code: str, limit: int = 24) -> list[Inmate]:
    """Inmates currently charged under a given ORC base code, capped at limit."""
    code_norm = orc_mod.normalize_code(code)
    out: list[Inmate] = []
    for inm in snapshot.inmates:
        for c in inm.charges:
            if orc_mod.normalize_code((c.orc_code or "").strip()) == code_norm:
                out.append(inm)
                break
        if len(out) >= limit:
            break
    return out

def _feed_description(event: str, name: str, inmate_number: str, note: str) -> str:
    """Build a readable per-item <description> for the RSS feeds. The template
    previously rendered "{event} {note}" verbatim, which produced strings like
    "released no longer on HCSO public roster" - grammatical noise. This shapes
    each event type into a complete sentence."""
    nm = (name or "Unknown").strip()
    n = (note or "").strip()
    if event == "booked":
        if n.startswith("booked "):
            return f"{nm} (#{inmate_number}) was {n} into the Hamilton County Justice Center."
        return f"{nm} (#{inmate_number}) was booked into the Hamilton County Justice Center."
    if event == "released":
        return f"{nm} (#{inmate_number}) is no longer on the HCSO public roster."
    if event == "updated":
        return f"{nm} (#{inmate_number}): record updated{(' — ' + n) if n else ''}."
    return f"{nm} (#{inmate_number}): {event}{(' — ' + n) if n else ''}."

def _bond_by_tier(inmate: Inmate, offenses: dict | None = None) -> dict:
    """Sum bond amounts split by charge tier. Returns {felony, misdemeanor, other, total}."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    out = {"felony": 0, "misdemeanor": 0, "other": 0}
    for c in inmate.charges:
        amt = _parse_bond_amount(c.bond_amount)
        if amt is None:
            continue
        ct = _charge_tier(c, offenses)
        key = ct["kind"] if ct else "other"
        out[key] = out.get(key, 0) + amt
    out["total"] = out["felony"] + out["misdemeanor"] + out["other"]
    return {k: (f"${v:,}" if v else "$0") for k, v in out.items()}

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
    today = datetime.now()
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
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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


def _events_for_inmate(events: list[ChangeEvent], inmate_number: str) -> list[ChangeEvent]:
    """Return the chronological list of changelog events for one inmate,
    oldest first. Empty list if the inmate has no events on file.
    """
    if not inmate_number:
        return []
    out = [e for e in events if e.inmate_number == inmate_number]
    out.sort(key=lambda e: e.timestamp_utc or "")
    return out

def _case_numbers(inmate: Inmate) -> list[str]:
    seen, out = set(), []
    for c in inmate.charges:
        for v in (c.common_pleas_case, c.municipal_case, c.other_case):
            v = (v or "").strip()
            if v and v not in seen:
                seen.add(v)
                out.append(v)
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

def _card_data_attrs(inmate: Inmate) -> dict:
    """Return data-* values for client-side filtering / search on the cards."""
    tier = _primary_tier(inmate)
    chap = _primary_chapter(inmate)
    orc_codes = " ".join((c.orc_code or "") for c in inmate.charges)
    charges_txt = " ".join((c.description or "") for c in inmate.charges)
    return {
        "tier": tier["kind"] if tier else "unknown",
        "chap": _chap_slug(chap["label"]) if chap else "unknown",
        "name": (inmate.full_name or "").lower(),
        "search": f"{inmate.full_name} {charges_txt} {orc_codes} #{inmate.inmate_number}".lower(),
    }

def _card_tip(inmate: Inmate, offenses: dict | None = None, max_rows: int = 12) -> str:
    """Newline-joined tooltip payload for a card's tier badge.

    Line 0 is the tier label ("FELONY ×2"); each later line is one charge as
    ``CODE · DEGREE · ORC-title-or-description``. The card template drops this
    into ``data-tip`` and the shared #tier-tip element renders it on hover/focus
    — so cards carry no nested tooltip DOM (≈8 fewer nodes each over 1k+ cards,
    and nothing for content-visibility:auto to clip).
    """
    if offenses is None:
        offenses = orc_mod.load_offenses()
    t = _primary_tier(inmate)
    lines = [t["label"] if t else "—"]
    rows = 0
    for c in inmate.charges:
        code = (c.orc_code or "").strip()
        if code.upper() == "NONE":
            code = ""
        desc = (c.description or "").strip()
        if desc.upper() == "NONE":
            desc = ""
        if not code and not desc and not (c.common_pleas_case or "").strip() and not (c.municipal_case or "").strip():
            continue
        if rows >= max_rows:
            extra = len(inmate.charges) - rows
            if extra > 0:
                lines.append(f"+{extra} more charge{'' if extra == 1 else 's'}")
            break
        ct = _charge_tier(c, offenses)
        title = orc_mod.title_for(code, offenses) if code else ""
        last = title or desc
        if len(last) > 56:
            last = last[:55].rstrip() + "…"
        bits = [b for b in (code or "—", (ct["label"] if ct else ""), last) if b]
        lines.append(" · ".join(bits) if bits else "—")
        rows += 1
    return "\n".join(lines)

def _bond_total(inmate: Inmate) -> str:
    """Sum the inmate's bond amounts where parseable, return a formatted string."""
    total = 0
    for c in inmate.charges:
        total += _parse_bond_amount(c.bond_amount) or 0
    return f"${total:,}" if total else ""

def _days_in_custody(inmate: Inmate) -> int | None:
    bd = None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            bd = datetime.strptime((inmate.booking_date or "").strip(), fmt)
            break
        except ValueError:
            continue
    if bd is None:
        return None
    days = (datetime.now() - bd).days
    # Reject sentinel dates from upstream (e.g. epoch-era "1/1/70") that yield
    # tens of thousands of days. Nobody is in pretrial custody for 15+ years;
    # show no days-ago count rather than a nonsense one.
    if days < 0 or days > 5475:  # 15 * 365
        return None
    return days

def _charges_by_chapter(inmate: Inmate) -> list[dict]:
    """Return [{label, cls, count}] for this inmate's charges by offense category."""
    counts: dict[tuple[str, str], int] = {}
    for c in inmate.charges:
        off = _offense_for_code(c.orc_code)
        if not off:
            continue
        key = (off["label"], off["cls"])
        counts[key] = counts.get(key, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0]))
    return [{"label": k[0], "cls": k[1], "count": v} for k, v in items]

def _primary_charge_obj(inmate: Inmate):
    """Return the inmate's most-serious charge object (or None).

    'Most serious' ranks by offense-category severity, then by tier
    (felony before misdemeanor), then by charge order. The displayed
    charge text AND its color both derive from this one charge so they
    can never disagree (which was making 'ASSAULT' show in homicide-red
    because some *other* charge was the worst).
    """
    best = None
    best_key = (99, 9)  # (category-rank, tier-rank)
    for c in inmate.charges:
        off = _offense_for_code(c.orc_code)
        if not off:
            continue
        cat_rank = _CLS_RANK.get(off["cls"], 9)
        ct = _charge_tier(c)
        tier_rank = 0 if (ct and ct["kind"] == "felony") else (1 if ct else 2)
        key = (cat_rank, tier_rank)
        if key < best_key:
            best, best_key = c, key
    return best

def _primary_charge(inmate: Inmate) -> str:
    """Best single-line description for the inmate's top charge."""
    c = _primary_charge_obj(inmate)
    if c is not None and c.description and c.description.upper() != "NONE":
        return c.description
    # Fallbacks: any real description, then any ORC code, then the category.
    for c2 in inmate.charges:
        if c2.description and c2.description.upper() != "NONE":
            return c2.description
    if c is not None:
        off = _offense_for_code(c.orc_code)
        if off:
            return off["label"].upper()
    return ""

def _primary_chapter(inmate: Inmate) -> dict | None:
    """Return ``{label, cls}`` for the inmate's most-serious offense category —
    derived from the SAME charge as _primary_charge, so text and color agree."""
    c = _primary_charge_obj(inmate)
    if c is None:
        return None
    return _offense_for_code(c.orc_code)

def _sort_in_group(group: list[Inmate]) -> list[Inmate]:
    """Newest first: by booking number (sequential YYNNNNNN), then admit date, then name."""
    def _key(i):
        try:
            bn = int(i.booking_number) if i.booking_number else 0
        except ValueError:
            bn = 0
        dt = _parse_md_yy(i.booking_date) or datetime(1970, 1, 1)
        return (-bn, -dt.toordinal(), i.last_name, i.first_name)
    return sorted(group, key=_key)

def _group_by_month(inmates: list[Inmate]) -> list[tuple[str, list[Inmate]]]:
    """Return list of (month_label, [inmates]) sorted newest-first. Months with
    fewer than _MIN_MONTH_SIZE people — plus anyone with an unparseable booking
    date — are folded into one trailing "Earlier bookings" section so the roster
    doesn't end in a long tail of one-person 'sections'."""
    buckets: dict[tuple[int, int], list[Inmate]] = defaultdict(list)
    no_date: list[Inmate] = []
    for inm in inmates:
        dt = _parse_md_yy(inm.booking_date)
        if dt is None or dt.year < 2015:    # 2015 cutoff also catches the '1/1/70'-style junk
            no_date.append(inm)
            continue
        buckets[(dt.year, dt.month)].append(inm)
    big = {k: v for k, v in buckets.items() if len(v) >= _MIN_MONTH_SIZE}
    tail: list[Inmate] = list(no_date)
    for k, v in buckets.items():
        if k not in big:
            tail.extend(v)
    out: list[tuple[str, list[Inmate]]] = []
    for k in sorted(big.keys(), reverse=True):
        y, m = k
        out.append((datetime(y, m, 1).strftime("%B %Y"), _sort_in_group(big[k])))
    if tail:
        out.append((f"Earlier bookings ({len(tail)})", _sort_in_group(tail)))
    return out

def _events_in_window(events: list[ChangeEvent], hours: int) -> list[ChangeEvent]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    keep: list[ChangeEvent] = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.timestamp_utc.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if ts >= cutoff:
            keep.append(e)
    return keep

def _events_for_recent(events: list[ChangeEvent], hours: int = 8) -> list[ChangeEvent]:
    """Recent activity feed: events JCStream observed within the window,
    AND for 'booked' events, the actual HCSO booking date must also be within
    the window. Without that second check the first-ever sweep seeds the feed
    with hundreds of 'booked' events for inmates who were actually booked
    weeks or months ago.
    """
    cutoff_ts = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_date = cutoff_ts.date()
    out: list[ChangeEvent] = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.timestamp_utc.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if ts < cutoff_ts:
            continue
        if e.event == "booked" and e.note.startswith("booked "):
            bd_str = e.note[len("booked "):].strip()
            bd = None
            for fmt in ("%m/%d/%y", "%m/%d/%Y"):
                try:
                    bd = datetime.strptime(bd_str, fmt).date()
                    break
                except ValueError:
                    continue
            if bd is not None and bd < cutoff_date:
                continue
        out.append(e)
    return out
