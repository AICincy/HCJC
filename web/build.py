"""Render the static JCStream site from data/current.json + data/changelog.json.

Output goes to ``web/_dist/`` (gitignored). The GH Actions workflow uploads
that directory to GitHub Pages.
"""

from __future__ import annotations

import argparse
import email.utils
import json
import logging
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper import cfs as cfs_mod
from scraper import cfs_pdi as cfs_pdi_mod
from scraper import courtclerk as cck
from scraper import orc as orc_mod
from scraper import shootings as shootings_mod
from scraper.match import attach_candidates
from scraper.models import ChangeEvent, HistoryRecord, Inmate, Snapshot

# Static classification data moved to web/classify.py (arch-F1, partial).
# Re-exported here so tests/test_build.py can `from web.build import _foo`.
from web.classify import (  # noqa: F401  re-exported for test_build.py access
    _DEGREE_RE, _CHAPTER_LABEL, _OFFENSE_CATEGORY, _CLS_RANK, _TIER_MAX,
    _RACE_LABEL, _SEX_LABEL, _MIN_MONTH_SIZE,
    _offense_for_code, _orc_frequency, _codes_ohio_url, _chap_slug,
    _charge_tier, _tier_counts, _primary_tier, _primary_degree, _tier_max,
    _parse_book_date, _display_date, _parse_bond_amount, _parse_md_yy,
    _short_month_label, _approx_age, _booking_seq, _avatar_initials,
    _expand_race, _expand_sex, _pct_ordinal, _rfc822, _load_explainers,
)
from web.shape import (  # noqa: F401  re-exported for test_build.py access
    _related_inmates, _crimes_of_month, _recent_booked_inmates,
    _bond_context, _upcoming_courts, _tier_breakdown,
    _top_offenses_with_orc, _all_top_offenses, _timeline_markers,
    _similar_by_statute, _statute_held_inmates, _feed_description,
    _bond_by_tier, _next_court_date, _case_numbers,
    _charge_status_summary, _card_data_attrs, _card_tip,
    _bond_total, _days_in_custody, _charges_by_chapter,
    _primary_charge_obj, _primary_charge, _primary_chapter,
    _sort_in_group, _group_by_month, _events_in_window,
    _events_for_recent, _court_calendar, _events_for_inmate,
    _strftime_nopad,
)

log = logging.getLogger("jcstream.site")

ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
PHOTOS_DIR = Path("data/photos")
# Pages serves from /docs at the repo root. Building straight there means the
# workflow can commit the site alongside the data on every sweep.
DEFAULT_OUT = Path("docs")


