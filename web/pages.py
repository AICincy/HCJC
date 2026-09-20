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
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment

from scraper import orc as orc_mod
from scraper.client import DEFAULT_UA
from scraper.models import ChangeEvent, Inmate, Snapshot
from scraper.open_data_feeds import FEEDS
from scraper.photos import downscale_and_save
from scraper.store import BlockLogCorruptError, load_block_log
from web import feeds as feeds_mod
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
    surface it than silently drop it). Sorted newest-first; dateless rows
    sort last.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
    parsed: list[tuple[datetime | None, dict]] = []
    for r in rows:
        dt = _extract_row_dt(r, field_candidates)
        if dt is None or dt >= cutoff:
            parsed.append((dt, r))
    parsed.sort(key=lambda t: (t[0] is not None, t[0] or datetime.min), reverse=True)
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
        safety_teaser=feeds_mod.latest_incidents(feeds_mod.DATA_DIR, n=3),
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def _safe_crowdsourced_url(value: object) -> str:
    """Blank crowdsourced URLs whose scheme is not http/https.

    Defense-in-depth behind the ingest validation in
    ``scraper/ingest_issue.py``: records already stored in
    ``data/courtclerk_cases.json`` predate that hardening, and Jinja
    autoescape does not stop ``javascript:`` URLs in href attributes.
    """
    return sanitize_outbound_url(value)


def sanitize_outbound_url(value: object) -> str:
    """Allowlist corpus-derived URLs before they reach an href.

    Only http and https are allowed. Leading control characters are stripped.
    Fail closed by returning "" for anything invalid. Autoescape does not
    neutralize ``javascript:`` URLs, so this gate is required before new
    corpus-derived links ship.
    """
    s = value if isinstance(value, str) else ""
    # Strip leading control characters (including unicode bidi overrides)
    s = s.lstrip("".join(chr(c) for c in range(0x20)) + "\u200e\u200f\u202a\u202b\u202c\u202d\u202e")
    s = s.strip()
    if not s:
        return ""
    try:
        scheme = urllib.parse.urlsplit(s).scheme.lower()
    except ValueError:
        return ""
    return s if scheme in ("http", "https") else ""


def sanitize_phone_href(value: object) -> str:
    """Validate phone charset before building tel: hrefs.

    Allowed chars: + 0-9 ( ) . - whitespace. Invalid values return ""
    and the caller must render plain text instead of a link.
    """
    import re
    s = value if isinstance(value, str) else ""
    s = s.strip()
    if not s:
        return ""
    if not re.fullmatch(r"[+0-9().\-\s]+", s):
        return ""
    # Normalize to tel:+1... form for US numbers is left to the caller;
    # here we just return the validated raw value for href construction.
    return s


def sanitize_email_href(value: object) -> str:
    """Validate email charset before building mailto: hrefs.

    Very small allowlist: local@domain with common email chars.
    Invalid values return "" and the caller renders plain text.
    """
    import re
    s = value if isinstance(value, str) else ""
    s = s.strip()
    if not s:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", s):
        return ""
    return s


def _load_crowdsourced_cases(
    inmates: list[Inmate],
) -> dict[str, list[dict]]:
    """Read data/courtclerk_cases.json (populated via the case-data issue
    workflow) and index entries by matched inmate_number.

    Matching is by normalized defendant name plus date of birth
    (scraper.case_match); entries that match no current inmate are dropped,
    which is correct for a current-mirror: a submitted case for a released
    person must not linger on a page that no longer exists.
    """
    from scraper.case_match import match_cases_to_inmates

    path = feeds_mod.DATA_DIR / "courtclerk_cases.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    entries = raw if isinstance(raw, list) else []
    matched = match_cases_to_inmates([e for e in entries if isinstance(e, dict)], inmates)
    # Adapt stored records to the fields web/templates/inmate.html renders.
    adapted: dict[str, list[dict]] = {}
    for inmate_number, records in matched.items():
        adapted[inmate_number] = [
            {
                "case_number": r.get("case_number", ""),
                "case_number_key": r.get("case_number_key", ""),
                "judge": r.get("judge", ""),
                "disposition": r.get("disposition", ""),
                "next_hearing": r.get("next_hearing", ""),
                "charges_raw": r.get("charges_raw", ""),
                "notes": r.get("notes", ""),
                "source_url": _safe_crowdsourced_url(r.get("source_url", "")),
                "issue_url": _safe_crowdsourced_url(r.get("issue_url", "")),
                "submitter": r.get("submitter", ""),
                "submitted": (r.get("ingested_utc") or "")[:10],
                "dob_verified": r.get("dob_verified", False),
                "case_on_booking": r.get("case_on_booking", False),
            }
            for r in records
        ]
    return adapted


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
    crowdsourced = _load_crowdsourced_cases(snapshot.inmates)

    def _render_one(inm: Inmate) -> None:
        # Templates come from the shared env with autoescape enabled (see
        # web/build.py _build_env); not Flask, so render_template() N/A.
        # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
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
        # feed.xml is rendered by the shared autoescape-enabled env; XML content
        # is escaped, and this is a static builder, not a Flask request handler.
        # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
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
            return False
        bd_str = e.note[len("booked ") :].strip()
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(bd_str, fmt).date() >= cutoff
            except ValueError:
                continue
        return False

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


