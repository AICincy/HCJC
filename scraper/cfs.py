"""Cincinnati Open Data — CPD & CFD Calls For Service (Socrata `qiik-bpks`).

Public, free, no auth, no CAPTCHA. The dataset lags real-time CAD by a few
minutes. We pull only the most recent N hours, filter to dispositions that
indicate an arrest / citation, and persist for the matcher.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .cincy_open import dumps_rows_per_line, prev_row_count, query, since_iso, warn_on_row_drop

log = logging.getLogger(__name__)

DATASET_ID = "qiik-bpks"
ARREST_DISPOSITIONS = ("ARR:%", "CIT:%", "301:%")  # arrest, citation, offense report

CFS_PATH = Path("data/cfs_recent.json")


def pull_recent(hours: int = 168, limit: int = 5000) -> list[dict]:
    # 168h, not 48h - Cincinnati's qiik-bpks dataset lags real-time by a few
    # days, so a 48h window often returns zero rows.
    """Return ARREST/CITATION/OFFENSE rows from the last `hours`."""
    since = since_iso(hours=hours)
    disposition_filter = " OR ".join(
        f"disposition_text like '{d}'" for d in ARREST_DISPOSITIONS
    )
    where = f"create_time_incident > '{since}' AND ({disposition_filter})"
    rows = query(
        DATASET_ID,
        where=where,
        order="create_time_incident DESC",
        limit=limit,
    )
    log.info("CFS pull returned %d rows", len(rows))
    return rows


def save_recent(rows: list[dict], path: Path = CFS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    warn_on_row_drop("CFS", prev_row_count(path), len(rows))
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row_count": len(rows),
        "rows": rows,
    }
    path.write_text(dumps_rows_per_line(payload), encoding="utf-8")


def load_recent(path: Path = CFS_PATH) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("rows", [])


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
    if not args.force and recently_refreshed(CFS_PATH, max_age_hours=1):
        log.info("cfs_recent.json is < 1h old; skipping refresh (use --force to override)")
        return 0
    rows = pull_recent(hours=args.hours)
    save_recent(rows)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
