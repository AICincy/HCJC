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
