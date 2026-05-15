"""Cincinnati Open Data — PDI Crime Incidents (Socrata ``k59e-2pvf``).

This is the canonical reported-crime dataset: an officer has filed a report
(versus the CFS feed, which is just a dispatch event). PDI Crime Incidents
include UCR offense codes, occurred-on date, neighborhood, lat/lon. Matching
these to bookings is higher-confidence than CFS dispatches because the
disposition is on the record itself.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .cincy_open import query, since_iso

log = logging.getLogger(__name__)

DATASET_ID = "k59e-2pvf"
LOCAL_PATH = Path("data/incidents_recent.json")


def pull_recent(days: int = 30, limit: int = 5000) -> list[dict]:
    since = since_iso(hours=days * 24)
    # PDI Crime Incidents uses ``date_reported`` as the canonical timestamp.
    where_candidates = [
        f"date_reported > '{since}'",
        f"date_from > '{since}'",
    ]
    for where in where_candidates:
        try:
            rows = query(DATASET_ID, where=where, order=where.split()[0] + " DESC", limit=limit)
            log.info("incidents pull returned %d rows (filter=%s)", len(rows), where)
            return rows
        except httpx.HTTPStatusError as e:
            # Socrata's "bad column" rejection surfaces as 400 here; that's
            # the only thing the filter-candidate loop should be tolerant of.
            # Transport errors propagate so the operator sees them instead of
            # being silently rolled into a fallback bigger than the intended
            # filtered pull.
            log.debug("incidents filter %r rejected by Socrata: %s", where, e)
    log.warning("incidents pull failed all filters; falling back to unfiltered")
    return query(DATASET_ID, limit=limit)


def save(rows: list[dict], path: Path = LOCAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_id": DATASET_ID,
        "row_count": len(rows),
        "rows": rows,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load(path: Path = LOCAL_PATH) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("rows", [])


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--force", action="store_true",
                        help="Refresh even if the local file is < 24h old.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from .cincy_open import recently_refreshed
    if not args.force and recently_refreshed(LOCAL_PATH, max_age_hours=24):
        log.info("incidents_recent.json is < 24h old; skipping refresh (use --force to override)")
        return 0
    save(pull_recent(days=args.days))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
