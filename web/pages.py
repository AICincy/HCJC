"""Page-rendering functions for the JCStream static site.

Each function renders one or more HTML pages from Jinja2 templates and writes
them to the output directory. Extracted from web/build.py for modularity.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment

from scraper.models import ChangeEvent, Inmate, Snapshot
from web.classify import (
    _expand_race,
    _expand_sex,
    _load_caselaw_cache,
    _load_explainers,
    _parse_bond_amount,
    _primary_tier,
    _tier_max,
)
from web.shape import (
    _court_calendar,
    _crimes_of_month,
    _days_in_custody,
    _statute_held_inmates,
    _tier_breakdown,
    _top_offenses_with_orc,
    _upcoming_courts,
)


def _filter_last_days(rows: list[dict], field_candidates: tuple[str, ...], days: int = 30) -> list[dict]:
    """Return rows whose date in one of ``field_candidates`` is within the
    last ``days`` days. Rows with unparseable dates are kept (defensive: the
    Socrata feeds occasionally ship a row with a NULL date and we'd rather
    surface it than silently drop it). Sorted newest-first.
    """
    from web.build import _parse_dispatch_dt
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
    parsed: list[tuple[datetime | None, dict]] = []
    for r in rows:
        dt = None
        for key in field_candidates:
            v = r.get(key)
            if v:
                dt = _parse_dispatch_dt(str(v))
                if dt:
                    break
        if dt is None or dt >= cutoff:
            parsed.append((dt, r))
    # Sort newest first; unparseable dates (None) go to the bottom.
    parsed.sort(key=lambda t: (t[0] is None, t[0] or datetime.min), reverse=True)
    return [r for _, r in parsed]


def _group_by_district(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group rows by CPD district (the 'district' field), preserving each
    group's input order (newest-first if the caller filtered+sorted).
    Districts are returned in CPD's natural numeric order (1..5), with the
    unknown / centralized districts ('C', 'UNK', '—') appended after.
    """
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = str(r.get("district") or "").strip() or "—"
        groups.setdefault(key, []).append(r)
    ordered: list[tuple[str, list[dict]]] = []
    for k in ("1", "2", "3", "4", "5"):
        if k in groups:
            ordered.append((k, groups.pop(k)))
    # Remaining keys (C, UNK, —, ...) sorted alphabetically at the end.
    for k in sorted(groups.keys()):
        ordered.append((k, groups[k]))
    return ordered