def build(out_dir: Path) -> int:
    current_path = Path("data/current.json")
    changelog_path = Path("data/changelog.json")

    if not current_path.exists():
        log.warning("no data/current.json yet; rendering an empty site")
        snapshot = Snapshot(generated_utc="", inmate_count=0, inmates=[])
    else:
        raw = json.loads(current_path.read_text(encoding="utf-8"))
        snapshot = Snapshot(**raw)

    if changelog_path.exists():
        events_raw = json.loads(changelog_path.read_text(encoding="utf-8"))
        events = [ChangeEvent(**e) for e in events_raw]
    else:
        events = []

    cfs_rows = cfs_mod.load_recent()
    cfs_pdi_rows = cfs_pdi_mod.load()
    shooting_rows = shootings_mod.load()
    # The matcher gets BOTH dispatch feeds (qiik-bpks often lags past its pull
    # window and comes back empty; gexm-h6bt pulls a wider window), de-duplicated
    # on event_number.
    _seen_ev: set[str] = set()
    _all_cfs: list[dict] = []
    for r in (cfs_rows + cfs_pdi_rows):
        ev = r.get("event_number") or id(r)
        if ev not in _seen_ev:
            _seen_ev.add(ev)
            _all_cfs.append(r)
    matches = attach_candidates(snapshot.inmates, _all_cfs)
    dispatch_points = _dispatch_points(_all_cfs, shooting_rows)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Cross-platform strftime for templates: `{{ dt | dt_fmt('%b %-d, %Y') }}`
    # maps %-d/%-m to %#d/%#m on Windows so the build is portable between the
    # Linux CI runner and Windows dev boxes.
    env.filters["dt_fmt"] = _strftime_nopad
    env.globals["cck_name_search"] = cck.name_search_url
    env.globals["cck_case_summary"] = cck.case_summary_url
    env.globals["base_url"] = _resolve_base_url()
    # Absolute origin (scheme + host) for RSS/Atom links, the web manifest and
    # JSON-LD — distinct from base_url, which is a path prefix and is empty when
    # we serve from a custom domain at the root.
    env.globals["site_url"] = _resolve_site_url()
    # Optional Giscus (GitHub-Discussions-backed) comments on inmate pages.
    # Activated only when JCSTREAM_GISCUS_REPO_ID is set as a secret/var; the
    # comment-policy section renders either way.
    import os as _os
    env.globals["giscus"] = {
        "repo": _os.environ.get("JCSTREAM_GISCUS_REPO", "AICincy/JCStream"),
        "repo_id": _os.environ.get("JCSTREAM_GISCUS_REPO_ID", ""),
        "category": _os.environ.get("JCSTREAM_GISCUS_CATEGORY", "Announcements"),
        "category_id": _os.environ.get("JCSTREAM_GISCUS_CATEGORY_ID", ""),
    }
    # Cache-bust the stylesheet by its CONTENT hash, not the data timestamp —
    # otherwise a CSS change with unchanged data ships new HTML against stale CSS.
    import hashlib as _hl
    _css = STATIC_DIR / "style.css"
    env.globals["css_version"] = (_hl.sha256(_css.read_bytes()).hexdigest()[:10]
                                  if _css.exists() else "dev")
    # Same pattern for the externalized JS modules.
    _main_js = STATIC_DIR / "main.js"
    _map_js = STATIC_DIR / "map.js"
    env.globals["main_js_version"] = (_hl.sha256(_main_js.read_bytes()).hexdigest()[:10]
                                      if _main_js.exists() else "dev")
    env.globals["map_js_version"] = (_hl.sha256(_map_js.read_bytes()).hexdigest()[:10]
                                     if _map_js.exists() else "dev")
    offenses = orc_mod.load_offenses()
    env.globals["orc_title"] = lambda code: orc_mod.title_for(code, offenses)
    env.globals["primary_charge"] = _primary_charge
    env.globals["primary_chapter"] = _primary_chapter
    env.globals["primary_tier"] = _primary_tier
    env.globals["primary_degree"] = _primary_degree
    env.globals["tier_max"] = _tier_max
    env.globals["tier_ladder"] = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    env.globals["bond_context"] = lambda inm: _bond_context(inm, snapshot.inmates, offenses)
    env.globals["recent_booked_inmates"] = _recent_booked_inmates(snapshot, n=6)
    env.globals["timeline_markers"] = _timeline_markers
    env.globals["display_date"] = _display_date
    env.globals["similar_by_statute"] = lambda inm: _similar_by_statute(inm, snapshot.inmates, offenses, limit=6)
    env.globals["tier_counts"] = _tier_counts
    env.globals["charge_tier"] = _charge_tier
    env.globals["avatar_initials"] = _avatar_initials
    env.globals["card_data"] = _card_data_attrs
    env.globals["card_tip"] = lambda inm: _card_tip(inm, offenses)
    env.globals["expand_race"] = _expand_race
    env.globals["expand_sex"] = _expand_sex
    env.globals["approx_age"] = _approx_age
    env.globals["booking_seq"] = _booking_seq
    env.globals["pct_ordinal"] = _pct_ordinal
    env.globals["rfc822"] = _rfc822
    env.globals["feed_description"] = _feed_description
    env.globals["bond_by_tier"] = lambda inm: _bond_by_tier(inm, offenses)
    env.globals["next_court_date"] = _next_court_date
    env.globals["case_numbers"] = _case_numbers
    env.globals["charge_status_summary"] = _charge_status_summary
    # Distinct chapters present, for the filter dropdown.
    _chap_set: dict[str, str] = {}
    for inm in snapshot.inmates:
        ch = _primary_chapter(inm)
        if ch:
            _chap_set[_chap_slug(ch["label"])] = ch["label"]
    env.globals["all_chapters"] = sorted(_chap_set.items(), key=lambda kv: kv[1])
    env.globals["bond_total"] = _bond_total
    env.globals["days_in_custody"] = _days_in_custody
    env.globals["charges_by_chapter"] = _charges_by_chapter
    env.globals["crimes_of_month"] = _crimes_of_month
    env.globals["inmates_by_id"] = {i.inmate_number: i for i in snapshot.inmates}
    orc_freq = _orc_frequency(snapshot.inmates)
    env.globals["orc_freq"] = lambda code: orc_freq.get(orc_mod.normalize_code(code), 0)
    env.globals["codes_ohio_url"] = _codes_ohio_url
    env.globals["related_inmates"] = lambda inm: _related_inmates(inm, snapshot.inmates)
    env.globals["all_inmates_total"] = snapshot.inmate_count

    _warn_about_unmapped_orcs(snapshot.inmates, offenses)

    by_month = _group_by_month(snapshot.inmates)
    # Month-nav data: short label + count.
    nav_months = [
        {"slug": m.replace(" ", "-").lower(), "label": _short_month_label(m), "count": len(g)}
        for m, g in by_month
    ]
    # Only the newest month renders expanded; older ones collapsed by default.
    expanded_months = {m for m, _ in by_month[:1]}
    # "in the last 24h" must mean the EVENT happened in the last 24h AND (for
    # 'booked') the HCSO booking date is recent too — otherwise the first-ever
    # sweep counts every inmate it ever saw as "booked in the last 24h".
    recent_24h = _events_for_recent(events, hours=24)
    recent_booked = sum(1 for e in recent_24h if e.event == "booked")
    recent_released = sum(1 for e in recent_24h if e.event == "released")
    events_recent = list(reversed(_events_for_recent(events, hours=8)))[:12]
    trend = _update_history(snapshot, recent_booked, recent_released)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    _render_index(env, snapshot, by_month, nav_months, expanded_months,
                  events_recent, recent_booked, recent_released, trend,
                  cfs_rows, shooting_rows, len(dispatch_points), out_dir)
    _render_inmates(env, snapshot, matches, events, out_dir)
    _render_feeds(env, events, out_dir)
    _render_data_page(env, snapshot, out_dir)
    _render_stats_page(env, snapshot, by_month, trend, out_dir)
    _render_statute_page(env, snapshot, offenses, out_dir)
    _render_court_page(env, snapshot, out_dir)
    _render_visit_page(env, out_dir)
    _render_help_page(env, out_dir)
    _render_courts_page(env, out_dir)
    _copy_static(out_dir)
    _copy_photos(out_dir)
    _write_manifest(out_dir, env.globals["base_url"])
    _write_search_json(out_dir, snapshot)
    _write_dispatches(out_dir, dispatch_points)
    _write_cname(out_dir)
    _write_well_known(out_dir, env.globals["site_url"], snapshot.generated_utc)
    _write_checksums(out_dir)
    # Tell GitHub Pages NOT to Jekyll-process the built site.
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    log.info(
        "site built: %d inmates, %d recent events -> %s",
        snapshot.inmate_count,
        len(events),
        out_dir,
    )
    return 0





