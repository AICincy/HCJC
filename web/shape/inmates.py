"""Inmate-level shaping: primary charge/chapter, card rendering, grouping,
similar inmates, roster staleness, and the full prepare_render_data pipeline."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from scraper import orc as orc_mod
from scraper.models import ChangeEvent, Inmate, Snapshot
from web.classify import (
    _CLS_RANK,
    _DEGREE_RE,
    _MIN_MONTH_SIZE,
    _chap_slug,
    _charge_tier,
    _offense_for_code,
    _parse_book_date,
    _parse_md_yy,
    _primary_chapter,
    _primary_tier,
    _short_month_label,
)

from .common import RosterIndexes, _cached_offenses


def _related_inmates(
    target: Inmate,
    all_inmates: list[Inmate],
    limit: int = 6,
    indexes: RosterIndexes | None = None,
) -> list[Inmate]:
    """Other inmates in custody whose primary ORC chapter matches the target's."""
    target_chap = _primary_chapter(target)
    if not target_chap:
        return []
    target_label = target_chap["label"]
    if indexes is not None:
        candidates = indexes.by_chapter.get(target_label, [])
        return [i for i in candidates if i.inmate_number != target.inmate_number][:limit]
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


def _similar_by_statute(
    target: Inmate,
    all_inmates: list[Inmate],
    offenses: dict | None = None,
    limit: int = 6,
    indexes: RosterIndexes | None = None,
) -> list[Inmate]:
    """Other inmates in custody charged under the target's most-severe ORC base
    code. Falls back to chapter-level match when fewer than 3 peers exist."""
    if offenses is None:
        offenses = _cached_offenses()
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
    if indexes is not None:
        candidates = indexes.by_code.get(primary_code, [])
        matched = [i for i in candidates if i.inmate_number != target.inmate_number][:limit]
        if len(matched) >= 3:
            return matched
        return _related_inmates(target, all_inmates, limit=limit, indexes=indexes)
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


def _card_data_attrs(inmate: Inmate) -> dict:
    """Return data-* values for client-side filtering / search on the cards."""
    tier = _primary_tier(inmate)
    chap = _primary_chapter(inmate)
    orc_codes = " ".join((c.orc_code or "") for c in inmate.charges)
    charges_txt = " ".join((c.description or "") for c in inmate.charges)
    return {
        "tier": tier["kind"] if tier else "unknown",
        "chap": _chap_slug(chap["label"]) if chap else "unknown",
        "search": f"{inmate.full_name} {charges_txt} {orc_codes} #{inmate.inmate_number}".lower(),
    }


def _card_tip(inmate: Inmate, offenses: dict | None = None, max_rows: int = 12) -> str:
    """Newline-joined tooltip payload for a card's tier badge.

    Line 0 is the tier label ("FELONY ×2"); each later line is one charge as
    ``CODE · DEGREE · ORC-title-or-description``. The card template drops this
    into ``data-tip`` and the shared #tier-tip element renders it on hover/focus
    - so cards carry no nested tooltip DOM (≈8 fewer nodes each over 1k+ cards,
    and nothing for content-visibility:auto to clip).
    """
    if offenses is None:
        offenses = _cached_offenses()
    t = _primary_tier(inmate)
    lines = [t["label"] if t else "-"]
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
        bits = [b for b in (code or "-", (ct["label"] if ct else ""), last) if b]
        lines.append(" · ".join(bits) if bits else "-")
        rows += 1
    return "\n".join(lines)


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
    fewer than _MIN_MONTH_SIZE people - plus anyone with an unparseable booking
    date - are folded into one trailing "Earlier bookings" section so the roster
    doesn't end in a long tail of one-person 'sections'."""
    buckets: dict[tuple[int, int], list[Inmate]] = defaultdict(list)
    no_date: list[Inmate] = []
    for inm in inmates:
        dt = _parse_md_yy(inm.booking_date)
        if dt is None or dt.year < 2015:  # 2015 cutoff also catches the '1/1/70'-style junk
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


def _roster_stale_context(snapshot: Snapshot) -> dict:
    """Staleness / transparency context for templates. ``blocked`` is True once
    the last-good roster is older than the freeze-alarm threshold, which
    (verified 2026-05-19 onward) means HCSO's WAF is denying this site's
    automated public-records retrieval. ``since`` is the first recorded block
    date from the durable evidence log; ``ever_blocked`` keeps the Data-page
    documentation present after recovery."""
    from scraper.store import load_block_log
    from scraper.sweep_guards import ROSTER_STALE_ALARM_HOURS, roster_stale_hours

    hours = roster_stale_hours(snapshot.generated_utc)
    log = load_block_log()
    since = None
    for rec in log:
        if rec.get("event") == "blocked":
            ts = rec.get("timestamp_utc") or ""
            since = ts[:10] if ts else None
            break
    return {
        "hours": round(hours, 1) if hours is not None else None,
        "blocked": hours is not None and hours >= ROSTER_STALE_ALARM_HOURS,
        "since": since,
        "ever_blocked": any(r.get("event") == "blocked" for r in log),
        "last_updated": (snapshot.generated_utc or "")[:10],
    }


def _prepare_render_data(snapshot: Snapshot, events: list[ChangeEvent]) -> dict:
    """Compute the month grouping, month-nav data, recent-event counts and
    trend that the page renderers consume. Returned as a dict so build() can
    pass the pieces to the individual _render_* calls."""
    from web.history import _update_history

    from .feeds import _events_for_recent

    by_month = _group_by_month(snapshot.inmates)
    # Month-nav data: short label + count.
    nav_months = [
        {"slug": m.replace(" ", "-").lower(), "label": _short_month_label(m), "count": len(g)} for m, g in by_month
    ]
    # Only the newest month renders expanded; older ones collapsed by default.
    expanded_months = {m for m, _ in by_month[:1]}
    # "in the last 24h" must mean the EVENT happened in the last 24h AND (for
    # 'booked') the HCSO booking date is recent too - otherwise the first-ever
    # sweep counts every inmate it ever saw as "booked in the last 24h".
    recent_24h = _events_for_recent(events, hours=24)
    recent_booked = sum(1 for e in recent_24h if e.event == "booked")
    recent_released = sum(1 for e in recent_24h if e.event == "released")
    events_recent = list(reversed(_events_for_recent(events, hours=8)))[:12]
    trend = _update_history(snapshot, recent_booked, recent_released)
    return {
        "by_month": by_month,
        "nav_months": nav_months,
        "expanded_months": expanded_months,
        "recent_booked": recent_booked,
        "recent_released": recent_released,
        "events_recent": events_recent,
        "trend": trend,
    }


def _warn_about_unmapped_orcs(inmates: list[Inmate], offenses: dict[str, dict]) -> None:
    logger = logging.getLogger("jcstream.site")
    codes = [c.orc_code for inm in inmates for c in inm.charges if c.orc_code]
    missing = orc_mod.codes_without_titles(codes, offenses)
    missing = [c for c in missing if not c.startswith(("0000", "0001", "0002"))]
    if missing:
        logger.info("ORC titles missing for %d codes: %s", len(missing), ", ".join(missing[:20]))
