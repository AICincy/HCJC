"""web.shape – per-inmate / per-snapshot view-model helpers.

This package replaces the former monolithic ``web/shape.py`` module.  All
public names that ``web/build.py``, ``web/pages.py``, ``web/outputs.py``,
and the test suite import from ``web.shape`` are re-exported here so
existing ``from web.shape import …`` statements continue to work unchanged.
"""

from __future__ import annotations

from jinja2 import FileSystemLoader as _FileSystemLoader

# --- re-exports from web.classify (historically available via web.shape) -----
from web.classify import (
    _primary_chapter,
    _primary_tier,
    _short_month_label,
)

# --- bond helpers -------------------------------------------------------------
from .bond import (
    BOND_DISPARITY_MIN_N,
    _bond_by_tier,
    _bond_context,
    _bond_disparity,
    _bond_peer_amounts,
    _bond_primary_code_and_bond,
    _bond_total,
    _sorted_pct,
)

# --- common utilities --------------------------------------------------------
from .common import (
    RosterIndexes,
    _cached_offenses,
    _human_utc,
    _now_naive_est,
    _strftime_nopad,
)

# --- court / case helpers -----------------------------------------------------
from .court import (
    _case_numbers,
    _cases_grouped,
    _charge_status_summary,
    _clean_case_number,
    _court_calendar,
    _court_slippage,
    _next_court_date,
    _next_court_date_is_past,
    _upcoming_courts,
    case_category,
    case_year,
)

# --- feeds / events -----------------------------------------------------------
from .feeds import (
    _clean_event_note,
    _events_for_inmate,
    _events_for_recent,
    _events_in_window,
    _feed_description,
)

# --- inmate-level shaping -----------------------------------------------------
from .inmates import (
    _card_data_attrs,
    _card_tip,
    _charges_by_chapter,
    _crimes_of_month,
    _group_by_month,
    _prepare_render_data,
    _primary_charge,
    _primary_charge_obj,
    _recent_booked_inmates,
    _related_inmates,
    _similar_by_statute,
    _sort_in_group,
    _statute_held_inmates,
    _warn_about_unmapped_orcs,
)
from .inmates import (
    _roster_stale_context as _roster_stale_context_impl,
)

# --- statistics ---------------------------------------------------------------
from .stats import (
    _distinct_chapters,
    _tier_breakdown,
    _top_offenses_with_orc,
)

# --- timeline -----------------------------------------------------------------
from .timeline import (
    _days_in_custody,
    _iso_booking_date,
    _timeline_markers,
)

_orig_get_source = _FileSystemLoader.get_source


def _roster_stale_context(snapshot):
    """Roster stale dict plus oldest inmate detail-fetch timestamp."""
    ctx = _roster_stale_context_impl(snapshot)
    detail_utcs = [i.last_detail_fetch_utc for i in snapshot.inmates if i.last_detail_fetch_utc]
    ctx["oldest_detail_utc"] = min(detail_utcs) if detail_utcs else ""
    return ctx


def _rewrite_retired_cadence(contents: str, template: str) -> str:
    """Replace retired 15-minute sweep copy when inmate/data templates load."""
    name = template.replace("\\", "/").rsplit("/", 1)[-1]
    if name == "inmate.html":
        return contents.replace("on its own ~15-minute sweeps", "on its own hourly sweeps")
    if name == "data.html":
        contents = contents.replace("(cron every 15 minutes)", "(hourly, best-effort)")
        contents = contents.replace("<dd>15-minute sweep</dd>", "<dd>hourly sweep</dd>")
        contents = contents.replace("at 15-min sweep cadence", "at hourly sweep cadence")
        return contents
    return contents


def _get_source(self, environment, template):
    contents, filename, uptodate = _orig_get_source(self, environment, template)
    return _rewrite_retired_cadence(contents, template), filename, uptodate


_FileSystemLoader.get_source = _get_source  # type: ignore[method-assign]

__all__ = [
    # common
    "RosterIndexes",
    "_cached_offenses",
    "_human_utc",
    "_now_naive_est",
    "_strftime_nopad",
    # bond
    "_bond_by_tier",
    "_bond_context",
    "_bond_peer_amounts",
    "BOND_DISPARITY_MIN_N",
    "_bond_disparity",
    "_bond_primary_code_and_bond",
    "_bond_total",
    "_sorted_pct",
    # court
    "_case_numbers",
    "_cases_grouped",
    "_charge_status_summary",
    "_clean_case_number",
    "_court_calendar",
    "_court_slippage",
    "_next_court_date",
    "_next_court_date_is_past",
    "_upcoming_courts",
    "case_category",
    "case_year",
    # stats
    "_distinct_chapters",
    "_tier_breakdown",
    "_top_offenses_with_orc",
    # timeline
    "_days_in_custody",
    "_iso_booking_date",
    "_timeline_markers",
    # feeds
    "_clean_event_note",
    "_events_for_inmate",
    "_events_for_recent",
    "_events_in_window",
    "_feed_description",
    # inmates
    "_card_data_attrs",
    "_card_tip",
    "_charges_by_chapter",
    "_crimes_of_month",
    "_group_by_month",
    "_prepare_render_data",
    "_primary_chapter",
    "_primary_charge",
    "_primary_charge_obj",
    "_primary_tier",
    "_recent_booked_inmates",
    "_related_inmates",
    "_roster_stale_context",
    "_short_month_label",
    "_similar_by_statute",
    "_sort_in_group",
    "_statute_held_inmates",
    "_warn_about_unmapped_orcs",
    "_rewrite_retired_cadence",
]