def _resolve_base_url() -> str:
    """Return the URL path prefix the site is served from (no trailing slash).

    Order of precedence:
      1. ``JCSTREAM_SITE_BASE_URL`` env var (explicit override, e.g. ``/jcstream`` or empty)
      2. Derived from GitHub Actions env: ``GITHUB_REPOSITORY`` -> ``/<repo>``
      3. Default: empty string (local serving from doc root)

    NOTE: this is distinct from ``JCSTREAM_BASE_URL`` which the scraper uses
    as the *HCSO* HTTP origin (``https://www.hcso.org``).
    """
    explicit = os.environ.get("JCSTREAM_SITE_BASE_URL")
    if explicit is not None:
        return explicit.rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        return "/" + repo.split("/", 1)[1].rstrip("/")
    return ""


def _resolve_site_url() -> str:
    """Absolute site origin (no trailing slash) for feeds / manifest / JSON-LD.

      1. ``JCSTREAM_SITE_URL`` env var (explicit, e.g. ``https://www.aretheyinjail.com``)
      2. ``https://<JCSTREAM_CNAME>`` if a custom domain is configured
      3. Derived from GitHub Actions: ``https://<owner>.github.io/<repo>``
      4. Fallback: ``https://aicincy.github.io/JCStream``
    """
    explicit = os.environ.get("JCSTREAM_SITE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    cname = (os.environ.get("JCSTREAM_CNAME", "") or "").strip()
    if cname:
        return "https://" + cname.rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}"
    return "https://aicincy.github.io/JCStream"


