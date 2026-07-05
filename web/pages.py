"""Page-rendering functions for the JCStream static site.

Each function renders one or more HTML pages from Jinja2 templates and writes
them to the output directory. Extracted from web/build.py for modularity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment

from scraper.client import DEFAULT_UA
from scraper.models import ChangeEvent, Inmate, Snapshot
from scraper.open_data_feeds import FEEDS
from scraper.photos import downscale_and_save
from scraper.store import load_block_log
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
    BOND_DISPARITY_MIN_N,
    RosterIndexes,
    _bond_disparity,
    _court_calendar,
    _court_slippage,
    _crimes_of_month,
    _days_in_custody,
    _statute_held_inmates,
    _tier_breakdown,
    _top_offenses_with_orc,
    _upcoming_courts,
)
from web.transparency import compute_transparency_metrics


def _extract_row_dt(row: dict, field_candidates: tuple[str, ...]) -> datetime | None:
    """Try each candidate field in order, returning the first parseable datetime."""
    from web.classify import parse_dispatch_dt

    for key in field_candidates:
        v = row.get(key)
        if v:
            dt = parse_dispatch_dt(str(v))
            if dt:
                return dt
    return None


def _filter_last_days(rows: list[dict], field_candidates: tuple[str, ...], days: int = 30) -> list[dict]:
    """Return rows whose date in one of ``field_candidates`` is within the
    last ``days`` days. Rows with unparseable dates are kept (defensive: the
    Socrata feeds occasionally ship a row with a NULL date and we'd rather
    surface it than silently drop it). Sorted newest-first.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
    parsed: list[tuple[datetime | None, dict]] = []
    for r in rows:
        dt = _extract_row_dt(r, field_candidates)
        if dt is None or dt >= cutoff:
            parsed.append((dt, r))
    parsed.sort(key=lambda t: (t[0] is None, t[0] or datetime.min), reverse=True)
    return [r for _, r in parsed]


