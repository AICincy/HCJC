"""Cincinnati Open Data — PDI Police Calls For Service / CAD (Socrata ``gexm-h6bt``).

This is the national Police Data Initiative-standard CFS feed (CPD only), with
6.5M+ historical rows going back several years. The local feed (qiik-bpks)
covers both CPD and CFD and a rolling 30-day window; gexm-h6bt is the better
choice when you want historical context (prior contacts, neighborhood patterns,
event-number reconciliation across years).

JCStream uses this as an enrichment-only source for now; it is not folded into
the recent-events sections on the home page.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .cincy_open import (
    dumps_rows_per_line,
    prev_row_count,
    query,
    since_iso,
    warn_on_row_drop,
)

log = logging.getLogger(__name__)

DATASET_ID = "gexm-h6bt"
LOCAL_PATH = Path("data/cfs_pdi_recent.json")

ARREST_DISPOSITIONS = ("ARR:%", "CIT:%", "301:%")


def pull_recent(hours: int = 168, limit: int = 10000) -> list[dict]:
    """Default window is 7 days; gexm-h6bt has the history to support longer."""
    since = since_iso(hours=hours)
    disp_filter = " OR ".join(f"disposition_text like '{d}'" for d in ARREST_DISPOSITIONS)
    where = f"create_time_incident > '{since}' AND ({disp_filter})"
    rows = query(
        DATASET_ID,
        where=where,
        order="create_time_incident DESC",
        limit=limit,
    )
    log.info("PDI CFS pull returned %d rows", len(rows))
    return rows


def save(rows: list[dict], path: Path = LOCAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    warn_on_row_drop("PDI CFS", prev_row_count(path), len(rows))
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_id": DATASET_ID,
        "row_count": len(rows),
        "rows": rows,
    }
    path.write_text(dumps_rows_per_line(payload), encoding="utf-8")


def load(path: Path = LOCAL_PATH) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("rows", [])


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=720)  # 30 days
    parser.add_argument("--force", action="store_true",
                        help="Refresh even if the local file is < 1h old.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from .cincy_open import recently_refreshed
    if not args.force and recently_refreshed(LOCAL_PATH, max_age_hours=1):
        log.info("cfs_pdi_recent.json is < 1h old; skipping refresh (use --force to override)")
        return 0
    save(pull_recent(hours=args.hours))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