def _dispatch_points(cfs_rows: list[dict], shooting_rows: list[dict], limit: int = 600) -> list[dict]:
    """Geocoded points for the homepage map: recent CPD arrest/citation/report
    dispatches plus reported shootings that carry coordinates.

    Compact keys keep dispatches.json small: la/lo (lat/lon), k (kind:
    'cfs'|'shooting'), d (disposition/type), a (address/block), n (neighborhood),
    t (timestamp as the source prints it).
    """
    def _coord(row: dict) -> tuple[float, float] | None:
        try:
            la = float(row.get("latitude_x"))
            lo = float(row.get("longitude_x"))
        except (TypeError, ValueError):
            return None
        # Greater-Cincinnati sanity box — drops 0,0 and obviously bad rows.
        if not (38.0 < la < 40.0 and -85.5 < lo < -83.5):
            return None
        return (round(la, 5), round(lo, 5))

    pts: list[dict] = []
    for r in cfs_rows:
        c = _coord(r)
        if not c:
            continue
        pts.append({"la": c[0], "lo": c[1], "k": "cfs",
                    "d": (r.get("disposition_text") or "").strip(),
                    "a": (r.get("address_x") or "").strip(),
                    "n": (r.get("cpd_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                    "t": (r.get("create_time_incident") or "").strip()})
    for r in shooting_rows:
        c = _coord(r)
        if not c:
            continue
        pts.append({"la": c[0], "lo": c[1], "k": "shooting",
                    "d": (r.get("type") or "SHOOTING").strip() or "SHOOTING",
                    "a": (r.get("streetblock") or "").strip(),
                    "n": (r.get("sna_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                    "t": (r.get("datetimeoccured") or r.get("dateoccurred") or "").strip()})
    return pts[:limit]


def _write_dispatches(out_dir: Path, points: list[dict]) -> None:
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(points),
        "points": points,
    }
    (out_dir / "dispatches.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _warn_about_unmapped_orcs(inmates: list[Inmate], offenses: dict[str, str]) -> None:
    codes = [c.orc_code for inm in inmates for c in inm.charges if c.orc_code]
    missing = orc_mod.codes_without_titles(codes, offenses)
    # Strip HCSO's placeholder rows (0000.00, 0001.00, 0002.00 etc.) — those
    # are sentinel values the booking system writes when a charge has been
    # entered but the ORC section hasn't yet been classified. They're not real
    # ORC codes and can't be looked up. Filtering keeps the warning's signal
    # focused on genuine lookup gaps that the orc-curator should fix.
    missing = [c for c in missing if not c.startswith(("0000", "0001", "0002"))]
    if missing:
        log.info("ORC titles missing for %d codes: %s", len(missing), ", ".join(missing[:20]))


_CFS_DT_FORMATS = (
    "%Y %b %d %I:%M:%S %p",   # CFS: "2026 May 12 12:09:57 AM"
    "%m/%d/%Y %I:%M:%S %p",   # shootings: "5/10/2026 10:35:00 PM"
    "%Y-%m-%dT%H:%M:%S",      # ISO-8601 (Socrata default for some columns)
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)


def _parse_dispatch_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    # ISO with trailing Z
    if s.endswith("Z"):
        s = s[:-1]
    for fmt in _CFS_DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _filter_last_days(rows: list[dict], field_candidates: tuple[str, ...], days: int = 30) -> list[dict]:
    """Return rows whose date in one of ``field_candidates`` is within the
    last ``days`` days. Rows with unparseable dates are kept (defensive: the
    Socrata feeds occasionally ship a row with a NULL date and we'd rather
    surface it than silently drop it). Sorted newest-first.
    """
    cutoff = datetime.now() - timedelta(days=days)
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


def _update_history(snapshot: Snapshot, booked_24h: int, released_24h: int) -> dict:
    """Append/replace today's roster-size record in data/history.json (committed
    by the cron) and return a small `trend` dict for the homepage:
      {today, yesterday, delta, spark: [counts...], spark_dates: [...]}
    History is a series of *counts*, not of individuals — it doesn't archive
    anyone, so it's consistent with 'we mirror, we don't archive'.
    """
    path = Path("data/history.json")
    # data-F7: validate each record on load via HistoryRecord. A structurally
    # valid but wrong-typed file (e.g. count as a string) would otherwise
    # crash _compute_stats or drive a bogus sparkline. Drop invalid records
    # rather than failing the build; the next write self-heals.
    raw: list[dict] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for entry in data:
                    try:
                        raw.append(HistoryRecord(**entry).model_dump())
                    except Exception as e:
                        log.warning("dropping invalid history.json record %r: %s", entry, e)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("could not read history.json (%s); starting fresh", e)
    hist = raw
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rec = HistoryRecord(
        date=today,
        count=snapshot.inmate_count,
        booked_24h=booked_24h,
        released_24h=released_24h,
    ).model_dump()
    if hist and hist[-1].get("date") == today:
        hist[-1] = rec
    else:
        hist.append(rec)
    hist = hist[-400:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hist, separators=(",", ":")), encoding="utf-8")
    # build the trend
    counts = [h.get("count", 0) for h in hist]
    today_n = counts[-1] if counts else snapshot.inmate_count
    yest_n = counts[-2] if len(counts) >= 2 else None
    spark = hist[-60:]
    last7 = hist[-7:]
    return {
        "today": today_n,
        "yesterday": yest_n,
        "delta": (today_n - yest_n) if yest_n is not None else None,
        "spark": [h.get("count", 0) for h in spark],
        "spark_dates": [h.get("date", "") for h in spark],
        "days_tracked": len(hist),
        "booked_7d": sum(h.get("booked_24h", 0) for h in last7),
        "released_7d": sum(h.get("released_24h", 0) for h in last7),
        "churn_days": len(last7),
    }


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
    # Pre-index events by inmate_number for O(1) per-render lookup instead of
    # filtering the full changelog (Phase 9: capped at 10000) for each inmate.
    events_by_inmate: dict[str, list[ChangeEvent]] = {}
    for e in events:
        events_by_inmate.setdefault(e.inmate_number, []).append(e)
    for ev_list in events_by_inmate.values():
        ev_list.sort(key=lambda e: e.timestamp_utc or "")
    # Phase 11: load the crowdsourced courtclerk submissions once so each
    # inmate.render() can grab their own list in O(1).
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

    # "booked" feed = booked events whose HCSO booking date is genuinely recent —
    # so a sweep that re-discovers months-old records (e.g. after a degraded
    # cycle) doesn't fill booked.xml with stale "new bookings".
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
    # Copy the raw data files into the published tree so they're fetchable.
    data_out = out_dir / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    from scraper.open_data_feeds import FEEDS
    supplemental = [f.filename for f in FEEDS]
    for name in ("current.json", "changelog.json", "history.json", "cfs_recent.json",
                 "shootings_recent.json",
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


def _write_manifest(out_dir: Path, base_url: str) -> None:
    """Minimal web app manifest — gives the bookmark a name/icon/theme.
    Deliberately `display: browser` (not a PWA): a stale cached jail roster
    would be misleading, so no service worker."""
    manifest = {
        "name": "JCStream — Hamilton County, OH jail roster mirror",
        "short_name": "JCStream",
        "description": "Public-records mirror of the Hamilton County (Ohio) Justice Center inmate roster.",
        "start_url": (base_url or "") + "/",
        "scope": (base_url or "") + "/",
        "display": "browser",
        "background_color": "#14181f",
        "theme_color": "#14181f",
        "icons": [],
    }
    (out_dir / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _compute_stats(snapshot: Snapshot, by_month) -> dict:
    """Aggregates for the /stats/ page — all from the current snapshot."""
    inmates = snapshot.inmates
    n = len(inmates)
    months = [(m, len(g)) for m, g in by_month]                       # newest-first already
    offenses = _crimes_of_month(inmates)                              # [{label, cls, count}] desc
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
    # bonds
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
    # charges per inmate
    ch_counts = [len(inm.charges) for inm in inmates]
    avg_ch = (sum(ch_counts) / n) if n else 0
    max_ch = max(ch_counts) if ch_counts else 0
    one_charge = sum(1 for c in ch_counts if c == 1)
    # photo coverage
    with_photo = sum(1 for inm in inmates if inm.photo_filename)
    # days in custody (where parseable)
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


def _load_caselaw_cache() -> dict:
    """Read data/orc_caselaw.json (populated by scripts/refresh_caselaw.py).
    Missing or malformed file degrades silently to {} so the statute page
    still renders without the case-law block."""
    p = Path("data/orc_caselaw.json")
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("by_code", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _render_statute_page(env: Environment, snapshot: Snapshot, offenses: dict, out_dir: Path) -> None:
    """Statute lookup — one page with each ORC section currently on the roster."""
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


def _write_search_json(out_dir: Path, snapshot: Snapshot) -> None:
    """Compact searchable index of the current roster — useful for API
    consumers and as a base for a future client-side search UI.
    One row per inmate: n=name, c=primary offense category, t=tier, id."""
    rows = []
    for inm in snapshot.inmates:
        tier = _primary_tier(inm)
        chap = _primary_chapter(inm)
        rows.append({
            "n": inm.full_name,
            "c": (chap["label"] if chap else _primary_charge(inm)) or "",
            "t": tier["kind"] if tier else "",
            "b": inm.booking_date or "",
            "id": inm.inmate_number,
        })
    payload = {
        "generated_utc": snapshot.generated_utc,
        "count": len(rows),
        "rows": rows,
    }
    (out_dir / "search.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _write_cname(out_dir: Path) -> None:
    """GitHub Pages custom-domain file. Written from JCSTREAM_CNAME so it
    survives the docs/ rebuild; skipped if the env var is empty."""
    import os as _os
    domain = (_os.environ.get("JCSTREAM_CNAME", "") or "").strip()
    if domain:
        (out_dir / "CNAME").write_text(domain + "\n", encoding="utf-8")


def _write_well_known(out_dir: Path, site_url: str, generated_utc: str) -> None:
    """robots.txt + .well-known/security.txt + humans.txt — make the
    don't-amplify posture explicit at the protocol level and give crawlers /
    researchers a clear, no-fee contact point. RSS readers ignore robots.txt,
    so the feeds stay usable for people."""
    issues = "https://github.com/AICincy/JCStream/issues"
    (out_dir / "robots.txt").write_text(
        "# JCStream mirrors public records and asks search engines not to index it\n"
        "# (every page also carries <meta name=\"robots\" content=\"noindex\">).\n"
        "# Feeds and raw data are linked from /data/ — RSS readers don't honour\n"
        "# robots.txt, so subscriptions still work.\n"
        "User-agent: *\n"
        "Disallow: /\n",
        encoding="utf-8",
    )
    # security.txt (RFC 9116) — Expires is required; keep it ~1 year out (the
    # cron rebuilds every ~30 min so it never actually goes stale).
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    wk = out_dir / ".well-known"
    wk.mkdir(parents=True, exist_ok=True)
    (wk / "security.txt").write_text(
        f"# JCStream is a static mirror of public records (ORC §149.43). For data\n"
        f"# corrections, sealing/expungement removal, or any security or privacy\n"
        f"# concern, open an issue — there is never a fee.\n"
        f"Contact: {issues}\n"
        f"Expires: {expires}\n"
        f"Preferred-Languages: en\n"
        + (f"Canonical: {site_url}/.well-known/security.txt\n" if site_url else ""),
        encoding="utf-8",
    )
    (out_dir / "humans.txt").write_text(
        "/* PROJECT */\n"
        "  JCStream — mirror of the Hamilton County, OH Justice Center inmate roster\n"
        f"  Site: {site_url or 'https://www.aretheyinjail.com'}\n"
        "  Source: https://github.com/AICincy/JCStream (MIT)\n"
        f"  Corrections / sealing / removal: {issues} — no fee, ever\n"
        "\n/* DATA */\n"
        "  HCSO public inmate roster (ORC §149.43) + Cincinnati Open Data feeds\n"
        "  No historical archive — records drop off when HCSO removes them\n"
        f"  Rebuilt every ~30 minutes via GitHub Actions · last build {generated_utc or '—'}\n"
        "\n/* BUILT WITH */\n"
        "  Python · Jinja2 · httpx · selectolax · Pillow · GitHub Pages\n",
        encoding="utf-8",
    )


def _write_checksums(out_dir: Path) -> None:
    """SHA-256 manifest of the published data files — cheap tamper-evidence
    on top of the (already authenticated) git history. Not 'Web3'; just hygiene."""
    import hashlib
    data_out = out_dir / "data"
    if not data_out.exists():
        return
    lines = []
    for f in sorted(data_out.glob("*.json")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        lines.append(f"{h}  {f.name}")
    if lines:
        (data_out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_static(out_dir: Path) -> None:
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, out_dir / "static", dirs_exist_ok=True)


def _copy_photos(out_dir: Path) -> None:
    if PHOTOS_DIR.exists() and any(PHOTOS_DIR.iterdir()):
        shutil.copytree(PHOTOS_DIR, out_dir / "photos", dirs_exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the JCStream static site")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return build(args.out)


if __name__ == "__main__":
    sys.exit(main())
