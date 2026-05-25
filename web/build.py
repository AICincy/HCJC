"""Render the static JCStream site from data/current.json + data/changelog.json.

Output goes to ``web/_dist/`` (gitignored). The GH Actions workflow uploads
that directory to GitHub Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper import cfs as cfs_mod
from scraper import cfs_pdi as cfs_pdi_mod
from scraper import courtclerk as cck
from scraper import orc as orc_mod
from scraper import shootings as shootings_mod
from scraper.match import attach_candidates
from scraper.models import ChangeEvent, HistoryRecord, Inmate, Snapshot
from web.classify import (
    _approx_age,
    _avatar_initials,
    _booking_seq,
    _chap_slug,
    _charge_tier,
    _codes_ohio_url,
    _display_date,
    _expand_race,
    _expand_sex,
    _load_explainers,
    _orc_chapters,
    _orc_frequency,
    _parse_book_date,
    _pct_ordinal,
    _primary_degree,
    _primary_tier,
    _rfc822,
    _short_month_label,
    _tier_counts,
    _tier_max,
    case_category,
    is_orc_code,
)
from web.shape import (
    _bond_by_tier,
    _bond_context,
    _bond_total,
    _card_data_attrs,
    _card_tip,
    _case_numbers,
    _cases_grouped,
    _charge_status_summary,
    _charges_by_chapter,
    _clean_case_number,
    _crimes_of_month,
    _days_in_custody,
    _events_for_recent,
    _feed_description,
    _group_by_month,
    _next_court_date,
    _primary_chapter,
    _primary_charge,
    _recent_booked_inmates,
    _related_inmates,
    _similar_by_statute,
    _strftime_nopad,
    _timeline_markers,
)

log = logging.getLogger("jcstream.site")

ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
PHOTOS_DIR = Path("data/photos")
# Pages serves from /docs at the repo root. Building straight there means the
# workflow can commit the site alongside the data on every sweep.
DEFAULT_OUT = Path("docs")


def _statute_url(code: str, offenses: dict,
                 orc_chapters_set: frozenset[str] | None = None) -> str:
    """codes.ohio.gov link for a charge code, empty for anything that is not a
    genuine ORC section: municipal-code charges (Cincinnati / suburb / mayor's
    courts), HCSO placeholder hold codes (0000.00, etc.), and untitled codes
    whose chapter is not a known ORC chapter. See classify.is_orc_code."""
    if is_orc_code(code, offenses, orc_chapters_set):
        return _codes_ohio_url(code)
    return ""


def _clean_event_note(note: str | None) -> str:
    """Scrub the HCSO epoch-0 sentinel ('1/1/70') out of historical changelog
    notes so the status history never shows a 1970 date."""
    s = note or ""
    for sentinel in ("01/01/1970", "1/1/1970", "01/01/70", "1/1/70"):
        s = s.replace(sentinel, "date not reported")
    return s


def _load_inputs():
    """Load the snapshot + changelog + dispatch feeds. Dedupe the two CFS
    feeds on event_number (qiik-bpks often lags past its pull window and comes
    back empty; gexm-h6bt pulls a wider window), attach dispatch candidates to
    inmates, and build the map points. Returns
    (snapshot, events, cfs_rows, shooting_rows, matches, dispatch_points)."""
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
    seen_ev: set[str] = set()
    all_cfs: list[dict] = []
    for r in (cfs_rows + cfs_pdi_rows):
        ev = str(r.get("event_number") or id(r))
        if ev not in seen_ev:
            seen_ev.add(ev)
            all_cfs.append(r)
    matches = attach_candidates(snapshot.inmates, all_cfs)
    dispatch_points = _dispatch_points(all_cfs, shooting_rows)
    return snapshot, events, cfs_rows, shooting_rows, matches, dispatch_points


def _distinct_chapters(inmates: list[Inmate]) -> list[tuple[str, str]]:
    """Distinct (slug, label) ORC chapters present on the roster, sorted by
    label, for the homepage filter dropdown."""
    chap: dict[str, str] = {}
    for inm in inmates:
        ch = _primary_chapter(inm)
        if ch:
            chap[_chap_slug(ch["label"])] = ch["label"]
    return sorted(chap.items(), key=lambda kv: kv[1])


def _build_env(snapshot: Snapshot, offenses: dict[str, dict],
               base_url: str, site_url: str) -> Environment:
    """Construct the Jinja Environment and register every template global and
    filter. The registered names ARE the template contract: a helper added in
    web/shape.py or web/classify.py must be registered here under the same name
    to be visible to templates."""
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
    env.filters["clean_note"] = _clean_event_note
    env.filters["case_fmt"] = _clean_case_number
    env.globals["cck_name_search"] = cck.name_search_url
    env.globals["cck_case_summary"] = cck.case_summary_url
    env.globals["base_url"] = base_url
    # Absolute origin (scheme + host) for RSS/Atom links, the web manifest and
    # JSON-LD — distinct from base_url, which is a path prefix and is empty when
    # we serve from a custom domain at the root.
    env.globals["site_url"] = site_url
    # Optional Giscus (GitHub-Discussions-backed) comments on inmate pages.
    # Activated only when JCSTREAM_GISCUS_REPO_ID is set as a secret/var; the
    # comment-policy section renders either way.
    env.globals["giscus"] = {
        "repo": os.environ.get("JCSTREAM_GISCUS_REPO", "AICincy/JCStream"),
        "repo_id": os.environ.get("JCSTREAM_GISCUS_REPO_ID", ""),
        "category": os.environ.get("JCSTREAM_GISCUS_CATEGORY", "Announcements"),
        "category_id": os.environ.get("JCSTREAM_GISCUS_CATEGORY_ID", ""),
    }
    # Cache-bust the stylesheet by its CONTENT hash, not the data timestamp —
    # otherwise a CSS change with unchanged data ships new HTML against stale CSS.
    _css = STATIC_DIR / "style.css"
    env.globals["css_version"] = (hashlib.sha256(_css.read_bytes()).hexdigest()[:10]
                                  if _css.exists() else "dev")
    # Same pattern for the externalized JS module. `map.js` was removed; the
    # previous `map_js_version` env.global had no template reference and is
    # gone too.
    _main_js = STATIC_DIR / "main.js"
    env.globals["main_js_version"] = (hashlib.sha256(_main_js.read_bytes()).hexdigest()[:10]
                                      if _main_js.exists() else "dev")
    _register_template_helpers(env, snapshot, offenses)
    return env


def _register_template_helpers(env: Environment, snapshot: Snapshot,
                               offenses: dict[str, dict]) -> None:
    """Register the per-inmate / per-roster helper globals (from web.shape and
    web.classify) that templates call. Split out of _build_env so each stays a
    readable unit; the names here are part of the template contract."""
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
    env.globals["iso_booking_date"] = _iso_booking_date
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
    env.globals["cases_grouped"] = _cases_grouped
    env.globals["case_category"] = case_category
    _explainers = _load_explainers()
    env.globals["orc_explainer"] = lambda code: (
        (_explainers.get(orc_mod.normalize_code(code)) or {}).get("plain") if code else None
    )
    env.globals["orc_base"] = orc_mod.normalize_code
    env.globals["charge_status_summary"] = _charge_status_summary
    env.globals["all_chapters"] = _distinct_chapters(snapshot.inmates)
    env.globals["bond_total"] = _bond_total
    env.globals["days_in_custody"] = _days_in_custody
    env.globals["charges_by_chapter"] = _charges_by_chapter
    env.globals["crimes_of_month"] = _crimes_of_month
    env.globals["inmates_by_id"] = {i.inmate_number: i for i in snapshot.inmates}
    orc_freq = _orc_frequency(snapshot.inmates)
    env.globals["orc_freq"] = lambda code: orc_freq.get(orc_mod.normalize_code(code), 0)
    env.globals["roster_stale"] = _roster_stale_context(snapshot)
    # The satirical Sheriff overlay renders on the blocked notice only when the
    # asset is present, so there is no broken image before it is added.
    env.globals["waf_sheriff_available"] = (STATIC_DIR / "img" / "sheriff-waf.png").exists()
    _orc_chaps = _orc_chapters(offenses)
    env.globals["codes_ohio_url"] = lambda code: _statute_url(code, offenses, _orc_chaps)
    env.globals["chap_slug"] = _chap_slug
    env.globals["related_inmates"] = lambda inm: _related_inmates(inm, snapshot.inmates)
    env.globals["all_inmates_total"] = snapshot.inmate_count


def _prepare_render_data(snapshot: Snapshot, events: list[ChangeEvent]) -> dict:
    """Compute the month grouping, month-nav data, recent-event counts and
    trend that the page renderers consume. Returned as a dict so build() can
    pass the pieces to the individual _render_* calls."""
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
    return {
        "by_month": by_month,
        "nav_months": nav_months,
        "expanded_months": expanded_months,
        "recent_booked": recent_booked,
        "recent_released": recent_released,
        "events_recent": events_recent,
        "trend": trend,
    }


def build(out_dir: Path) -> int:
    snapshot, events, cfs_rows, shooting_rows, matches, dispatch_points = _load_inputs()
    offenses = orc_mod.load_offenses()
    base_url = _resolve_base_url()
    site_url = _resolve_site_url()
    env = _build_env(snapshot, offenses, base_url, site_url)
    _warn_about_unmapped_orcs(snapshot.inmates, offenses)
    rd = _prepare_render_data(snapshot, events)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    idx_ctx = IndexContext(
        snapshot=snapshot,
        by_month=rd["by_month"],
        nav_months=rd["nav_months"],
        expanded_months=rd["expanded_months"],
        events_recent=rd["events_recent"],
        recent_booked=rd["recent_booked"],
        recent_released=rd["recent_released"],
        trend=rd["trend"],
        cfs_rows=cfs_rows,
        shooting_rows=shooting_rows,
        map_points=len(dispatch_points),
    )
    _render_index(env, idx_ctx, out_dir)
    _render_inmates(env, snapshot, matches, events, out_dir)
    _render_feeds(env, events, out_dir)
    _render_data_page(env, snapshot, out_dir)
    _render_stats_page(env, snapshot, rd["by_month"], rd["trend"], out_dir)
    _render_statute_page(env, snapshot, offenses, out_dir)
    _render_court_page(env, snapshot, out_dir)
    _render_visit_page(env, out_dir)
    _render_help_page(env, out_dir)
    _render_courts_page(env, out_dir)
    _copy_static(out_dir)
    _copy_photos(out_dir)
    _write_manifest(out_dir, base_url)
    _write_search_json(out_dir, snapshot)
    _write_dispatches(out_dir, dispatch_points)
    _write_cname(out_dir)
    _write_well_known(out_dir, site_url, snapshot.generated_utc)
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
        lat_raw = row.get("latitude_x")
        lon_raw = row.get("longitude_x")
        if lat_raw is None or lon_raw is None:
            return None
        try:
            la = float(lat_raw)
            lo = float(lon_raw)
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


def _warn_about_unmapped_orcs(inmates: list[Inmate], offenses: dict[str, dict]) -> None:
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



# Page renderers and output writers extracted to web/pages.py and web/outputs.py.
from web.outputs import (  # noqa: E402
    _copy_photos,
    _copy_static,
    _write_checksums,
    _write_cname,
    _write_dispatches,
    _write_manifest,
    _write_search_json,
    _write_well_known,
)
from web.pages import (  # noqa: E402
    IndexContext,
    _render_court_page,
    _render_courts_page,
    _render_data_page,
    _render_feeds,
    _render_help_page,
    _render_index,
    _render_inmates,
    _render_stats_page,
    _render_statute_page,
    _render_visit_page,
)


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
