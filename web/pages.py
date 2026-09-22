"""Page-rendering functions for the JCStream static site.

Each function renders one or more HTML pages from Jinja2 templates and writes
them to the output directory. Extracted from web/build.py for modularity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
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


#: Homepage roster window (spec 1.3.6). False (default): the homepage shows the
#: current booking month plus two prior months; older months move to the
#: /archive/ page, which the homepage links. True: the homepage shows the full
#: roster, restoring the pre-redesign roster in one build. No booking data is
#: unpublished either way. V4 is the release gate for the windowed layout
#: (time-to-interactive on a mid-range Android device, before vs after): the
#: flag returns to True if the archive move shows no material improvement.
#: V4 was not performed in this environment and remains a
#: human/physical-device gate before release.
HOMEPAGE_FULL_ROSTER = False

#: Booking-month groups shown on the homepage when HOMEPAGE_FULL_ROSTER is
#: False: the current month plus two prior months (spec 1.3.6).
HOMEPAGE_MONTH_WINDOW = 3


def _render_index(env: Environment, ctx: IndexContext, out_dir: Path) -> None:
    # Spec 1.3.6: windowed homepage roster behind HOMEPAGE_FULL_ROSTER.
    # The /stats/ page always uses the full month list (passed separately).
    if HOMEPAGE_FULL_ROSTER:
        hp_months = ctx.by_month
        hp_nav = ctx.nav_months
    else:
        hp_months = ctx.by_month[:HOMEPAGE_MONTH_WINDOW]
        hp_nav = ctx.nav_months[:HOMEPAGE_MONTH_WINDOW]
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
        by_month=hp_months,
        nav_months=hp_nav,
        expanded_months={m for m, _ in hp_months[:1]},
        recent_booked=ctx.recent_booked,
        recent_released=ctx.recent_released,
        trend=ctx.trend,
        cfs_rows=cfs_30d,
        shooting_rows=shoot_30d,
        cfs_by_district=_group_by_district(cfs_30d),
        shoot_by_district=_group_by_district(shoot_30d),
        map_points=ctx.map_points,
        # The homepage is not in the drawer groups (spec 1.3): no highlight.
        active_nav="",
        # Archive link inputs (spec 1.3.6): shown only when the window is on.
        homepage_full_roster=HOMEPAGE_FULL_ROSTER,
        archive_months=max(0, len(ctx.by_month) - len(hp_months)),
        archive_bookings=sum(len(g) for _, g in ctx.by_month[len(hp_months):]),
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def _render_archive_page(
    env: Environment,
    snapshot: Snapshot,
    by_month,
    nav_months: list[dict],
    out_dir: Path,
) -> None:
    """Earlier-bookings archive (/archive/): the full roster with the same
    search and filters as the homepage. Keeps every booking published and
    searchable while the homepage shows the 3-month window
    (HOMEPAGE_FULL_ROSTER=False). Rendered always, so the one-build reversal
    of the flag never 404s a linked page."""
    page = env.get_template("archive.html").render(
        snapshot=snapshot,
        by_month=by_month,
        nav_months=nav_months,
        expanded_months={m for m, _ in by_month[:1]},
        generated_utc=env.globals["generated_utc"],
        active_nav="",
    )
    target = out_dir / "archive" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


def _render_public_records_page(env: Environment, snapshot: Snapshot, out_dir: Path) -> None:
    """Public Records Dashboard (/data/public-records/): collects the
    public-records material already published by the build (open data feeds,
    the access-interruption evidence log, the transparency scorecard) with a
    one-line description of each. The repo carries no public-records
    correspondence log, so none is presented; the page links the agency's own
    request channel instead. Factual and minimal; no records are invented."""
    page = env.get_template("public_records.html").render(
        snapshot=snapshot,
        generated_utc=env.globals["generated_utc"],
        active_nav="",
    )
    target = out_dir / "data" / "public-records" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


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
    manifest_path = Path(__file__).resolve().parent.parent / "config" / "public-data-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        name = entry["path"]
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
    # by_month rides along so the crimes-of-the-month section (moved here from
    # the homepage, spec 1.3.7) can compute per-month categories. "stats" is
    # the drawer's Roster-tools key for this page (spec 3.5).
    page = env.get_template("stats.html").render(
        snapshot=snapshot, s=stats, trend=trend, by_month=by_month, active_nav="stats"
    )
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


def _render_judges_page(env: Environment, out_dir: Path) -> None:
    """Judge profile grid (/judges/).

    Feed: the in-repo ingested corpus data/court_judges.json (30 profiles, 16
    Common Pleas / 14 Municipal), read through _judges_from_ingested_json()
    (feeds_mod.DATA_DIR / "court_judges.json"), plus the self-hosted photo
    provenance manifest (web/static/judges/provenance.json). Photos are served
    from the manifest's local_path; the remote photo_url is never referenced
    (no hotlinking, per the T5 self-hosting decision). Fails closed on
    missing feed, count drift, photo-manifest mismatch, or slug collision:
    unlike _parse_judges(), an invalid feed raises instead of falling back to
    HAMCO/ profiles.
    """

    parsed = _judges_from_ingested_json()
    if parsed is None:
        raise RuntimeError(
            "judges page: data/court_judges.json missing, unreadable, or not "
            "30 validated profiles (fail-closed; no HAMCO fallback on /judges/)"
        )
    common_pleas_raw, municipal_raw = parsed
    if len(common_pleas_raw) != 16 or len(municipal_raw) != 14:
        raise RuntimeError(
            "judges page: data/court_judges.json count FAIL: expected 16 Common "
            f"Pleas + 14 Municipal, got {len(common_pleas_raw)} + {len(municipal_raw)}"
        )

    prov_path = Path(__file__).resolve().parent / "static" / "judges" / "provenance.json"
    try:
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"judge photo provenance.json missing or corrupt: {e}") from e
    photos = {
        j.get("full_name"): j
        for j in prov.get("judges", [])
        if isinstance(j, dict)
    }
    if len(photos) != 30:
        raise RuntimeError(
            f"judge photo provenance FAIL: expected 30 manifest entries, got {len(photos)}"
        )

    def _tel_href(num: str) -> str:
        digits = "".join(ch for ch in sanitize_phone_href(num) if ch.isdigit())
        return f"tel:+1{digits}" if digits else ""

    base_url = str(env.globals.get("base_url", ""))
    seen_slugs: set[str] = set()
    judges: list[dict] = []
    for court, rec in [("Common Pleas", r) for r in common_pleas_raw] + [
        ("Municipal", r) for r in municipal_raw
    ]:
        name = rec["name"]
        slug = rec["slug"]
        if slug in seen_slugs:
            raise RuntimeError(f"judges.json: slug collision on {slug!r}")
        seen_slugs.add(slug)
        manifest = photos.get(name)
        if not manifest or manifest.get("status") != "ok" or not manifest.get("local_path"):
            raise RuntimeError(
                f"judges.json: no self-hosted photo for {name!r} "
                f"(manifest status: {(manifest or {}).get('status')}); "
                "initials fallback is not a build-time default"
            )

        contacts: list[dict] = []
        room = str(rec.get("room") or "").strip()
        if room:
            contacts.append({"label": "Courtroom", "display": room, "href": ""})
        bailiff = str(rec.get("bailiff") or "").strip()
        if bailiff:
            contacts.append({"label": "Bailiff", "display": bailiff, "href": ""})
        phone = str(rec.get("phone") or "").strip()
        if phone:
            contacts.append({"label": "Chambers", "display": phone, "href": _tel_href(phone)})
        fax = str(rec.get("fax") or "").strip()
        if fax:
            contacts.append({"label": "Fax", "display": fax, "href": ""})
        email = str(rec.get("email") or "").strip()
        if email:
            email_href = sanitize_email_href(email)
            contacts.append(
                {
                    "label": "Chambers email",
                    "display": email,
                    "href": f"mailto:{email_href}" if email_href else "",
                }
            )
        law_clerk = str(rec.get("law_clerk") or "").strip()
        if law_clerk:
            contacts.append({"label": "Law clerk", "display": law_clerk, "href": ""})

        judges.append({
            "name": name,
            "slug": slug,
            "court": court,
            "court_chip": court if court == "Common Pleas" else "Municipal Court",
            # The ingested feed carries no district/division, presiding flag,
            # or standing-orders text; those corpus-only fields stay empty.
            "sub_chip": "",
            "presiding": False,
            "photo_src": f"{base_url}{manifest['local_path']}",
            "contacts": contacts,
            "bio": str(rec.get("bio") or ""),
            "standing_orders": "",
            "source_url": str(rec.get("source_url") or ""),
            "search_text": " ".join([name, room, bailiff]).lower(),
        })

    # _judges_from_ingested_json() already returns both lists sorted by
    # (last_name, name); the presiding-first ordering needed the corpus-only
    # presiding flag, so the loader order stands.
    common_pleas = [j for j in judges if j["court"] == "Common Pleas"]
    municipal = [j for j in judges if j["court"] == "Municipal"]

    provenance = {
        "feed": "data/court_judges.json",
        "captured": "2026-09-20",
        "sources": [
            {
                "label": "hamiltoncountycourts.org judge profile pages",
                "url": "https://hamiltoncountycourts.org",
            }
        ],
        "note": "All 30 portraits self-hosted; manifest at /static/judges/provenance.json",
    }
    page = env.get_template("judges.html").render(
        common_pleas=common_pleas,
        municipal=municipal,
        judges_total=len(judges),
        provenance=provenance,
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "judges" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


# --- Court-reference tab feeds (spec 2.3, 5.1, 5.5): jury.json / rules.json.
# The tab-build feeds are read-only build inputs; the build never edits them.
_TAB_FEEDS_DIR = Path(
    os.environ.get(
        "HCJC_TAB_FEEDS_DIR",
        str(Path(__file__).parents[1] / ".." / "firecrawl-zips" / "tab-build-2026-09-21" / "feeds"),
    )
).resolve()


def _load_tab_feed(name: str) -> dict:
    """Load one court-reference tab feed JSON; fail closed on any error."""
    path = _TAB_FEEDS_DIR / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.warning("tab feed %s unreadable: %s", path, e)
        return {}


def _pdf_url_from_source_path(source_path: str) -> str:
    """Rebuild the official wp-content PDF URL from a staged pdf-text path.

    Staged form: pdf-text/hamiltoncountycourts.org_wp-content_uploads_<YYYY>_<MM>_<File>.pdf.txt
    Official form: https://hamiltoncountycourts.org/wp-content/uploads/<YYYY>/<MM>/<File>.pdf
    Every URL produced here is HEAD-checked against the live court host before
    publish (spec V5); sanitize_outbound_url still gates the href.
    """
    m = source_path.replace("pdf-text/hamiltoncountycourts.org_wp-content_uploads_", "", 1)
    if m == source_path or not m.endswith(".txt"):
        return ""
    stem = m[: -len(".txt")]
    parts = stem.split("_", 2)
    if len(parts) != 3 or not (parts[0].isdigit() and parts[1].isdigit()):
        return ""
    return f"https://hamiltoncountycourts.org/wp-content/uploads/{parts[0]}/{parts[1]}/{parts[2]}"


def _prose_paragraphs(text: str) -> list[str]:
    """Split extracted court text into paragraphs, dropping page-number lines.

    Verbatim: line content is never edited, only regrouped. Lines that are
    nothing but a page number (digits, optional whitespace) are dropped.
    """
    paras: list[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.isdigit():
            continue
        paras.append(s)
    return paras


# ---------------------------------------------------------------------------
# Jury tab (/jury/): prose plus directory (spec 2.3 Jury).
# ---------------------------------------------------------------------------

_JURY_QA = [
    ("Who may be called to serve as a juror?",
     "You may be called to serve if you are at least 18 years old, a United States citizen and a resident of Hamilton County. In addition, you must have a reasonable knowledge of English and be physically and mentally capable of serving."),
    ("How did my name get selected for jury duty?",
     "Jurors' names are selected at random by a computer from a list of registered voters provided by the Board of Elections."),
    ("How long will I be required to serve?",
     "Normal length of service is for two weeks. However, if you are not serving on a jury in progress, you will call a recording each night for reporting instructions for the next day. If your services are not required, it is recommended that you report to work."),
    ("Do I get paid for jury duty?",
     "You will receive a fee of $30.00 for each day that you are required to attend. Work statements for your company indicating the days that you served as a juror and the amount paid will be furnished upon request."),
    ("What should I wear for jury duty?",
     "Wear comfortable clothing that enhances the dignity of the Court and emphasizes the seriousness of your responsibility. Shorts, hats, tank tops, tee-shirts, sweatsuits, or other such informal attire is not considered appropriate in the courtroom. Because the Courthouse is an older building the Jury Commission Office tends to run either hot or cold; it is recommended that you come prepared with a jacket for colder temperatures."),
    ("What hours will I serve?",
     "Normal business hours at the Courthouse are from 8:00 a.m. to 4:00 p.m. On days that you report for jury service, you can expect to be there during its normal hours. A specific time that you will need to appear by will be given with your nightly jury instructions, but the building will open at 8:00 a.m. If not selected for a jury, you may be able to leave early. Jurors will be given a lunch break and may be given other breaks during a trial. On occasion, a trial will continue beyond the normal working hours; if this happens, you may need to arrange your schedule to allow you to stay longer."),
    ("Is it possible that I might report for jury service but not sit on a jury?",
     "Yes. The parties involved in a case generally seek to settle their differences and avoid the expense and time of a trial. Sometimes the case is settled just a few moments before the trial begins. Though many trials are scheduled daily, the Court does not know until that morning how many will actually go to trial. But your time spent waiting is not wasted; your presence encourages settlement."),
    ("Why doesn't my summons have a time to appear if I am a Petit Juror?",
     "If you are a Petit Juror you will not automatically be appearing on the date listed on your summons that you received in the mail. Instead you must check the Juror Hotline (513-946-5879) or the court's reporting-instructions page after 4:00 p.m. the weekend prior to the date on your summons for your reporting instructions. If you are to appear you will be given a time to appear within the message. If you need to appear on the initial date from your summons the time will most likely be 8:30 a.m. Other days your reporting time may vary. Grand jurors are always to report on the date and time listed on your summons."),
    ("Can I bring food and drinks into the courthouse?",
     "Yes. You are more than welcome to pack your lunch and any drinking vessel that you prefer so long as it has a lid. For your convenience the Jury Commission Office is equipped with a refrigerator, freezer, and 2 microwaves. Do not bring metal cutlery as it is possible it could be confiscated at the security checkpoint upon arrival. Plastic cutlery and plates are available here for you to use."),
    ("A note on security",
     "Deputy Sheriffs will no longer be issuing claim tickets for items deemed by them to be dangerous items. This list includes, but is not limited to: pocket knives, scissors, mace, or any other weapon. If you feel you have a dangerous item in your possession you will need to leave it in your car. The Sheriff will not let you in the building with these items."),
]

_JURY_AMENITIES = [
    "Three 55-inch flat screen televisions with cable access",
    "Desktop computers with internet",
    "Wireless internet",
    "4 cell phone charging stations",
    "Books (donated by the Cincinnati Public Library)",
    "Private bathrooms",
    "Jurors quiet area (Room 468)",
    "Private room for nursing mothers",
    "Landline telephone access",
    "Free coffee, tea, and water",
    "Refrigerator, freezer, and microwave access",
    "Plastic cutlery (forks, spoons, and knives) and paper plates available",
    "Vending machines for both snacks and drinks (available for pay)",
    "Complimentary: Tylenol, Advil, Aleve, and Aspirin available upon request",
]

_JURY_CREED = [
    "I am a JUROR.",
    "I am a seeker after truth.",
    "I must listen carefully and with concentration to all of the evidence.",
    "I must heed and follow the instructions of the Court.",
    "I must respectfully and attentively follow the arguments of the lawyers, dispassionately seeking to find and follow the silver thread of truth through their conflicting assertions.",
    "I must lay aside all bias and prejudice.",
    "I must be led by my intelligence and not by my emotions.",
    "I must respect the opinions of my fellow jurors, as they must respect mine, and in a spirit of tolerance and understanding must endeavor to bring the deliberations of the whole jury to agreement upon a verdict: but I must never assent to a verdict which violates the instructions of the Court or which finds as a fact that which, under the evidence and in my conscience, I believe to be untrue.",
    "In fine, I must apply the Golden Rule by putting myself impartially in the place of the plaintiff, and of the defendant, remembering that although I am a juror today passing upon the rights of others, tomorrow I may be a litigant whose rights other jurors shall pass upon.",
    'My verdict must do justice, for what is just is "true and righteous altogether"; and when my term of jury service is ended, I must leave it with my citizenship unsullied and my conscience clear.',
]

_JURY_CONTACT = [
    ("Jury Commissioner, Bradley J. Seitz", "513-946-5880, bseitz@cms.hamilton-co.org"),
    ("Jury Clerk, Alicia Vollner", "513-946-5882"),
    ("Jury Clerk, Liz Jeffries", "513-946-5881"),
    ("Juror information line", "513-946-5879"),
    ("Jury response email", "juryresponse@cms.hamilton-co.org (response must be scanned as an attachment; do NOT respond in the body of an email)"),
    ("Jury office fax", "513-946-5885"),
    ("Office", "Hamilton County Courthouse, 1000 Main Street, Room 455, Cincinnati, Ohio 45202"),
]


def _render_jury_page(env: Environment, out_dir: Path) -> None:
    """Jury Duty tab: hero link-out to the live court reporting page, scam
    alert (with the 2023 press release date-labeled in the archival block),
    contact, Q&A, excuses, amenities, work statements and check re-issue,
    creed, and orientation video. Reporting instructions are never cached:
    the hero card routes to the court's live page with the link-verified date.
    """
    feed = _load_tab_feed("jury.json")
    items = {i.get("id", ""): i for i in feed.get("items", []) if isinstance(i, dict)}
    reporting = items.get(
        "hamiltoncountycourts.org_index.php_jury-reporting-instructions_.json", {}
    )
    reporting_url = sanitize_outbound_url(
        reporting.get("url", "https://hamiltoncountycourts.org/index.php/jury-reporting-instructions/")
    )
    page = env.get_template("jury.html").render(
        active_nav="jury",
        reporting_url=reporting_url,
        link_verified_date=feed.get("built_date", "2026-09-21"),
        reporting_live_date=reporting.get("live_date", ""),
        jury_qa=_JURY_QA,
        jury_amenities=_JURY_AMENITIES,
        jury_creed=_JURY_CREED,
        jury_contact=_JURY_CONTACT,
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "jury" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------
# Rules tab (/rules/): versioned corpus (spec 2.3 Rules).
# ---------------------------------------------------------------------------

_RULE_AMENDMENT_WHAT_CHANGED = {
    "31": "Any civil case filed in the Court of Common Pleas General Division may be referred to mediation by order of the Court.",
    "17": 'Technology plan adopted "Pursuant to Ohio Superintendence Rule 3.03," describing "what technical tools the court has to assist" court customers.',
    "18": 'Compliance Plan for the submission of Fingerprints, Incident Tracking Numbers (ITN) and case disposition numbers; Mental Health Adjudications (Hopper Act); Protections Orders [sic]; and Bureau of Motor Vehicle related convictions.',
}


def _render_rules_page(env: Environment, out_dir: Path) -> None:
    """Local Rules tab: the post-book amendment layer (Rules 31, 17, 18)
    first, the 4-24-26 rules book with its 47-entry TOC, the Municipal Court
    rule index, and the archival block (50 superseded standalone rules plus
    the archived Municipal Rule 11 proposal). The 2017 Rule 24 text is never
    published (dropped from every feed per owner decision).
    """
    feed = _load_tab_feed("rules.json")
    book = feed.get("canonical_rules_book", {}) or {}
    book_url = sanitize_outbound_url(
        _pdf_url_from_source_path(book.get("source_path", ""))
    )

    amendments = []
    for a in feed.get("amendments", []):
        rule_no = str(a.get("rule", ""))
        effective = a.get("effective")
        amendments.append({
            "rule": rule_no,
            "title": a.get("title", ""),
            "court": a.get("court", ""),
            "effective_display": effective if effective else "not stated",
            "effective_caveat": a.get("effective_provenance", ""),
            "what_changed": _RULE_AMENDMENT_WHAT_CHANGED.get(rule_no, ""),
            "source_url": sanitize_outbound_url(_pdf_url_from_source_path(a.get("source_path", ""))),
            "source_label": _pdf_url_from_source_path(a.get("source_path", "")).rsplit("/", 1)[-1],
            "full_text": _prose_paragraphs(a.get("full_text", "")),
        })

    toc = [
        {"rule": str(e.get("rule", "")), "title": e.get("title", "")}
        for e in book.get("toc", [])
    ]

    municipal = feed.get("municipal", {}) or {}
    html_rules = []
    for e in municipal.get("html_rules", []):
        html_rules.append({
            "title": e.get("title", ""),
            "url": sanitize_outbound_url(e.get("url", "")),
        })
    civil_pdfs = []
    for e in municipal.get("civil_rules_pdfs", []):
        url = _pdf_url_from_source_path(e.get("source_path", ""))
        civil_pdfs.append({
            "title": e.get("title", ""),
            "url": sanitize_outbound_url(url),
            "label": url.rsplit("/", 1)[-1],
        })

    archival = []
    for e in feed.get("archival_standalone_rules", []):
        archival.append({
            "rule": str(e.get("rule", "")) if e.get("rule") else "",
            "title": e.get("title", ""),
            "status": e.get("status", ""),
        })

    proposed = []
    for e in feed.get("proposed_amendments_archived", []):
        proposed.append({
            "title": e.get("title", ""),
            "url": sanitize_outbound_url(e.get("url", "")),
            "item": e.get("proposed_item", ""),
            "closed": e.get("comment_period_closed", ""),
            "extract_note": e.get("proposed_pdf_note", ""),
            "contact": e.get("contact_per_page", ""),
        })

    page = env.get_template("rules.html").render(
        active_nav="rules",
        book_effective=book.get("effective", "2026-04-24"),
        book_url=book_url,
        book_sha256=book.get("source_sha256", ""),
        toc=toc,
        toc_count=len(toc),
        amendments=amendments,
        amendment_count=len(amendments),
        municipal_html=html_rules,
        municipal_pdf=civil_pdfs,
        archival=archival,
        archival_count=len(archival),
        proposed=proposed,
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "rules" / "index.html"
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


# ---------------------------------------------------------------------------
# Forms (/forms/) and Services/Programs (/services/) tab pages.
# Source feeds are resolved through _TAB_FEEDS_DIR (defined above with the
# jury/rules feeds: HCJC_TAB_FEEDS_DIR env override, else the repo-relative
# tab-build feeds dir). No absolute machine paths: the laptop checkout path
# must never appear here.
# (forms.json, services-programs.json). Templates render exactly what the
# feeds contain; nothing is invented. Form link verification results live in
# web/forms_source_status.json (checked 2026-09-22): rows whose official
# source URL failed verification render "Official source pending
# verification" per spec 5.4, never a dead link.
_FORMS_LINK_STATUS_PATH = Path(__file__).resolve().parent / "forms_source_status.json"


def _load_court_forms_feed(name: str) -> dict:
    """Load a staged tab-build feed. Fail soft: a missing or unreadable feed
    logs a warning and returns {}, and the forms/services renderers publish
    an empty page with a note instead of failing the build."""
    path = _TAB_FEEDS_DIR / name
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.error("tab feed %s unreadable: %s", path, e, exc_info=True)
        return {}
    if not isinstance(raw, dict):
        log.warning("tab feed %s schema violation: top level is not an object", path)
        return {}
    return raw


def _form_file_type(source_txt: str) -> str:
    if source_txt.endswith(".docx.txt") or source_txt.endswith(".doc.txt"):
        return "Word"
    return "PDF"


def _form_court(lead: str | None) -> str:
    """Court derived from the feed lead text only. Empty when not derivable."""
    text = (lead or "").upper()
    has_common = "COMMON PLEAS" in text
    has_municipal = "MUNICIPAL COURT" in text
    if has_common and has_municipal:
        return "Common Pleas and Municipal"
    if has_municipal:
        return "Municipal Court"
    if has_common:
        return "Common Pleas"
    return ""


# Defect #2 (2026-09-22, owner-directed): the /forms/ page rendered each
# form's raw extracted-PDF-text lead as a visible wall of text. Leads no
# longer ship to the template; each row gets a one-line human blurb composed
# from the feed's own category/court/revision fields. Nothing is invented:
# the purpose labels humanize the feed's category slugs.
_FORM_PURPOSE = {
    "plea": "Plea form",
    "discovery": "Discovery plan form",
    "jury-waiver": "Jury trial waiver",
    "indigency": "Indigency affidavit",
    "scheduling": "Scheduling order form",
    "mediator": "Mediation application",
    "registration-notice": "Registration notice",
    "reec": "REEC docket application",
    "transcript": "Transcript request form",
    "media": "Media coverage request",
}


def _form_revision(revision: str | None) -> str:
    """Human revision label, no underscores: '2023_01' -> '2023-01 generation'."""
    rev = (revision or "").strip()
    if re.fullmatch(r"\d{4}_\d{2}", rev):
        return rev.replace("_", "-") + " generation"
    return rev


# Defect #2 (2026-09-22): title-specific one-line descriptions. Keys are the
# exact feed titles; each value paraphrases its title in plain words and
# invents nothing. Unmapped titles fall back to the category purpose.
_FORM_BLURB = {
    "Alford Plea": "Alford plea entry, pleading guilty while maintaining innocence",
    "Guilty Plea": "Standard guilty plea entry",
    "Guilty Plea, Agreed Sentence": "Guilty plea entry with an agreed sentence",
    "No Contest Plea": "No-contest plea entry",
    "Misdemeanor Guilty Plea": "Guilty plea entry for misdemeanor cases",
    "Guilty Plea, Reagan Tokes Qualifying Offense": "Guilty plea entry for a Reagan Tokes qualifying offense",
    "No Contest Plea, Reagan Tokes Qualifying Offense": "No-contest plea entry for a Reagan Tokes qualifying offense",
    "Waiver of Trial by Jury": "Written waiver of the right to a jury trial",
    "Affidavit of Indigency": "Sworn statement of inability to pay court costs",
    "Joint Discovery Plan (Jenkins, Crim.R. 26F)": "Joint discovery plan, Judge Jenkins, under Crim.R. 26(F)",
    "Crim.R. 26F Discovery Form 2": "Crim.R. 26(F) discovery form, second version",
    "Joint Discovery Plan (Goering, Crim.R. 26F)": "Joint discovery plan, Judge Goering, under Crim.R. 26(F)",
    "Joint Discovery Plan (Tallent, Crim.R. 26F)": "Joint discovery plan, Judge Tallent, under Crim.R. 26(F)",
    "Crim.R. 26F Discovery Plan v5": "Crim.R. 26(F) joint discovery plan, version 5",
    "Joint Discovery Plan (Branch, Crim.R. 26F)": "Joint discovery plan, Judge Branch, under Crim.R. 26(F)",
    "Criminal Case Scheduling Order": "Scheduling order for a criminal case",
    "Jury Scheduling Order (Silverstein)": "Jury scheduling order, Judge Silverstein",
    "Volunteer Mediator Application": "Application to serve as a volunteer mediator",
    "Contract Mediator Application (fillable)": "Fillable application for contract mediator",
    "Explanation of Duties to Register as a Sex Offender": "Explanation of sex-offender registration duties",
    "Notice of Duties to Enroll as a Violent Offender (ORC 2903.41 et seq.)": "Notice of violent-offender enrollment duties under ORC 2903.41 et seq.",
    "Notice of Duties to Register as an Arson Offender (ORC 2909.14)": "Notice of arson-offender registration duties under ORC 2909.14",
    "REEC Application (Hamilton County)": "Application for the Hamilton County REEC docket",
    "Transcript Request Form": "Request for a transcript of proceedings",
    "Media Request Form": "Request for media coverage of proceedings",
}


def _form_blurb(title: str | None, category: str | None, court: str, revision: str, prior: bool = False) -> str:
    desc = _FORM_BLURB.get(title or "")
    if desc is None:
        base = _FORM_PURPOSE.get(category or "", "Court form")
        desc = ("Prior-generation " if prior else "") + base[0].lower() + base[1:]
    return ", ".join(part for part in (desc, court, revision) if part)


def _render_forms_page(env: Environment, out_dir: Path) -> None:
    """Court Forms reference page (spec 2.3 Forms).

    Current 2026_04 generation is the default view; archival generations sit
    in a separate collapsed block; related standing forms get their own
    section. Counts come from the feed at build time.
    """
    raw = _load_court_forms_feed("forms.json")
    if not raw:
        # Feed absent (e.g. CI checkout without the tab-build feeds): publish
        # an empty page with a note instead of failing the build.
        page = env.get_template("forms.html").render(
            groups_current=[],
            groups_other=[],
            waves=[],
            counts={"current": 0, "archival": 0, "other": 0},
            forms_link_summary={"ok": 0, "pending": 0, "total": 0},
            feed_note=(
                "The court forms feed was not available when this page was built, "
                "so no forms are listed."
            ),
            generated_utc=env.globals["generated_utc"],
        )
        target = out_dir / "forms" / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        return
    try:
        link_status = json.loads(_FORMS_LINK_STATUS_PATH.read_text(encoding="utf-8"))
        status_map = link_status["forms"]
    except (OSError, json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(
            f"forms_source_status.json missing or corrupt: {e}"
        ) from e

    def _ctx(f: dict, prior: bool = False) -> dict:
        sid = f["id"]
        entry = status_map.get(sid, {"status": "pending", "url": None})
        href = entry["url"] or f["source_url"] if entry["status"] == "ok" else None
        # court is still derived from the feed lead text (feed-only parsing),
        # but the raw lead itself no longer ships to the template (defect #2).
        court = _form_court(f.get("lead"))
        revision = _form_revision(f.get("revision"))
        return {
            "id": sid,
            "title": f["title"],
            "revision": revision,
            "court": court,
            "file_type": _form_file_type(f.get("source_txt", "")),
            "blurb": _form_blurb(f.get("title"), f.get("category"), court, revision, prior),
            "note": f.get("note"),
            "href": href,
        }

    current = [_ctx(f) for f in raw.get("current", [])]
    archival = [_ctx(f, prior=True) for f in raw.get("archival", [])]
    other = [_ctx(f) for f in raw.get("other_forms", [])]
    if not current or not archival or not other:
        raise RuntimeError("forms.json schema violation: empty current/archival/other list")
    # Citizen panel 2026-09-22 (quick win 1): the pending-verification state
    # is stated once at the top of the page, not repeated on every row.
    _all_forms = current + archival + other
    _link_ok = sum(1 for f in _all_forms if f["href"])

    cat_order = [("plea", "Plea forms"), ("jury-waiver", "Waiver of Trial by Jury"),
                 ("indigency", "Affidavit of Indigency")]
    by_cat: dict[str, list] = {c: [] for c, _ in cat_order}
    for c, items in zip(
        (f["category"] for f in raw["current"]), current, strict=True
    ):
        by_cat.setdefault(c, []).append(items)
    groups_current = [(label, by_cat[c]) for c, label in cat_order if by_cat.get(c)]

    wave_order = ["2025_04", "2024_03", "2023_01", "2022_01", "2021_12", "2021_10"]
    by_wave: dict[str, list] = {w: [] for w in wave_order}
    for gen, items in zip((f["generation"] for f in raw["archival"]), archival, strict=True):
        by_wave.setdefault(gen, []).append(items)
    waves = [(f"{w.replace('_', '-')} generation", by_wave[w]) for w in wave_order if by_wave.get(w)]

    other_groups = [
        ("Discovery", [x for x, f in zip(other, raw["other_forms"], strict=True) if f["category"] == "discovery"]),
        ("Scheduling and mediation", [x for x, f in zip(other, raw["other_forms"], strict=True)
                                      if f["category"] in ("scheduling", "mediator")]),
        ("Notices and misc", [x for x, f in zip(other, raw["other_forms"], strict=True)
                               if f["category"] in ("registration-notice", "reec",
                                                    "transcript", "media")]),
    ]
    if any(not items for _, items in other_groups):
        raise RuntimeError("forms.json schema violation: empty other-forms group")

    page = env.get_template("forms.html").render(
        groups_current=groups_current,
        groups_other=other_groups,
        waves=waves,
        counts={
            "current": len(current),
            "archival": len(archival),
            "other": len(other),
        },
        forms_link_summary={
            "ok": _link_ok,
            "pending": len(_all_forms) - _link_ok,
            "total": len(_all_forms),
        },
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "forms" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


# Contact details quoted from the feed lead fields (hamiltoncountycourts.org
# program pages). The feed's leads are truncated strings, so the contacts are
# recorded here keyed by item id rather than parsed; every value below comes
# from the feed, nothing is invented.
_SERVICES_CONTACTS: dict[str, list[dict]] = {
    "pretrial-services": [
        {"role": "Director", "name": "Amy Ruehl",
         "address": "1000 Sycamore St, Rm 111, Cincinnati, Ohio 45202",
         "phone": "(513) 946-6161"},
    ],
    "pretrial-services-prosecutors-diversion-programs": [
        {"role": "Program Coordinator", "name": "Maria Karvelas",
         "address": "230 E 9th St #1150, Cincinnati, Ohio 45202",
         "phone": "(513) 946-3385"},
    ],
    "drug-court": [
        {"role": "Bailiff", "name": "Doris Vincent", "phone": "(513) 946-5770"},
        {"role": "Director", "name": "Keshia Jones", "phone": "(513) 946-5773"},
        {"role": "Certification Coordinator", "name": "Ashley Autry",
         "phone": "(513) 946-5777"},
        {"role": "Specialized Docket Assistant", "name": "Tamara Clark",
         "phone": "(513) 946-5775"},
    ],
    "felony-veterans-treatment-court": [
        {"role": "Program Director", "name": "Gary Yuratovac, Esq.",
         "phone": "(513) 618-4215"},
        {"role": "Court Coordinator", "name": "Greg Street",
         "phone": "(513) 946-3371"},
    ],
    "hamilton-county-re-entry-docket": [
        {"role": "Reentry Docket Specialist", "name": "Sheryl Miles",
         "phone": "(513) 946-5556"},
        {"role": "Director, Hamilton County Office of Reentry",
         "name": "Trina Jackson", "phone": "(513) 946-4304"},
        {"role": "Probation Officer", "name": "Mia Willright",
         "phone": "(513) 946-9767"},
    ],
}

# Complete first sentences quoted from the feed lead fields.
_SERVICES_DESCRIPTIONS = {
    "specialized-dockets-common-pleas": (
        "Specialized dockets are particular sessions of court or dockets that "
        "offer a therapeutically oriented judicial approach to providing court "
        "supervision and appropriate treatment to individuals."
    ),
    "municipal-specialized-dockets": (
        "The objective of Veterans Court is to divert veterans from the "
        "traditional criminal justice system to a treatment-based court in "
        "order to rehabilitate and assist veterans in leading a productive "
        "and law abiding life."
    ),
}


def _render_services_page(env: Environment, out_dir: Path) -> None:
    """Services and Programs directory (spec 2.3 Services).

    The authoritative home for probation, pretrial services, electronic
    monitoring, and specialized dockets. Grouped by program with contact
    info and descriptions as stated in the feed. Counts come from the feed
    at build time.
    """
    raw = _load_court_forms_feed("services-programs.json")
    if not raw:
        # Feed absent (e.g. CI checkout without the tab-build feeds): publish
        # an empty page with a note instead of failing the build.
        page = env.get_template("services.html").render(
            counts={"probation": 0, "pretrial": 0, "specialized_dockets": 0},
            probation_cards=[],
            probation_rows=[],
            pretrial_card={},
            pretrial_rows=[],
            docket_cards=[],
            docket_rows=[],
            missing_municipal_staff="",
            feed_note=(
                "The services and programs feed was not available when this page "
                "was built, so no programs are listed."
            ),
            generated_utc=env.globals["generated_utc"],
        )
        target = out_dir / "services" / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        return
    items = raw.get("items", [])
    if not items:
        raise RuntimeError("services-programs.json schema violation: no items")
    by_id = {it["id"]: it for it in items}
    by_cat: dict[str, list[dict]] = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)

    def _row(item_id: str, title: str | None = None,
             see_also: list | None = None) -> dict:
        it = by_id[item_id]
        return {
            "id": item_id,
            "title": title or it["title"],
            "href": it["page_url"],
            "contacts": _SERVICES_CONTACTS.get(item_id, []),
            "see_also": see_also or [],
            "description": _SERVICES_DESCRIPTIONS.get(item_id),
        }

    probation_cards = [
        {"title": by_id["probation-common-pleas"]["title"],
         "href": by_id["probation-common-pleas"]["page_url"]},
        {"title": by_id["probation-municipal"]["title"],
         "href": by_id["probation-municipal"]["page_url"]},
    ]
    probation_rows = [
        _row("common-pleas-probation", "Common Pleas Probation, department page"),
        _row("probation-intensive-supervision-probation-isp"),
        _row("probation-inter-state-intra-state-compact-ic"),
        _row("probation-presentence-investigation-psi"),
        _row("probation-community-service-program"),
        _row("probation-substations"),
        _row("probation-victims-services-unit"),
        _row("probation-faqs"),
        _row("probation-holiday-closures"),
        _row("probation-common-pleas-staff-directory"),
    ]

    pretrial_card = {
        "title": by_id["pretrial-services"]["title"],
        "href": by_id["pretrial-services"]["page_url"],
        "contacts": _SERVICES_CONTACTS["pretrial-services"],
    }
    pretrial_rows = [
        _row("pretrial-services-electronic-monitoring-release-unit", see_also=[
            {"label": "Bond schedule", "href": "/bond-schedule/"}]),
        _row("pretrial-services-failure-to-appear-unit", see_also=[
            {"label": "Help and free aid", "href": "/help/"}]),
        _row("pretrial-services-jail-intake-processing-bail-investigations-and-bail-review"),
        _row("pretrial-services-jail-monitoring-offender-classification-and-post-conviction-services"),
        _row("pretrial-services-court-ordered-supervision"),
        _row("pretrial-services-court-ordered-testing-for-sexually-transmitted-and-communicable-diseases"),
        _row("pretrial-services-mediation-services", see_also=[
            {"label": "Local Rules", "href": "/rules/"},
            {"label": "Help and free aid", "href": "/help/"}]),
        _row("pretrial-services-prosecutors-diversion-programs"),
        _row("pretrial-services-veteran-intervention-programs"),
        _row("pretrial-services-court-interpreter-services", see_also=[
            {"label": "Help and free aid", "href": "/help/"}]),
    ]

    docket_cards = [
        {"title": by_id["drug-court"]["title"],
         "href": by_id["drug-court"]["page_url"],
         "note": "First drug court in Ohio.",
         "contacts": _SERVICES_CONTACTS["drug-court"]},
        {"title": by_id["felony-veterans-treatment-court"]["title"],
         "href": by_id["felony-veterans-treatment-court"]["page_url"],
         "note": None,
         "contacts": _SERVICES_CONTACTS["felony-veterans-treatment-court"]},
        {"title": by_id["hamilton-county-re-entry-docket"]["title"],
         "href": by_id["hamilton-county-re-entry-docket"]["page_url"],
         "note": None,
         "contacts": _SERVICES_CONTACTS["hamilton-county-re-entry-docket"]},
    ]
    docket_rows = [
        _row("specialized-dockets-common-pleas"),
        _row("municipal-specialized-dockets"),
    ]

    sections = raw.get("sections", {})
    page = env.get_template("services.html").render(
        counts={
            "probation": sections.get("probation", len(by_cat.get("probation", []))),
            "pretrial": sections.get("pretrial", len(by_cat.get("pretrial", []))),
            "specialized_dockets": sections.get("specialized_dockets",
                                               len(by_cat.get("specialized-dockets", []))),
        },
        probation_cards=probation_cards,
        probation_rows=probation_rows,
        pretrial_card=pretrial_card,
        pretrial_rows=pretrial_rows,
        docket_cards=docket_cards,
        docket_rows=docket_rows,
        missing_municipal_staff=(
            "No Municipal staff directory exists in the corpus: the legacy "
            "capital-URL staff directory page returns a 404 ('Sorry!'), and "
            "no lowercase replacement was found."
        ),
        generated_utc=env.globals["generated_utc"],
    )
    target = out_dir / "services" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