def _group_by_district(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group rows by CPD district (the 'district' field), preserving each
    group's input order (newest-first if the caller filtered+sorted).
    Districts are returned in CPD's natural numeric order (1..5), with the
    unknown / centralized districts ('C', 'UNK', '-') appended after.
    """
    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = str(r.get("district") or "").strip() or "-"
        groups.setdefault(key, []).append(r)
    ordered: list[tuple[str, list[dict]]] = []
    for k in ("1", "2", "3", "4", "5"):
        if k in groups:
            ordered.append((k, groups.pop(k)))
    # Remaining keys (C, UNK, -, ...) sorted alphabetically at the end.
    for k in sorted(groups.keys()):
        ordered.append((k, groups[k]))
    return ordered


@dataclass
class IndexContext:
    """Bundle of pre-computed data for the index page template."""

    snapshot: Snapshot
    by_month: list[tuple[str, list[Inmate]]]
    nav_months: list[dict]
    expanded_months: set
    recent_booked: int
    recent_released: int
    trend: dict
    cfs_rows: list[dict]
    shooting_rows: list[dict]
    map_points: int


def _render_index(env: Environment, ctx: IndexContext, out_dir: Path) -> None:
    cfs_30d = _filter_last_days(
        ctx.cfs_rows,
        ("create_time_incident", "create_time_dispatch", "dispatch_time_primary_unit"),
        days=30,
    )
    shoot_30d = _filter_last_days(
        ctx.shooting_rows,
        ("datetimeoccured", "dateoccurred"),
        days=30,
    )
    page = env.get_template("index.html").render(
        snapshot=ctx.snapshot,
        by_month=ctx.by_month,
        nav_months=ctx.nav_months,
        expanded_months=ctx.expanded_months,
        recent_booked=ctx.recent_booked,
        recent_released=ctx.recent_released,
        trend=ctx.trend,
        cfs_rows=cfs_30d,
        shooting_rows=shoot_30d,
        cfs_by_district=_group_by_district(cfs_30d),
        shoot_by_district=_group_by_district(shoot_30d),
        map_points=ctx.map_points,
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

    def _render_one(inm: Inmate) -> None:
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

    workers = min(os.cpu_count() or 1, len(snapshot.inmates), 8)
    if workers <= 1 or len(snapshot.inmates) <= 4:
        for inm in snapshot.inmates:
            _render_one(inm)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_render_one, snapshot.inmates))


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
        bd_str = e.note[len("booked ") :].strip()
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(bd_str, fmt).date() >= cutoff
            except ValueError:
                continue
        return True

    _write(
        "feed.xml",
        "JCStream changes",
        "New, updated, and released records on the Hamilton County, OH Justice Center public roster.",
        events,
    )
    _write(
        "booked.xml",
        "JCStream - new bookings",
        "People recently booked into the Hamilton County, OH Justice Center.",
        [e for e in events if _recent_booked(e)],
    )
    _write(
        "released.xml",
        "JCStream - releases",
        "People released from the Hamilton County, OH Justice Center public roster.",
        [e for e in events if e.event == "released"],
    )


def _render_data_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Documentation + download index for the raw JSON the site is built from."""
    data_out = out_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    supplemental = [f.filename for f in FEEDS]
    for name in (
        "current.json",
        "changelog.json",
        "anon_changelog.json",
        "history.json",
        "cfs_recent.json",
        "shootings_recent.json",
        "waf_block_log.json",
        "cfs_pdi_recent.json",
        "courtclerk_cases.json",
        "orc_offenses.json",
        *supplemental,
    ):
        src = Path("data") / name
        if src.exists():
            shutil.copy2(src, data_out / name)
    page = env.get_template("data.html").render(
        snapshot=snapshot,
        courtclerk_cases_available=(Path("data") / "courtclerk_cases.json").exists(),
    )
    (data_out / "index.html").write_text(page, encoding="utf-8")


def _render_transparency_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Public accountability scorecard computed from the WAF-block evidence
    ledger, plus a JSON mirror of the metrics under /data/ so exhibit numbers
    for public-records filings regenerate on every build."""
    metrics = compute_transparency_metrics(load_block_log(), snapshot.generated_utc)
    page = env.get_template("transparency.html").render(metrics=metrics)
    target = out_dir / "transparency" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    data_out = out_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    (data_out / "transparency_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def _tally_attribute(inmates: list[Inmate], attr: str, expand) -> list[tuple[str, int]]:
    """Count inmates by a demographic attribute, returning (label, count) descending."""
    out: dict[str, int] = {}
    for inm in inmates:
        label = expand(getattr(inm, attr, ""))
        out[label] = out.get(label, 0) + 1
    return sorted(out.items(), key=lambda kv: -kv[1])


def _tier_summary(inmates: list[Inmate]) -> dict[str, int]:
    """Count inmates by primary tier kind (felony/misdemeanor/other)."""
    tiers: dict[str, int] = {"felony": 0, "misdemeanor": 0, "other": 0}
    for inm in inmates:
        t = _primary_tier(inm)
        tiers[t["kind"] if t else "other"] += 1
    return tiers


def _inmate_bond_total(inmate: Inmate) -> float | None:
    """Sum all parseable bond amounts for an inmate; None if no amounts found."""
    total = 0.0
    any_amt = False
    for c in inmate.charges:
        amt = _parse_bond_amount(c.bond_amount)
        if amt is not None:
            any_amt = True
            total += amt
    return total if any_amt else None


def _bond_stats(inmates: list[Inmate]) -> dict:
    """Aggregate bond statistics across all inmates."""
    bond_vals: list[float] = []
    zero_bond = 0
    for inm in inmates:
        total = _inmate_bond_total(inm)
        if total is not None:
            bond_vals.append(total)
            if total == 0:
                zero_bond += 1
    bond_vals.sort()
    return {
        "bond_total": sum(bond_vals),
        "bond_median": bond_vals[len(bond_vals) // 2] if bond_vals else 0,
        "bond_zero": zero_bond,
        "bond_known": len(bond_vals),
    }


def _charge_stats(inmates: list[Inmate]) -> dict:
    """Aggregate charge-count statistics across all inmates."""
    n = len(inmates)
    ch_counts = [len(inm.charges) for inm in inmates]
    avg_ch = (sum(ch_counts) / n) if n else 0
    return {
        "avg_charges": round(avg_ch, 1),
        "max_charges": max(ch_counts) if ch_counts else 0,
        "one_charge": sum(1 for c in ch_counts if c == 1),
    }


def _custody_stats(inmates: list[Inmate]) -> dict:
    """Aggregate days-in-custody statistics across all inmates."""
    days = [d for inm in inmates if (d := _days_in_custody(inm)) is not None]
    avg_days = (sum(days) / len(days)) if days else 0
    return {"avg_days": round(avg_days), "max_days": max(days) if days else 0}


def _compute_stats(snapshot: Snapshot, by_month) -> dict:
    """Aggregates for the /stats/ page."""
    inmates = snapshot.inmates
    n = len(inmates)
    with_photo = sum(1 for inm in inmates if inm.photo_filename)
    return {
        "n": n,
        "months": [(m, len(g)) for m, g in by_month],
        "offenses": _crimes_of_month(inmates),
        "tiers": _tier_summary(inmates),
        "sex": _tally_attribute(inmates, "sex", _expand_sex),
        "race": _tally_attribute(inmates, "race", _expand_race),
        **_bond_stats(inmates),
        **_charge_stats(inmates),
        "with_photo": with_photo,
        "no_photo": n - with_photo,
        **_custody_stats(inmates),
        "tier_breakdown": _tier_breakdown(snapshot),
        "top_offenses": _top_offenses_with_orc(snapshot, top_n=12),
        "court_calendar": _upcoming_courts(snapshot, days_ahead=14),
        "slippage": _court_slippage(inmates),
    }


def _render_stats_page(env: Environment, snapshot: Snapshot, by_month, trend: dict, out_dir: Path) -> None:
    stats = _compute_stats(snapshot, by_month)
    page = env.get_template("stats.html").render(snapshot=snapshot, s=stats, trend=trend)
    target = out_dir / "stats" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_bond_disparity_page(env: Environment, snapshot: Snapshot, offenses: dict, out_dir: Path) -> None:
    """Flagship analytics: per-statute bond dispersion with the n >= 5
    suppression floor. Aggregate only; no individual bonds are shown."""
    idx = RosterIndexes(snapshot.inmates, offenses)
    rows = _bond_disparity(idx, offenses)
    page = env.get_template("bond-disparity.html").render(
        snapshot=snapshot,
        rows=rows,
        min_n=BOND_DISPARITY_MIN_N,
    )
    target = out_dir / "bond-disparity" / "index.html"
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


log = logging.getLogger(__name__)

_JUDGES_PHOTO_DIR = Path(__file__).parent / "static" / "judges"


def _mirror_judge_photo(image_url: str, base_url: str) -> str:
    """Mirror a remote judge headshot to a same-origin /static/judges/ asset.

    Returns a base_url-prefixed local path. Returns "" on a missing URL or any
    fetch/decode failure so the template omits the <img> rather than hot-linking
    a third-party government host (an FCRA third-party-embed and CSP img-src
    violation). Idempotent: a mirrored file is reused, never refetched.
    """
    if not image_url or not image_url.startswith(("http://", "https://")):
        return ""
    name = hashlib.sha1(image_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16] + ".jpg"
    dest = _JUDGES_PHOTO_DIR / name
    if not dest.exists():
        try:
            import httpx

            resp = httpx.get(
                image_url,
                timeout=5.0,
                follow_redirects=True,
                headers={"User-Agent": DEFAULT_UA},
            )
            resp.raise_for_status()
        except Exception as e:
            log.warning("judge photo fetch failed for %s: %s", image_url, e)
            return ""
        if not downscale_and_save(resp.content, dest):
            return ""
    return f"{base_url}/static/judges/{name}"


def _parse_judges(base_url: str = "") -> tuple[list[dict], list[dict]]:
    """Parse Common Pleas and Municipal judge profile JSON files in HAMCO/.
    Returns (common_pleas_list, municipal_list) sorted by judge's last name or clean name.
    """
    import re

    hamco_dir = Path("HAMCO")
    if not hamco_dir.exists():
        return [], []

    common_pleas: list[dict] = []
    municipal: list[dict] = []

    for path in hamco_dir.glob("*.json"):
        filename = path.name.lower()
        if "court-judge-" not in filename or "schedules" in filename:
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Skip error pages (like 404)
        metadata = data.get("metadata", {}) or {}
        status_code = metadata.get("statusCode", 200)
        if status_code >= 400 or data.get("error"):
            continue

        markdown = data.get("markdown", "")
        if not markdown:
            continue

        header_line = ""
        for line in markdown.splitlines():
            if line.startswith("# "):
                header_line = line.lstrip("# ").strip()
                break

        if not header_line:
            continue

        if header_line.isupper():
            header_line = header_line.title()

        header_line_clean = re.sub(r"common please", "Common Pleas", header_line, flags=re.IGNORECASE)

        prefix_pat = re.compile(r"^(common pleas (court )?judge|municipal (court )?judge)\s*", re.IGNORECASE)

        clean_name = prefix_pat.sub("", header_line_clean).strip()

        if clean_name in ("Sorry!", "Page Not Found", "Court & Judge Schedules"):
            continue

        if "municipal" in header_line_clean.lower() or "municipal" in filename:
            court_type = "municipal"
            title = "Municipal Court Judge"
        else:
            court_type = "common_pleas"
            title = "Common Pleas Court Judge"

        image_url = ""
        img_match = re.search(r"!\[.*?\]\((.*?)\)", markdown)
        if img_match:
            image_url = _mirror_judge_photo(img_match.group(1), base_url)

        room = ""
        bailiff = ""
        phone = ""
        for line in markdown.splitlines():
            line_str = line.strip()
            if line_str.lower().startswith("room"):
                room = line_str
                if room.isupper():
                    room = room.capitalize()
            elif "bailiff" in line_str.lower():
                bailiff = line_str
            elif "phone number" in line_str.lower() or "phone:" in line_str.lower():
                if not phone:
                    phone = line_str

        bio_lines = []
        proc_lines = []
        current_section = None
        for line in markdown.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("##"):
                lower_stripped = line_stripped.lower()
                if "about" in lower_stripped:
                    current_section = "bio"
                elif "procedures" in lower_stripped:
                    current_section = "procedures"
                else:
                    current_section = "other"
            elif current_section == "bio":
                bio_lines.append(line)
            elif current_section == "procedures":
                proc_lines.append(line)

        bio = "\n".join(bio_lines).strip()
        procedures = "\n".join(proc_lines).strip()

        name_parts = clean_name.split()
        last_name = name_parts[-1] if name_parts else clean_name

        slug = clean_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')

        judge_dict = {
            "name": clean_name,
            "title": title,
            "room": room,
            "bailiff": bailiff,
            "phone": phone,
            "image_url": image_url,
            "bio": bio,
            "procedures": procedures,
            "last_name": last_name,
            "slug": slug,
            "filename": path.name,
        }

        if court_type == "municipal":
            municipal.append(judge_dict)
        else:
            common_pleas.append(judge_dict)

    common_pleas.sort(key=lambda j: (j["last_name"].lower(), j["name"].lower()))
    municipal.sort(key=lambda j: (j["last_name"].lower(), j["name"].lower()))

    return common_pleas, municipal


def _render_courts_page(env: Environment, out_dir: Path) -> None:
    """Static "Hamilton County court system" reference page. Mirrors directory
    and jurisdictional info from hamiltoncountycourts.org (Municipal +
    Common Pleas), probatect.org, and the Clerk of Courts. Distinct from
    /court/ which is the operational calendar of upcoming hearings."""
    common_pleas, municipal = _parse_judges(str(env.globals.get("base_url", "")))
    page = env.get_template("courts.html").render(
        common_pleas=common_pleas,
        municipal=municipal,
    )
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
        sections.append(
            {
                **r,
                "tier_max": _tier_max(r["degree"]),
                "explainer": explainers.get(r["code"]),
                "held": _statute_held_inmates(snapshot, r["code"], limit=18),
                "caselaw": caselaw.get(r["code"], []),
            }
        )
    page = env.get_template("statute.html").render(
        snapshot=snapshot,
        sections=sections,
        total_roster=snapshot.inmate_count,
    )
    target = out_dir / "statute" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
