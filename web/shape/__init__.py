"""web.shape – per-inmate / per-snapshot view-model helpers.

This package replaces the former monolithic ``web/shape.py`` module.  All
public names that ``web/build.py``, ``web/pages.py``, ``web/outputs.py``,
and the test suite import from ``web.shape`` are re-exported here so
existing ``from web.shape import …`` statements continue to work unchanged.
"""

from __future__ import annotations

# --- re-exports from web.classify (historically available via web.shape) -----
from web.classify import (
    _primary_chapter,
    _primary_tier,
    _short_month_label,
)

# --- bond helpers -------------------------------------------------------------
from .bond import (
    _bond_by_tier,
    _bond_context,
    _bond_peer_amounts,
    _bond_primary_code_and_bond,
    _bond_total,
    _sorted_pct,
)

# --- common utilities --------------------------------------------------------
from .common import (
    RosterIndexes,
    _cached_offenses,
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
    _next_court_date,
    _upcoming_courts,
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
    _roster_stale_context,
    _similar_by_statute,
    _sort_in_group,
    _statute_held_inmates,
    _warn_about_unmapped_orcs,
)

# --- statistics ---------------------------------------------------------------
from .stats import (
    _all_top_offenses,
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

__all__ = [
    # common
    "RosterIndexes",
    "_cached_offenses",
    "_now_naive_est",
    "_strftime_nopad",
    # bond
    "_bond_by_tier",
    "_bond_context",
    "_bond_peer_amounts",
    "_bond_primary_code_and_bond",
    "_bond_total",
    "_sorted_pct",
    # court
    "_case_numbers",
    "_cases_grouped",
    "_charge_status_summary",
    "_clean_case_number",
    "_court_calendar",
    "_next_court_date",
    "_upcoming_courts",
    # stats
    "_all_top_offenses",
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
]
