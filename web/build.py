"""Render the static JCStream site from data/current.json + data/changelog.json.

Output goes to ``docs/`` (``DEFAULT_OUT``), which GitHub Actions uploads as
the verified GitHub Pages deployment artifact. The sweep can render into a
temporary output while committing only source data. build() renders into a
temp sibling dir and swaps it into place, so a render failure leaves the
last-good output intact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper import cfs as cfs_mod
from scraper import cfs_pdi as cfs_pdi_mod
from scraper import courtclerk as cck
from scraper import orc as orc_mod
from scraper import shootings as shootings_mod
from scraper.match import attach_candidates
from scraper.models import ChangeEvent, Snapshot
from web.classify import (
    _approx_age,
    _avatar_initials,
    _booking_seq,
    _chap_slug,
    _charge_tier,
    _display_date,
    _expand_race,
    _expand_sex,
    _load_explainers,
    _offense_for_code,
    _orc_chapters,
    _orc_frequency,
    _pct_ordinal,
    _primary_degree,
    _primary_tier,
    _rfc822,
    _spark_points,
    _tier_counts,
    _tier_max,
    case_category,
    judge_link,
    statute_url,
)
from web.shape import (
    RosterIndexes,
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
    _clean_event_note,
    _crimes_of_month,
    _days_in_custody,
    _distinct_chapters,
    _feed_description,
    _human_utc,
    _iso_booking_date,
    _next_court_date,
    _next_court_date_is_past,
    _prepare_render_data,
    _primary_chapter,
    _primary_charge,
    _recent_booked_inmates,
    _related_inmates,
    _roster_stale_context,
    _similar_by_statute,
    _strftime_nopad,
    _tier_breakdown,
    _timeline_markers,
    _warn_about_unmapped_orcs,
)

log = logging.getLogger("jcstream.site")

ROOT = Path(__file__).parent
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
PHOTOS_DIR = Path(__file__).resolve().parent.parent / "data" / "photos"
# Pages serves from /docs at the repo root. Building straight there means the
# workflow can commit the site alongside the data on every sweep.
DEFAULT_OUT = Path("docs")

# Non-generated files that must survive the output-directory swap. build()
# renders into a temp dir and replaces the output dir wholesale, so anything
# that is not a build output must be listed here: each entry is copied aside
# before the swap and restored into the fresh tree after it. (Added 2026-09-20
# after the swap silently deleted docs/FRAMEWORK-REVIEW-2026-09-20.md from the
# working tree; CNAME added the same day after the swap silently deleted
# docs/CNAME when JCSTREAM_CNAME was unset in the local environment.)
# Paths are relative to the output directory.
PRESERVED_FILES = ("FRAMEWORK-REVIEW-2026-09-20.md", "CNAME")


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

    takedowns_path = Path("data/takedowns.json")
    takedowns: set[str] = set()
    if takedowns_path.exists():
        # Fail closed like the store write boundary: rendering with an empty
        # seal set would republish sealed records (ORC 2953.32). str() matches
        # the coercion in scraper/store.py so int entries still seal.
        try:
            takedowns = {str(n) for n in json.loads(takedowns_path.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"refusing to build: corrupt takedown seal file {takedowns_path} ({exc}); "
                "a corrupt seal file must not silently build without seals"
            ) from exc

    if takedowns:
        filtered_inmates = [i for i in snapshot.inmates if i.inmate_number not in takedowns]
        snapshot = Snapshot(
            schema_version=snapshot.schema_version,
            generated_utc=snapshot.generated_utc,
            inmate_count=len(filtered_inmates),
            inmates=filtered_inmates,
        )
        events = [e for e in events if e.inmate_number not in takedowns]

    cfs_rows = cfs_mod.load_recent()
    cfs_pdi_rows = cfs_pdi_mod.load()
    shooting_rows = shootings_mod.load()
    seen_ev: set[str] = set()
    all_cfs: list[dict] = []
    for r in cfs_rows + cfs_pdi_rows:
        ev = str(r.get("event_number") or id(r))
        if ev not in seen_ev:
            seen_ev.add(ev)
            all_cfs.append(r)
    matches = attach_candidates(snapshot.inmates, all_cfs)
    dispatch_points = _dispatch_points(all_cfs, shooting_rows)
    return snapshot, events, cfs_rows, shooting_rows, matches, dispatch_points


def _rss_guid(event: ChangeEvent) -> str:
    """Stable hash-based RSS GUID for a ChangeEvent."""
    content = f"{event.event}|{event.inmate_number}|{event.timestamp_utc}"
    # Non-security use: GUIDs need stability and uniqueness, not collision
    # resistance. Changing the algorithm would invalidate every existing
    # subscriber's read state, so the stable SHA1 GUID contract is kept.
    # nosemgrep: insecure-hash-algorithm-sha1
    return hashlib.sha1(content.encode("utf-8")).hexdigest()


def _build_env(snapshot: Snapshot, offenses: dict[str, dict], base_url: str, site_url: str) -> Environment:
    """Construct the Jinja Environment and register every template global and
    filter. The registered names ARE the template contract: a helper added in
    the `web/shape/` package or `web/classify.py` must be registered here under the same name
    to be visible to templates."""
    # autoescape is explicitly enabled for html/xml below; this is not Flask
    # (static site builder), so render_template() does not apply.
    # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
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
    env.filters["rss_guid"] = _rss_guid
    env.globals["cck_name_search"] = cck.name_search_url
    env.globals["cck_case_summary"] = cck.case_summary_url
    env.globals["base_url"] = base_url
    # Absolute origin (scheme + host) for RSS/Atom links, the web manifest and
    # JSON-LD - distinct from base_url, which is a path prefix and is empty when
    # we serve from a custom domain at the root.
    env.globals["site_url"] = site_url
    # Optional Giscus (GitHub-Discussions-backed) comments on inmate pages.
    # Activated only when JCSTREAM_GISCUS_REPO_ID is set as a secret/var; the
    # comment-policy section renders either way.
    env.globals["giscus"] = {
        "repo": os.environ.get("JCSTREAM_GISCUS_REPO", "AICincy/HCJC"),
        "repo_id": os.environ.get("JCSTREAM_GISCUS_REPO_ID", ""),
        "category": os.environ.get("JCSTREAM_GISCUS_CATEGORY", "Announcements"),
        "category_id": os.environ.get("JCSTREAM_GISCUS_CATEGORY_ID", ""),
    }
    # Cache-bust the stylesheet by its CONTENT hash, not the data timestamp -
    # otherwise a CSS change with unchanged data ships new HTML against stale CSS.
    _css = STATIC_DIR / "style.css"
    env.globals["css_version"] = hashlib.sha256(_css.read_bytes()).hexdigest()[:10] if _css.exists() else "dev"
    _fold_css = STATIC_DIR / "fold-chrome.css"
    env.globals["fold_css_version"] = hashlib.sha256(_fold_css.read_bytes()).hexdigest()[:10]
    # Same pattern for the externalized JS module. `map.js` was removed; the
    # previous `map_js_version` env.global had no template reference and is
    # gone too.
    _main_js = STATIC_DIR / "main.js"
    env.globals["main_js_version"] = (
        hashlib.sha256(_main_js.read_bytes()).hexdigest()[:10] if _main_js.exists() else "dev"
    )
    # Same pattern for the pre-paint theme init script (synchronous in <head>).
    _theme_js = STATIC_DIR / "theme-init.js"
    env.globals["theme_js_version"] = (
        hashlib.sha256(_theme_js.read_bytes()).hexdigest()[:10] if _theme_js.exists() else "dev"
    )
    _register_template_helpers(env, snapshot, offenses)
    return env


def _compact_money(n: int | float | None) -> str:
    """Compact currency for KPI cards: 243200000 -> $243.2M, 14500 -> $14.5K.

    KPI numerals use nowrap+ellipsis, so full "$243,200,000" truncates; the
    compact form keeps the figure legible at card width."""
    if n is None:
        return "$0"
    v = float(n)
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"${s}M"
    if v >= 1_000:
        s = f"{v / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"${s}K"
    return f"${v:,.0f}"


def _register_template_helpers(env: Environment, snapshot: Snapshot, offenses: dict[str, dict]) -> None:
    """Register the per-inmate / per-roster helper globals (from web.shape and
    web.classify) that templates call. Split out of _build_env so each stays a
    readable unit; the names here are part of the template contract."""
    env.globals["orc_title"] = lambda code: orc_mod.title_for(code, offenses)
    env.globals["primary_charge"] = _primary_charge
    env.globals["primary_chapter"] = _primary_chapter
    # Tier/degree globals are bound with the offenses dict so every template
    # sees one degree basis: description suffix, then ORC lookup, then venue
    # fallback. The raw functions stay venue-based when called without
    # offenses; templates must never take that path (F-10-02/F-10-03).
    env.globals["primary_tier"] = lambda inm: _primary_tier(inm, offenses)
    env.globals["primary_degree"] = lambda inm: _primary_degree(inm, offenses)
    env.globals["tier_max"] = _tier_max
    env.globals["tier_ladder"] = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    idx = RosterIndexes(snapshot.inmates)
    env.globals["bond_context"] = lambda inm: _bond_context(inm, snapshot.inmates, offenses, indexes=idx)
    env.globals["recent_booked_inmates"] = _recent_booked_inmates(snapshot, n=6)
    # Changelog-derived defaults; build() overwrites them once events load.
    env.globals["recent_booked_ids"] = set()
    env.globals["recent_released_24h"] = []
    env.globals["timeline_markers"] = _timeline_markers
    env.globals["display_date"] = _display_date
    env.globals["human_utc"] = _human_utc
    env.globals["compact_money"] = _compact_money
    env.globals["iso_booking_date"] = _iso_booking_date
    env.globals["similar_by_statute"] = lambda inm: _similar_by_statute(
        inm, snapshot.inmates, offenses, limit=6, indexes=idx
    )
    env.globals["tier_counts"] = lambda inm: _tier_counts(inm, offenses)
    env.globals["charge_tier"] = lambda c: _charge_tier(c, offenses)
    env.globals["charge_chapter"] = _offense_for_code
    env.globals["spark_points"] = _spark_points
    env.globals["roster_tiers"] = _tier_breakdown(snapshot)
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
    env.globals["next_court_date_is_past"] = _next_court_date_is_past
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
    # D1/A5: the footer in base.html renders snapshot.generated_utc, but the
    # static pages (visit, help, courts, bond-schedule) render without a
    # snapshot in context. This global gives their render calls (and the
    # footer fallback) the build timestamp without changing any masthead
    # branches that key on `snapshot is defined`.
    env.globals["generated_utc"] = snapshot.generated_utc
    # The satirical Sheriff overlay renders on the blocked notice only when the
    # asset is present, so there is no broken image before it is added.
    env.globals["waf_sheriff_available"] = (STATIC_DIR / "img" / "sheriff-waf.png").exists()
    _orc_chaps = _orc_chapters(offenses)
    env.globals["codes_ohio_url"] = lambda code: statute_url(code, offenses, _orc_chaps)
    env.globals["chap_slug"] = _chap_slug
    env.globals["related_inmates"] = lambda inm: _related_inmates(inm, snapshot.inmates, indexes=idx)
    env.globals["all_inmates_total"] = snapshot.inmate_count

    env.globals["judge_link"] = judge_link


def _render_build(
    env: Environment,
    snapshot: Snapshot,
    offenses: dict[str, dict],
    matches: dict[str, list[dict]],
    events: list[ChangeEvent],
    rd: dict,
    cfs_rows: list[dict],
    shooting_rows: list[dict],
    dispatch_points: list[dict],
    base_url: str,
    site_url: str,
    build_dir: Path,
) -> None:
    """Render every page and data file into build_dir. Extracted so the
    caller can wrap the whole render phase in temp-dir cleanup (C-9)."""
    idx_ctx = IndexContext(
        snapshot=snapshot,
        by_month=rd["by_month"],
        nav_months=rd["nav_months"],
        expanded_months=rd["expanded_months"],
        recent_booked=rd["recent_booked"],
        recent_released=rd["recent_released"],
        trend=rd["trend"],
        cfs_rows=cfs_rows,
        shooting_rows=shooting_rows,
        map_points=len(dispatch_points),
    )
    _render_index(env, idx_ctx, build_dir)
    _render_archive_page(env, snapshot, rd["by_month"], rd["nav_months"], build_dir)
    _render_public_records_page(env, snapshot, build_dir)
    _render_inmates(env, snapshot, matches, events, build_dir)
    _render_feeds(env, events, build_dir)
    _render_data_page(env, snapshot, build_dir)
    _render_safety_page(env, snapshot, build_dir)
    _render_transparency_page(env, snapshot, build_dir)
    _render_stats_page(env, snapshot, rd["by_month"], rd["trend"], build_dir)
    _render_statute_page(env, snapshot, offenses, build_dir)
    _render_bond_disparity_page(env, snapshot, offenses, build_dir)
    _render_bond_schedule_page(env, build_dir)
    _render_court_page(env, snapshot, build_dir)
    _render_visit_page(env, build_dir)
    _render_help_page(env, build_dir)
    _render_courts_page(env, build_dir)
    _render_judges_page(env, build_dir)
    _render_jury_page(env, build_dir)
    _render_rules_page(env, build_dir)
    _render_forms_page(env, build_dir)
    _render_services_page(env, build_dir)
    _copy_static(build_dir)
    _copy_photos(build_dir)
    _write_manifest(build_dir, base_url)
    _write_search_json(build_dir, snapshot)
    _write_dispatches(build_dir, dispatch_points, snapshot.generated_utc)
    _write_cname(build_dir)
    _write_well_known(build_dir, site_url, snapshot.generated_utc)
    _render_404_page(env, build_dir)
    _write_checksums(build_dir)
    # Tell GitHub Pages NOT to Jekyll-process the built site.
    (build_dir / ".nojekyll").write_text("", encoding="utf-8")


def build(out_dir: Path) -> int:
    from scraper.update_orc_offenses import update_orc_offenses

    update_orc_offenses()

    snapshot, events, cfs_rows, shooting_rows, matches, dispatch_points = _load_inputs()
    offenses = orc_mod.load_offenses()
    base_url = _resolve_base_url()
    site_url = _resolve_site_url()
    env = _build_env(snapshot, offenses, base_url, site_url)
    _warn_about_unmapped_orcs(snapshot.inmates, offenses)
    rd = _prepare_render_data(snapshot, events)
    # Registered here rather than in _register_template_helpers because they
    # derive from the changelog events, which _build_env never sees.
    env.globals["recent_booked_ids"] = rd["recent_booked_ids"]
    env.globals["recent_released_24h"] = rd["recent_released_24h"]

    # Render into a temp sibling dir, then swap it into place. A render
    # exception then leaves the last-good out_dir intact instead of blanking
    # the site: out_dir is only wiped after a full, successful build.
    build_dir = out_dir.parent / f".{out_dir.name}.build-tmp"
    old_dir = out_dir.parent / f".{out_dir.name}.build-old"
    for d in (build_dir, old_dir):
        if d.exists():
            shutil.rmtree(d)
    build_dir.mkdir(parents=True)

    # C-9: clean up the temp build dir if rendering fails, so a failed build
    # leaves no `.docs.build-tmp` litter beside the last-good tree. (The swap
    # below only runs after a full successful render, so out_dir is untouched
    # either way.)
    try:
        _render_build(env, snapshot, offenses, matches, events, rd, cfs_rows, shooting_rows,
                      dispatch_points, base_url, site_url, build_dir)
    except BaseException:
        shutil.rmtree(build_dir, ignore_errors=True)
        raise

    # Set aside non-generated files so they survive the wholesale swap below.
    # Entries in PRESERVED_FILES are copied out of the old tree now and written
    # back into the fresh tree after the promote.
    preserved: dict[str, bytes] = {}
    if out_dir.exists():
        for rel in PRESERVED_FILES:
            src = out_dir / rel
            if src.is_file():
                preserved[rel] = src.read_bytes()
            else:
                log.warning("preserved file %s not found under %s; skipping", rel, out_dir)

    # Promote the freshly built site with a rename-based swap. Everything above
    # wrote only to build_dir, so a mid-render failure never touched out_dir.
    # If the promote itself fails after out_dir was moved aside, restore the
    # last-good site so out_dir is never left missing (a blank live site).
    if out_dir.exists():
        out_dir.replace(old_dir)
    try:
        build_dir.replace(out_dir)
    except OSError:
        if old_dir.exists() and not out_dir.exists():
            old_dir.replace(out_dir)
        raise
    if old_dir.exists():
        shutil.rmtree(old_dir)

    # Restore the non-generated files set aside above into the fresh tree.
    for rel, data in preserved.items():
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    if preserved:
        log.info(
            "preserved %d non-generated file(s): %s",
            len(preserved),
            ", ".join(sorted(preserved)),
        )

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
    4. Fallback: ``https://www.aretheyinjail.com`` (the live custom domain)
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
    return "https://www.aretheyinjail.com"


# Dispatch geocoding extracted to web/dispatch.py.
from web.dispatch import _dispatch_points  # noqa: E402

# Page renderers and output writers extracted to web/pages.py and web/outputs.py.
# History tracking extracted to web/history.py.
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
    _render_404_page,
    _render_archive_page,
    _render_bond_disparity_page,
    _render_bond_schedule_page,
    _render_court_page,
    _render_courts_page,
    _render_data_page,
    _render_feeds,
    _render_forms_page,
    _render_help_page,
    _render_index,
    _render_inmates,
    _render_judges_page,
    _render_jury_page,
    _render_public_records_page,
    _render_rules_page,
    _render_safety_page,
    _render_services_page,
    _render_stats_page,
    _render_statute_page,
    _render_transparency_page,
    _render_visit_page,
)


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
