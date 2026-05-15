"""Cincinnati Open Data — CPD Reported Shootings (Socrata ``sfea-4ksu``).

A confirmed shooting incident is a much higher-signal event than a generic
CFS dispatch. We pull the most recent N days; the matcher links these to
HCSO felony bookings.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .cincy_open import query, since_iso

log = logging.getLogger(__name__)

DATASET_ID = "sfea-4ksu"
LOCAL_PATH = Path("data/shootings_recent.json")


def pull_recent(days: int = 30, limit: int = 5000) -> list[dict]:
    since = since_iso(hours=days * 24)
    # The shootings dataset's date column is ``date_of_occurrence`` (Socrata
    # canonicalizes to lowercase_with_underscores). Fall back gracefully if a
    # column is renamed.
    where_candidates = [
        f"date_of_occurrence > '{since}'",
        f"reported_date > '{since}'",
    ]
    for where in where_candidates:
        try:
            rows = query(DATASET_ID, where=where, order=where.split()[0] + " DESC", limit=limit)
            log.info("shootings pull returned %d rows (filter=%s)", len(rows), where)
            return rows
        except httpx.HTTPStatusError as e:
            # Same scope-narrowing as incidents.pull_recent: only swallow
            # Socrata "bad column" rejections; let transport errors out so
            # the unfiltered fallback isn't masking a real outage.
            log.debug("shootings filter %r rejected by Socrata: %s", where, e)
    log.warning("shootings pull failed all filters; falling back to unfiltered")
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
        log.info("shootings_recent.json is < 24h old; skipping refresh (use --force to override)")
        return 0
    save(pull_recent(days=args.days))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
