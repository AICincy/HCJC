"""Generic loader for additional Cincinnati Open Data safety feeds beyond
the hand-rolled scrapers (cfs.py, cfs_pdi.py, shootings.py).

Each entry in :data:`FEEDS` describes a Socrata dataset to pull on the same
30-min sweep cron, gated to refresh at most once every 24h per feed
(:func:`scraper.cincy_open.recently_refreshed`). The output JSON shape
matches what the dedicated scrapers emit: ``{generated_utc, dataset_id,
row_count, rows}`` so downstream consumers (the build script, RSS readers,
researchers grabbing the public file) treat them uniformly.

Adding a new feed is one line in :data:`FEEDS`; no new module needed.

These feeds are pulled but NOT yet wired into the homepage map or the
templates. They land as files in ``data/`` (and after the build, also in
``docs/data/``) so the public Data page links + downloads them, and any
future site work can read from them without touching the scraper layer.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .cincy_open import query, recently_refreshed, since_iso, warn_on_row_drop

log = logging.getLogger(__name__)

DATA_DIR = Path("data")


@dataclass(frozen=True)
class FeedSpec:
    """One Cincinnati Open Data feed to pull on the sweep."""

    dataset_id: str
    filename: str
    label: str
    days: int = 30
    where_candidates: tuple[str, ...] = ()
    """SoQL `$where` clauses to try in order; first that returns rows wins.
    If empty, no filter is applied (pulls the most recent `limit` rows by
    default Socrata order)."""

    order: str | None = None
    """SoQL `$order` clause; e.g. 'date_reported DESC'."""

    limit: int = 5000

    cache_hours: int = 24
    """How fresh the local file must be to skip a refresh. Tighter for
    feeds that update on the source side more than once a day; relaxed for
    rare-event feeds (officer-involved shootings, CCA complaints) where
    sub-day polling is pure waste."""


# Supplemental feeds chosen for civic-accountability + criminal-justice
# relevance. Excluded: dataset-locator hrefs (police-district boundaries),
# pre-2024 historical archives (NFIRS 2018/2019/2020), filters on datasets
# we already pull (Drug & Heroin 24h report = filtered view of qiik-bpks),
# and frozen datasets with no 2025+ data (PDI OI Shootings r6q4-muts,
# removed May 2026; PDI Crime Incidents k59e-2pvf replaced by Crime STARS).
FEEDS: tuple[FeedSpec, ...] = (
    FeedSpec(
        dataset_id="8us8-wi2w",
        filename="use_of_force_pdi_recent.json",
        label="PDI Use of Force",
        days=365,
        # No filter — pulls most-recent 5000 rows in source order. The
        # dataset is paused per OPD's "transferring to a new data
        # management system" note, so a date filter would zero it out.
        cache_hours=24,  # OPD has paused updates; sub-daily polling is waste
    ),
    FeedSpec(
        dataset_id="748b-sht4",
        filename="use_of_force_incidents_recent.json",
        label="Use of Force - Incidents",
        days=365,
        where_candidates=("eventdate > '{since}'",),
        order="eventdate DESC",
        cache_hours=24,
    ),
    FeedSpec(
        dataset_id="w2kv-5pdg",
        filename="traffic_stops_drivers_recent.json",
        label="Traffic Stops - Contact Cards",
        days=30,
        where_candidates=("interview_date > '{since}'",),
        order="interview_date DESC",
        cache_hours=12,  # source updates daily; 12h catches AM and PM batches
    ),
    FeedSpec(
        dataset_id="swrz-ak2i",
        filename="pedestrian_stops_recent.json",
        label="Pedestrian Stops - Contact Cards",
        days=30,
        where_candidates=("interview_date > '{since}'",),
        order="interview_date DESC",
        cache_hours=12,  # source updates daily; 12h catches AM and PM batches
    ),
    FeedSpec(
        dataset_id="7aqy-xrv9",
        filename="crime_stars_recent.json",
        label="Reported Crime (STARS) after 6/3/2024",
        days=30,
        where_candidates=("datereported > '{since}'",),
        order="datereported DESC",
        cache_hours=12,  # STARS publishes daily; 12h gets same-day after PM update
    ),
    FeedSpec(
        dataset_id="ii65-eyg6",
        filename="cca_complaints_recent.json",
        label="Citizen Complaint Authority — Closed Complaints",
        days=730,  # CCA complaints are infrequent; 2-year window
        where_candidates=("incident_date_time > '{since}'",),
        order="incident_date_time DESC",
        cache_hours=24,  # complaints close on a slow cadence; daily is plenty
    ),
)


def _save(spec: FeedSpec, rows: list[dict]) -> None:
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_id": spec.dataset_id,
        "row_count": len(rows),
        "rows": rows,
    }
    out = DATA_DIR / spec.filename
    out.parent.mkdir(parents=True, exist_ok=True)
    warn_on_row_drop(out, spec.label, len(rows))
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("wrote %s (%d rows)", out, len(rows))


def _pull_one(spec: FeedSpec) -> list[dict]:
    """Pull one feed, falling back through any column-name candidates the
    dataset historically uses. Returns rows; empty on total failure."""
    since = since_iso(hours=spec.days * 24)
    if spec.where_candidates:
        for where_tpl in spec.where_candidates:
            where = where_tpl.format(since=since)
            order = spec.order
            if order is None and where:
                order = where.split()[0] + " DESC"
            try:
                rows = query(spec.dataset_id, where=where, order=order, limit=spec.limit)
                log.info("%s: %d rows (filter=%s)", spec.label, len(rows), where)
                return rows
            except httpx.HTTPStatusError as e:
                log.debug("%s where %r rejected: %s", spec.label, where, e)
        log.warning("%s: all column-name filters rejected; falling back to unfiltered", spec.label)
        try:
            return query(spec.dataset_id, order=spec.order, limit=spec.limit)
        except httpx.HTTPStatusError as e:
            log.warning("%s: unfiltered pull also failed: %s", spec.label, e)
            return []
    # No filter — just pull most recent N rows by configured order.
    try:
        return query(spec.dataset_id, order=spec.order, limit=spec.limit)
    except httpx.HTTPStatusError as e:
        log.warning("%s: pull failed: %s", spec.label, e)
        return []


def pull_all(force: bool = False) -> int:
    """Refresh every feed whose local file exceeds its configured cache window.
    Each FeedSpec carries its own ``cache_hours`` so rare-event feeds
    (officer-involved shootings, CCA complaints) stay on 24h while feeds
    that update sub-daily at the source (crime_stars, traffic / pedestrian
    stops) refresh as often as 12h. Returns count refreshed."""
    refreshed = 0
    for spec in FEEDS:
        path = DATA_DIR / spec.filename
        if not force and recently_refreshed(path, max_age_hours=spec.cache_hours):
            log.info("%s: < %dh old, skipping (path=%s)", spec.label, spec.cache_hours, path)
            continue
        rows = _pull_one(spec)
        _save(spec, rows)
        refreshed += 1
    return refreshed


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Pull the configured Cincinnati Open Data feeds.")
    parser.add_argument("--force", action="store_true",
                        help="Refresh even if a feed's local file is < 24h old.")
    parser.add_argument("--list", action="store_true",
                        help="Print the configured feeds and exit, without pulling.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.list:
        for s in FEEDS:
            print(f"  {s.dataset_id:13s}  {s.filename:42s}  {s.days:4d}d  {s.label}")
        return 0
    n = pull_all(force=args.force)
    log.info("refreshed %d / %d feeds", n, len(FEEDS))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