# V9-L03: per-feed vintage for the data page. Each supplemental feed JSON carries
# a generated_utc stamp; surfacing it keeps the "refresh attempts" rows from
# reading as a freshness SLA by showing the actual data age instead.
# The open-data pull specs (FEEDS) are the single source for the Socrata
# feed filenames; the three non-FEEDS files are listed explicitly.
_FEED_VINTAGE_FILES = (
    "cfs_recent.json",
    "cfs_pdi_recent.json",
    "shootings_recent.json",
    *[f.filename for f in FEEDS],
)


def _feed_vintage() -> dict[str, str]:
    """Map feed filename -> generated_utc stamp ("" when missing/unreadable).

    Delegates to feeds_mod.vintage_of on the anchored DATA_DIR: a build
    invoked from any working directory still finds the feeds instead of
    silently stamping every file "".
    """
    return {
        name: feeds_mod.vintage_of(feeds_mod.DATA_DIR, name)
        for name in _FEED_VINTAGE_FILES
    }


def _render_data_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Documentation + download index for the raw JSON the site is built from."""
    data_out = out_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    # Anchored to the repo source tree: a build invoked from any working
    # directory publishes the real downloads instead of an empty /data/.
    #
    # C-4: the waf_block_log.json duplication (data/ = sweep's working copy,
    # docs/data/ = published mirror) is deliberate. The sweep appends to
    # data/; the build publishes a byte-identical mirror under docs/data/ so
    # the evidence is browsable at the live URL. CI asserts the two stay
    # byte-identical, and the append-only rule covers both copies -- never
    # edit, rewrite, or truncate either by hand.
    data_dir = feeds_mod.DATA_DIR
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
        src = data_dir / name
        if src.exists():
            if name == "waf_block_log.json":
                # C-1: never publish an unreadable evidence file as the public
                # mirror; the last-good copy stays in git history.
                try:
                    load_block_log(src)
                except BlockLogCorruptError as e:
                    log.error("data page: skipping corrupt WAF-block log copy (%s)", e)
                    continue
            shutil.copy2(src, data_out / name)
    # Crowdsourced ingest is optional; still publish an empty file so the
    # documented /data/courtclerk_cases.json URL is not a GitHub Pages 404.
    cases_out = data_out / "courtclerk_cases.json"
    if not cases_out.exists():
        cases_out.write_text('{"cases": []}\n', encoding="utf-8")
    page = env.get_template("data.html").render(
        snapshot=snapshot,
        courtclerk_cases_available=(data_dir / "courtclerk_cases.json").exists(),
        feed_vintage=_feed_vintage(),
    )
    (data_out / "index.html").write_text(page, encoding="utf-8")


def _render_transparency_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Public accountability scorecard computed from the WAF-block evidence
    ledger, plus a JSON mirror of the metrics under /data/ so exhibit numbers
    for public-records filings regenerate on every build."""
    try:
        block_log = load_block_log()
    except BlockLogCorruptError as e:
        # C-1: a corrupt evidence log must not take the site build down, but
        # it must not be silently rendered as "no blocks" either: loud error
        # in CI logs, metrics rendered from an empty log this cycle.
        log.error(
            "transparency page: WAF-block evidence log unreadable (%s); rendering metrics as unavailable", e
        )
        block_log = []
    metrics = compute_transparency_metrics(
        block_log, snapshot.generated_utc, last_healthy_sweep_utc=snapshot.last_healthy_sweep_utc
    )
    page = env.get_template("transparency.html").render(metrics=metrics, snapshot=snapshot)
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
    from web.shape.common import _cached_offenses

    offenses = _cached_offenses()
    tiers: dict[str, int] = {"felony": 0, "misdemeanor": 0, "other": 0}
    for inm in inmates:
        t = _primary_tier(inm, offenses)
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
        "bond_total": int(sum(bond_vals)),
        "bond_median": int(bond_vals[len(bond_vals) // 2]) if bond_vals else 0,
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


def _render_safety_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Plain-English Cincinnati Open Data summaries (Phase 1: latest incidents
    + reported crime; Phase 2: traffic and pedestrian stops). Aggregates are
    computed at build time by web.feeds from whatever the sweep pulled."""
    data_dir = feeds_mod.DATA_DIR
    ctx = feeds_mod.safety_context(data_dir)
    try:
        incidents, stars, stops = ctx["incidents"], ctx["stars"], ctx["stops"]
    except KeyError as e:
        raise RuntimeError(
            f"web.feeds.safety_context() contract broken: missing key {e}"
        ) from e
    incident_files = (
        "cfs_recent.json",
        "cfs_pdi_recent.json",
        "shootings_recent.json",
        "crime_stars_recent.json",
    )
    stamps = [s for s in (feeds_mod.vintage_of(data_dir, f) for f in incident_files) if s]
    page = env.get_template("safety.html").render(
        snapshot=snapshot,
        incidents=incidents,
        stars=stars,
        stops=stops,
        newest_vintage=max(stamps) if stamps else "",
    )
    target = out_dir / "safety" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_bond_disparity_page(env: Environment, snapshot: Snapshot, offenses: dict, out_dir: Path) -> None:
    """Flagship analytics: per-statute bond dispersion with the n >= 5
    suppression floor. Aggregate only; no individual bonds are shown."""
    idx = RosterIndexes(snapshot.inmates)
    rows = _bond_disparity(idx, offenses)
    page = env.get_template("bond-disparity.html").render(
        snapshot=snapshot,
        rows=rows,
        min_n=BOND_DISPARITY_MIN_N,
    )
    target = out_dir / "bond-disparity" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_bond_schedule_page(env: Environment, out_dir: Path) -> None:
    """Render the court's Standard Bond Schedule (rev. 3/5/2026).

    Data source: data/court_bond_schedule.json (canonical, via ingest).
    Deliberate restraint: no computed "you post $X" amounts. The 10% rule
    is shown as published; whether it applies unconditionally is not
    established.
    """
    from markupsafe import Markup

    data_path = Path(__file__).resolve().parent.parent / "data" / "court_bond_schedule.json"
    try:
        raw = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"court_bond_schedule.json missing or corrupt: {e}") from e

    # Hard-fail on schema violation (fail-closed on integrity)
    if "_provenance" not in raw or "rows" not in raw:
        raise RuntimeError("court_bond_schedule.json schema violation: missing _provenance or rows")
    if len(raw["rows"]) != 19:
        raise RuntimeError(f"court_bond_schedule.json count FAIL: expected 19 rows, got {len(raw['rows'])}")

    def _tier_html(val: str) -> Markup:
        # NO BOND gets the literal #C22525 chip (5.9:1 both themes), never var(--accent)
        if val == "NO BOND":
            return Markup('<span class="bond-chip-no">NO BOND</span>')
        # Escape everything else; amounts are plain text in --fg
        import html
        # nosemgrep: explicit-unescape-with-markup
        return Markup(html.escape(val))

    def _orc_links(orc_field: str) -> list[dict]:
        # Split on comma, strip * suffixes, build anchors like orc-4511-19
        links = []
        for part in orc_field.split(","):
            code = part.strip().rstrip("*").strip()
            if not code:
                continue
            # Normalize for anchor: 4511-19 stays, 4510-037 -> 4510-037
            anchor = code.replace(".", "-")
            links.append({"code": code, "anchor": anchor})
        return links

    bond_rows = []
    for r in raw["rows"]:
        offense = r.get("offense", "")
        # SEXAUL typo: stored verbatim, corrected at render with [sic] provenance
        offense_display = offense
        if "SEXAUL" in offense:
            offense_display = offense.replace("SEXAUL", "SEXUAL")
        orc = r.get("orc", "")
        bond_rows.append({
            "section": r.get("section", ""),
            "offense": offense,
            "offense_display": offense_display,
            "orc": orc,
            "orc_links": _orc_links(orc),
            "in_county_html": _tier_html(r.get("in_county", "")),
            "out_of_county_html": _tier_html(r.get("out_of_county", "")),
            "out_of_state_no_address_html": _tier_html(r.get("out_of_state_no_address", "")),
        })

    no_standard = []
    for item in raw.get("no_standard_bond", []):
        orc = item.get("orc", "")
        # Take first code for anchor; the list shows single ORC per offense
        anchor = orc.split(",")[0].strip().replace(".", "-") if orc else ""
        no_standard.append({
            "offense": item.get("offense", ""),
            "orc": orc,
            "orc_anchor": anchor,
        })

    # Bond source PDF URL: allowlisted
    bond_source_url = sanitize_outbound_url(
        "https://hamiltoncountycourts.org/wp-content/uploads/2026/03/bond_sched_latest.pdf"
    )

    page = env.get_template("bond-schedule.html").render(
        bond_rows=bond_rows,
        no_standard_bond=no_standard,
        felony_notes=raw.get("felony_notes", []),
        general_notes=raw.get("general_notes", []),
        bond_source_url=bond_source_url,
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "bond-schedule" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_court_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Aggregate every inmate's earliest upcoming court date into today /
    tomorrow / this-week / next-30-days buckets. Court-watchers and journalists
    get a docket view that the per-record pages cannot offer.
    """
    cal = _court_calendar(snapshot.inmates)
    now_eastern = datetime.now(ZoneInfo("America/New_York"))
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
    page = env.get_template("visit.html").render(generated_utc=env.globals["generated_utc"])
    target = out_dir / "visit" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_help_page(env: Environment, out_dir: Path) -> None:
    """Static "Get help" resources page. Mirrors current contact info for the
    free Hamilton County legal and crisis resources most relevant to people
    who land on JCStream looking for help. No data dependencies."""
    page = env.get_template("help.html").render(generated_utc=env.globals["generated_utc"])
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
    import httpx

    try:
        httpx.URL(image_url)
    except Exception as e:
        # Malformed URL in the source HAMCO profile data (e.g. httpx
        # "Invalid port: ':1]'"). No network attempt is made; the template
        # omits the <img> instead of hot-linking a broken URL.
        log.warning("judge photo URL malformed, skipping: %s (%s)", image_url, e)
        return ""
    # SHA256 for filename (not security); truncated to 16 hex chars for brevity
    name = hashlib.sha256(image_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16] + ".jpg"
    dest = _JUDGES_PHOTO_DIR / name
    if not dest.exists():
        try:
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


def _judges_from_ingested_json() -> tuple[list[dict], list[dict]] | None:
    """Read data/court_judges.json (Firecrawl corpus, written by
    scraper/ingest_court_content.py).

    Returns None when the file is missing or fails validation so the caller
    falls back to the legacy HAMCO/ profiles loudly. The canonical JSON
    carries fax/email/law-clerk/source_url fields HAMCO never had; slugs and
    last names are derived with the same logic as the HAMCO parse so
    judge-deeplink.js anchors and classify.py #judge-<slug> targets are
    unchanged. Quarantined bios (bio_status != "clean") are not published.
    """
    import re

    path = feeds_mod.DATA_DIR / "court_judges.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.warning("judge data: %s missing; falling back to HAMCO/ profiles", path)
        return None
    except (json.JSONDecodeError, OSError) as e:
        log.warning("judge data: %s unreadable (%s); falling back to HAMCO/ profiles", path, e)
        return None

    judges = data.get("judges") if isinstance(data, dict) else None
    if not isinstance(judges, list) or len(judges) != 30:
        n = len(judges) if isinstance(judges, list) else "not-a-list"
        log.warning(
            "judge data: %s failed count band (%s records); falling back to HAMCO/ profiles",
            path,
            n,
        )
        return None

    common_pleas: list[dict] = []
    municipal: list[dict] = []

    for rec in judges:
        if not isinstance(rec, dict):
            log.warning("judge data: %s has a non-object record; falling back to HAMCO/ profiles", path)
            return None
        name = str(rec.get("name") or "").strip()
        court = str(rec.get("court") or "").strip()
        if not name or court not in ("Common Pleas", "Municipal"):
            log.warning(
                "judge data: %s record missing name/court; falling back to HAMCO/ profiles", path
            )
            return None

        courtroom = str(rec.get("courtroom") or "").strip()
        bio = rec.get("bio") or ""
        name_parts = name.split()
        last_name = name_parts[-1] if name_parts else name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

        judge_dict = {
            "name": name,
            "title": "Municipal Court Judge" if court == "Municipal" else "Common Pleas Court Judge",
            "room": f"Room {courtroom}" if courtroom else "",
            "bailiff": str(rec.get("bailiff") or "").strip(),
            "phone": str(rec.get("phone") or "").strip(),
            "fax": str(rec.get("fax") or "").strip(),
            "fax_href": sanitize_phone_href(rec.get("fax") or ""),
            "email": str(rec.get("email") or "").strip(),
            "email_href": sanitize_email_href(rec.get("email") or ""),
            "law_clerk": str(rec.get("law_clerk") or "").strip(),
            "source_url": sanitize_outbound_url(rec.get("source_url") or ""),
            "image_url": "",  # filled from the HAMCO photo index by _parse_judges
            "bio": bio if rec.get("bio_status") == "clean" else "",
            "procedures": "",
            "last_name": last_name,
            "slug": slug,
        }

        if court == "Municipal":
            municipal.append(judge_dict)
        else:
            common_pleas.append(judge_dict)

    common_pleas.sort(key=lambda j: (j["last_name"].lower(), j["name"].lower()))
    municipal.sort(key=lambda j: (j["last_name"].lower(), j["name"].lower()))

    return common_pleas, municipal


def _parse_judges(base_url: str = "") -> tuple[list[dict], list[dict]]:
    """Parse judge profiles, preferring data/court_judges.json with HAMCO/ fallback.

    The canonical JSON path keeps the already-mirrored headshots: HAMCO
    remains the photo source of record (the corpus ships no images), so the
    legacy parse runs as a photo index even on the JSON path. Missing or
    corrupt JSON logs loudly and falls back to the legacy HAMCO/ profiles.
    """
    from_json = _judges_from_ingested_json()
    hamco = _parse_judges_hamco(base_url)
    if from_json is None:
        return hamco
    photos = {j["slug"]: j["image_url"] for j in hamco[0] + hamco[1]}
    common_pleas, municipal = from_json
    for j in common_pleas + municipal:
        j["image_url"] = photos.get(j["slug"], "")
    return common_pleas, municipal


def _parse_judges_hamco(base_url: str = "") -> tuple[list[dict], list[dict]]:
    """Parse Common Pleas and Municipal judge profile JSON files in HAMCO/.
    Returns (common_pleas_list, municipal_list) sorted by judge's last name or clean name.
    """
    import re

    # Anchored to the repo root: a build invoked from any working directory
    # still finds the judge profile JSON instead of silently rendering none.
    hamco_dir = Path(__file__).resolve().parent.parent / "HAMCO"
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
        except Exception as e:
            log.warning("skipping unreadable HAMCO judge profile %s: %s", path.name, e)
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
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")

        judge_dict = {
            "name": clean_name,
            "title": title,
            "room": room,
            "bailiff": bailiff,
            "phone": phone,
            "fax": "",
            "fax_href": "",
            "email": "",
            "email_href": "",
            "law_clerk": "",
            "source_url": "",
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
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "courts" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _linked_statute_codes(snapshot: Snapshot) -> list[str]:
    """Every normalized ORC code actually linked from a built page.

    Inmate pages link ``/statute/#orc-<code>`` for each charge's normalized
    code, and the stats toplist plus the bond-disparity rows link the same
    normalized codes, so the union is every non-empty normalized charge code
    on the roster. Ordered by roster frequency (desc), then code, matching
    the ranking the statute page already uses.
    """
    counts: dict[str, int] = {}
    for inm in snapshot.inmates:
        for c in inm.charges:
            code = orc_mod.normalize_code((c.orc_code or "").strip())
            if code and code.upper() != "NONE":
                counts[code] = counts.get(code, 0) + 1
    return [code for code, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _render_statute_page(env: Environment, snapshot: Snapshot, offenses: dict, out_dir: Path) -> None:
    """Statute lookup -- one page with each ORC section currently on the roster."""
    explainers = _load_explainers()
    caselaw = _load_caselaw_cache()
    # A section for EVERY code linked from a built page, not just the top 60:
    # anything fewer leaves dead #orc-<code> anchors on inmate, stats, and
    # bond-disparity pages (V8-F2). The row set of _top_offenses_with_orc is
    # exactly the linked-code set, so top_n >= len(linked) returns one row
    # per code, still ranked by frequency with the old top 60 first.
    linked = _linked_statute_codes(snapshot)
    rows = _top_offenses_with_orc(snapshot, top_n=max(60, len(linked)), offenses=offenses)
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


def _render_404_page(env: Environment, out_dir: Path) -> None:
    """Branded GitHub Pages 404. Pages serves /404.html for any missing path."""
    page = env.get_template("404.html").render()
    (out_dir / "404.html").write_text(page, encoding="utf-8")
