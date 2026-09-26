"""Render the static JCStream site from data/current.json + data/changelog.json.

Output goes to ``docs/`` (``DEFAULT_OUT``). With Pages still on legacy
branch-serve (``build_type=legacy``), the committed ``docs/`` tree is the live
site: sweep and rebuild must build into ``docs/`` and commit it. ``pages.yml``
also uploads ``docs/`` as a verified Actions artifact once the repo source is
flipped to workflow. build() renders into a temp sibling dir and swaps it into
place, so a render failure leaves the last-good output intact.
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

    KPI numerals use nowrap+ellipsis, so full \"$243,200,000\" truncates; the
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
