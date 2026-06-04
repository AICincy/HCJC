"""Generic Cincinnati Open Data Socrata client.

Cincinnati publishes many crime / public-safety datasets through the same SODA
API. This module is dataset-agnostic; the per-feed pulls (CFS dispatch,
shootings, crime incidents) live in dedicated modules that build on top.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


def prev_row_count(path) -> int | None:
    """The `row_count` recorded in an existing feed file, or None if the file
    is missing/malformed. Lets a save() compare a fresh pull against the prior
    snapshot to flag a sharp collapse vs the normal few-percent rolling-window
    churn."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        rc = json.loads(p.read_text(encoding="utf-8")).get("row_count")
        return rc if isinstance(rc, int) else None
    except (json.JSONDecodeError, OSError, AttributeError):
        return None


def warn_on_row_drop(
    label: str, prev_count: int | None, new_count: int, *, drop_frac: float = 0.5, min_rows: int = 50
) -> None:
    """Log a WARNING when `new_count` falls below `drop_frac` of `prev_count`,
    distinguishing a real feed collapse from the few-percent churn a rolling
    window normally shows.

    Pure comparison: the caller passes the prior count (typically
    `prev_row_count(path)`) so the single file read is explicit at the call
    site and not a hidden side effect of this function. Advisory only: it
    logs, it does not block the write, because for these enrichment feeds a
    silent refuse-to-write would just preserve stale data (the failure mode
    that motivated the guard).

    No-op when `prev_count` is None (no prior snapshot) or below `min_rows`: a
    percentage guard is meaningless on small rare-event feeds (e.g. CCA
    complaints), where a 4 -> 1 swing is noise, not a collapse."""
    if not prev_count or prev_count < min_rows:
        return
    if new_count < prev_count * drop_frac:
        log.warning(
            "%s: row_count dropped sharply %d -> %d (< %.0f%% of prior); possible feed collapse",
            label,
            prev_count,
            new_count,
            drop_frac * 100,
        )


def dumps_rows_per_line(payload: dict) -> str:
    """Serialize a `{generated_utc, ..., rows: [...]}` feed payload as valid
    JSON with each row on its own line, so a sweep diff shows one changed line
    per changed row instead of ~18 (one per field). Envelope scalars stay on
    their own lines; row keys are sorted for diff stability across pulls."""
    rows = payload.get("rows", [])
    head = {k: v for k, v in payload.items() if k != "rows"}
    parts = ["{"]
    for k, v in head.items():
        parts.append(f"  {json.dumps(k)}: {json.dumps(v)},")
    parts.append('  "rows": [')
    for i, row in enumerate(rows):
        tail = "," if i < len(rows) - 1 else ""
        parts.append("    " + json.dumps(row, separators=(",", ":"), sort_keys=True) + tail)
    parts.append("  ]")
    parts.append("}")
    return "\n".join(parts) + "\n"


def utc_floor_isoformat(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def since_iso(hours: int) -> str:
    return utc_floor_isoformat(datetime.now(timezone.utc) - timedelta(hours=hours))


def _default_socrata_client() -> httpx.Client:
    """Build a one-shot Socrata client with the project UA."""
    ua = os.environ.get("JCSTREAM_USER_AGENT", DEFAULT_UA)
    return httpx.Client(timeout=30.0, headers={"User-Agent": ua})


def make_socrata_client() -> httpx.Client:
    """Create a reusable Socrata client for callers that issue multiple queries.

    Use as a context manager so connections are released::

        with make_socrata_client() as client:
            rows_a = query("dataset-a", client=client)
            rows_b = query("dataset-b", client=client)
    """
    return _default_socrata_client()


def query(
    dataset_id: str,
    *,
    where: str | None = None,
    order: str | None = None,
    limit: int = 5000,
    select: str | None = None,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Run a SODA query and return rows as a list of dicts.

    When *client* is provided, it is reused (no new TLS handshake). When
    omitted, a throwaway client is created and closed per call (preserving
    backward compatibility for standalone scripts).
    """
    params: dict[str, str] = {"$limit": str(limit)}
    if where:
        params["$where"] = where
    if order:
        params["$order"] = order
    if select:
        params["$select"] = select
    url = f"{resource_url(dataset_id)}?{urllib.parse.urlencode(params, safe=':')}"
    log.info("Socrata query %s", url)
    if client is not None:
        resp = _execute_with_retry(client, url)
        return resp.json()
    with _default_socrata_client() as c:
        resp = _execute_with_retry(c, url)
        return resp.json()


def _execute_with_retry(client: httpx.Client, url: str) -> httpx.Response:
    """Execute a GET request on Socrata with retries, backoff, and jitter on transient errors (5xx, 429, or RequestError)."""
    import random

    from .client import _retry_after_seconds

    max_retries = 3
    retry_base_delay = 1.0
    retry_jitter_fraction = 0.25

    for attempt in range(max_retries + 1):
        try:
            response = client.get(url)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == max_retries:
                    response.raise_for_status()
                if response.status_code == 429:
                    wait = _retry_after_seconds(response.headers.get("retry-after"))
                else:
                    delay = retry_base_delay * (2 ** attempt)
                    jitter = delay * retry_jitter_fraction * (2 * random.random() - 1)
                    wait = delay + jitter
                log.info(
                    "Socrata query returned status %d on %s; sleeping %.2fs before retry %d/%d",
                    response.status_code,
                    url,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            if attempt == max_retries:
                raise
            delay = retry_base_delay * (2 ** attempt)
            jitter = delay * retry_jitter_fraction * (2 * random.random() - 1)
            wait = delay + jitter
            log.info(
                "Socrata query failed with network error (%s) on %s; sleeping %.2fs before retry %d/%d",
                e,
                url,
                wait,
                attempt + 1,
                max_retries,
            )
            time.sleep(wait)
    raise httpx.HTTPError("Unexpected retry loop exit")
