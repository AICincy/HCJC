"""Generic Cincinnati Open Data Socrata client.

Cincinnati publishes many crime / public-safety datasets through the same SODA
API. This module is dataset-agnostic; the per-feed pulls (CFS dispatch,
shootings, crime incidents) live in dedicated modules that build on top.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from .client import DEFAULT_UA

log = logging.getLogger(__name__)

DOMAIN = "https://data.cincinnati-oh.gov"


def resource_url(dataset_id: str) -> str:
    return f"{DOMAIN}/resource/{dataset_id}.json"


def recently_refreshed(path, max_age_hours: float = 24) -> bool:
    """True if `path` was generated < `max_age_hours` ago (per its
    `generated_utc` JSON field), so callers can skip a redundant API pull
    when the existing data is still fresh. False if the file is missing,
    malformed, or older. Used by the open-data scrapers' main() to gate
    once-per-day refresh on top of the 30-min sweep cron."""
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return False
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
        ts = meta.get("generated_utc", "")
        if not ts:
            return False
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        last = datetime.fromisoformat(ts)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return age_h < max_age_hours
    except (json.JSONDecodeError, ValueError, OSError):
        return False


def utc_floor_isoformat(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def since_iso(hours: int) -> str:
    return utc_floor_isoformat(datetime.now(timezone.utc) - timedelta(hours=hours))


def query(
    dataset_id: str,
    *,
    where: str | None = None,
    order: str | None = None,
    limit: int = 5000,
    select: str | None = None,
) -> list[dict]:
    """Run a SODA query and return rows as a list of dicts."""
    params: dict[str, str] = {"$limit": str(limit)}
    if where:
        params["$where"] = where
    if order:
        params["$order"] = order
    if select:
        params["$select"] = select
    url = f"{resource_url(dataset_id)}?{urllib.parse.urlencode(params, safe=':')}"
    # Fall back to the full module DEFAULT_UA (with contact URL) when the
    # workflow doesn't override JCSTREAM_USER_AGENT, so the bare "JCStream/0.1"
    # never reaches Socrata. Politeness is the only social control here.
    ua = os.environ.get("JCSTREAM_USER_AGENT", DEFAULT_UA)
    log.info("Socrata query %s", url)
    with httpx.Client(timeout=30.0, headers={"User-Agent": ua}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()