def _render_index(
    env: Environment,
    snapshot: Snapshot,
    by_month: list[tuple[str, list[Inmate]]],
    nav_months: list[dict],
    expanded_months: set,
    events_recent: list[ChangeEvent],
    recent_booked: int,
    recent_released: int,
    trend: dict,
    cfs_rows: list[dict],
    shooting_rows: list[dict],
    map_points: int,
    out_dir: Path,
) -> None:
    cfs_30d = _filter_last_days(
        cfs_rows, ("create_time_incident", "create_time_dispatch", "dispatch_time_primary_unit"),
        days=30,
    )
    shoot_30d = _filter_last_days(
        shooting_rows, ("datetimeoccured", "dateoccurred"),
        days=30,
    )
    page = env.get_template("index.html").render(
        snapshot=snapshot,
        by_month=by_month,
        nav_months=nav_months,
        expanded_months=expanded_months,
        events_recent=events_recent,
        recent_booked=recent_booked,
        recent_released=recent_released,
        trend=trend,
        cfs_rows=cfs_30d,
        shooting_rows=shoot_30d,
        cfs_by_district=_group_by_district(cfs_30d),
        shoot_by_district=_group_by_district(shoot_30d),
        map_points=map_points,
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def _load_crowdsourced_cases() -> dict[str, list[dict]]:
    """Read data/courtclerk_cases.json (populated via the case-data issue
    workflow) and index entries by inmate_number. Each inmate gets a list of
    submitted case records they're named on; the inmate.html template can
    then render them under a 'Submitted by readers' aside."""
    path = Path("data/courtclerk_cases.json")
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    entries = raw.get("cases", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    by_inmate: dict[str, list[dict]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("inmate_number") or entry.get("inmate")
        if key:
            by_inmate.setdefault(str(key), []).append(entry)
    return by_inmate


def _render_inmates(
    env: Environment,
    snapshot: Snapshot,
    matches: dict[str, list[dict]],
    events: list[ChangeEvent],
    out_dir: Path,
) -> None:
    template = env.get_template("inmate.html")
    events_by_inmate: dict[str, list[ChangeEvent]] = {}
    for e in events:
        events_by_inmate.setdefault(e.inmate_number, []).append(e)
    for ev_list in events_by_inmate.values():
        ev_list.sort(key=lambda e: e.timestamp_utc or "")
    crowdsourced = _load_crowdsourced_cases()
    for inm in snapshot.inmates:
        page = template.render(
            inmate=inm,
            snapshot=snapshot,
            cfs_matches=matches.get(inm.inmate_number, []),
            inmate_events=events_by_inmate.get(inm.inmate_number, []),
            crowdsourced_for_inmate=crowdsourced.get(inm.inmate_number, []),
        )
        target = out_dir / "inmate" / inm.inmate_number / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")


def _render_feeds(env: Environment, events: list[ChangeEvent], out_dir: Path) -> None:
    """Three RSS feeds: everything, bookings only, releases only.

    Each is the most recent ~50 matching events, newest first.
    """
    tmpl = env.get_template("feed.xml")

    def _write(name: str, title: str, desc: str, evs: list[ChangeEvent]) -> None:
        xml = tmpl.render(
            events=list(reversed(evs[-50:])),
            feed_title=title,
            feed_desc=desc,
            self_path="/" + name,
        )
        (out_dir / name).write_text(xml, encoding="utf-8")

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=21)

    def _recent_booked(e: ChangeEvent) -> bool:
        if e.event != "booked":
            return False
        if not (e.note or "").startswith("booked "):
            return True
        bd_str = e.note[len("booked "):].strip()
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(bd_str, fmt).date() >= cutoff
            except ValueError:
                continue
        return True

    _write("feed.xml", "JCStream changes",
           "New, updated, and released records on the Hamilton County, OH Justice Center public roster.",
           events)
    _write("booked.xml", "JCStream — new bookings",
           "People recently booked into the Hamilton County, OH Justice Center.",
           [e for e in events if _recent_booked(e)])
    _write("released.xml", "JCStream — releases",
           "People released from the Hamilton County, OH Justice Center public roster.",
           [e for e in events if e.event == "released"])


def _render_data_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Documentation + download index for the raw JSON the site is built from."""
    data_out = out_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    from scraper.open_data_feeds import FEEDS
    supplemental = [f.filename for f in FEEDS]
    for name in ("current.json", "changelog.json", "history.json", "cfs_recent.json",
                 "shootings_recent.json", "waf_block_log.json",
                 "cfs_pdi_recent.json", "courtclerk_cases.json", "orc_offenses.json",
                 *supplemental):
        src = Path("data") / name
        if src.exists():
            shutil.copy2(src, data_out / name)
    page = env.get_template("data.html").render(
        snapshot=snapshot,
        courtclerk_cases_available=(Path("data") / "courtclerk_cases.json").exists(),
    )
    (data_out / "index.html").write_text(page, encoding="utf-8")


def _compute_stats(snapshot: Snapshot, by_month) -> dict:
    """Aggregates for the /stats/ page — all from the current snapshot."""
    inmates = snapshot.inmates
    n = len(inmates)
    months = [(m, len(g)) for m, g in by_month]
    offenses = _crimes_of_month(inmates)
    tiers = {"felony": 0, "misdemeanor": 0, "other": 0}
    for inm in inmates:
        t = _primary_tier(inm)
        tiers[t["kind"] if t else "other"] += 1
    def _tally(attr, expand):
        out: dict[str, int] = {}
        for inm in inmates:
            out[expand(getattr(inm, attr, ""))] = out.get(expand(getattr(inm, attr, "")), 0) + 1
        return sorted(out.items(), key=lambda kv: -kv[1])
    sex = _tally("sex", _expand_sex)
    race = _tally("race", _expand_race)
    bond_vals = []
    zero_bond = 0
    for inm in inmates:
        total = 0
        any_amt = False
        for c in inm.charges:
            amt = _parse_bond_amount(c.bond_amount)
            if amt is not None:
                any_amt = True
                total += amt
        if any_amt:
            bond_vals.append(total)
            if total == 0:
                zero_bond += 1
    bond_vals.sort()
    median_bond = bond_vals[len(bond_vals)//2] if bond_vals else 0
    total_bond = sum(bond_vals)
    ch_counts = [len(inm.charges) for inm in inmates]
    avg_ch = (sum(ch_counts) / n) if n else 0
    max_ch = max(ch_counts) if ch_counts else 0
    one_charge = sum(1 for c in ch_counts if c == 1)
    with_photo = sum(1 for inm in inmates if inm.photo_filename)
    days = [d for inm in inmates if (d := _days_in_custody(inm)) is not None]
    avg_days = (sum(days) / len(days)) if days else 0
    max_days = max(days) if days else 0
    return {
        "n": n, "months": months, "offenses": offenses, "tiers": tiers,
        "sex": sex, "race": race,
        "bond_total": total_bond, "bond_median": median_bond, "bond_zero": zero_bond,
        "bond_known": len(bond_vals),
        "avg_charges": round(avg_ch, 1), "max_charges": max_ch, "one_charge": one_charge,
        "with_photo": with_photo, "no_photo": n - with_photo,
        "avg_days": round(avg_days), "max_days": max_days,
        "tier_breakdown": _tier_breakdown(snapshot),
        "top_offenses": _top_offenses_with_orc(snapshot, top_n=12),
        "court_calendar": _upcoming_courts(snapshot, days_ahead=14),
    }


def _render_stats_page(env: Environment, snapshot: Snapshot, by_month, trend: dict, out_dir: Path) -> None:
    stats = _compute_stats(snapshot, by_month)
    page = env.get_template("stats.html").render(snapshot=snapshot, s=stats, trend=trend)
    target = out_dir / "stats" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_court_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Aggregate every inmate's earliest upcoming court date into today /
    tomorrow / this-week / next-30-days buckets. Court-watchers and journalists
    get a docket view that the per-record pages cannot offer.
    """
    cal = _court_calendar(snapshot.inmates)
    now_eastern = datetime.now()
    page = env.get_template("court.html").render(
        snapshot=snapshot,
        cal=cal,
        now_eastern=now_eastern,
        one_day=timedelta(days=1),
    )
    target = out_dir / "court" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_visit_page(env: Environment, out_dir: Path) -> None:
    """Static visitation-policy info page. Links out to HCSO's authoritative
    policy; deliberately does NOT show visitation records (privacy creep)."""
    page = env.get_template("visit.html").render()
    target = out_dir / "visit" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_help_page(env: Environment, out_dir: Path) -> None:
    """Static "Get help" resources page. Mirrors current contact info for the
    free Hamilton County legal and crisis resources most relevant to people
    who land on JCStream looking for help. No data dependencies."""
    page = env.get_template("help.html").render()
    target = out_dir / "help" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_courts_page(env: Environment, out_dir: Path) -> None:
    """Static "Hamilton County court system" reference page. Mirrors directory
    and jurisdictional info from hamiltoncountycourts.org (Municipal +
    Common Pleas), probatect.org, and the Clerk of Courts. Distinct from
    /court/ which is the operational calendar of upcoming hearings."""
    page = env.get_template("courts.html").render()
    target = out_dir / "courts" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_statute_page(env: Environment, snapshot: Snapshot, offenses: dict, out_dir: Path) -> None:
    """Statute lookup -- one page with each ORC section currently on the roster."""
    explainers = _load_explainers()
    caselaw = _load_caselaw_cache()
    rows = _top_offenses_with_orc(snapshot, top_n=60, offenses=offenses)
    sections = []
    for r in rows:
        sections.append({
            **r,
            "tier_max": _tier_max(r["degree"]),
            "explainer": explainers.get(r["code"]),
            "held": _statute_held_inmates(snapshot, r["code"], limit=18),
            "caselaw": caselaw.get(r["code"], []),
        })
    page = env.get_template("statute.html").render(
        snapshot=snapshot,
        sections=sections,
        total_roster=snapshot.inmate_count,
    )
    target = out_dir / "statute" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
