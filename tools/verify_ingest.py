"""Confirm JCStream sweep telemetry is reaching Datadog.

Run locally once after the first sweep that ran with DD_API_KEY set in CI:

    DD_API_KEY=<key> DD_APP_KEY=<key> python tools/verify_ingest.py

DD_API_KEY writes to intake and is already in CI. DD_APP_KEY reads via the API
and is needed only for this script (create a read-only application key, keep it
local, do not add it to CI). DD_SITE defaults to datadoghq.com to match
scraper/ddlog.py; set it (e.g. us5.datadoghq.com) if the sweep ships elsewhere.

Exit codes: 0 = events found in the last hour, 1 = none found, 2 = misconfig.
"""
from __future__ import annotations

import os
import sys

import httpx


def _event_name(entry: dict) -> str | None:
    attrs = entry.get("attributes", {}) or {}
    inner = attrs.get("attributes", {}) or {}
    return inner.get("event", attrs.get("event"))


def _search(api_key: str, app_key: str, site: str) -> list | None:
    """Return the matching log events, or None on transport error."""
    body = {
        "filter": {"query": "service:jcstream", "from": "now-1h", "to": "now"},
        "sort": "-timestamp",
        "page": {"limit": 100},
    }
    headers = {
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.post(
            f"https://api.{site}/api/v2/logs/events/search",
            json=body, headers=headers, timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("data") or []
    except (httpx.HTTPError, ValueError) as exc:
        print(f"Search failed: {exc!r}", file=sys.stderr)
        return None


def _report(events: list) -> None:
    print(f"OK. Found {len(events)} JCStream events in the last hour.")
    print("Most recent:")
    for e in events[:5]:
        ts = (e.get("attributes", {}) or {}).get("timestamp", "?")
        print(f"  - {ts}  event={_event_name(e) or '?'}")

    missing = {"sweep_start", "sweep_complete"} - {_event_name(e) for e in events}
    if missing:
        print(f"WARNING: missing expected events in the last hour: {sorted(missing)}")


def main() -> int:
    api_key = os.environ.get("DD_API_KEY")
    app_key = os.environ.get("DD_APP_KEY")
    site = os.environ.get("DD_SITE", "datadoghq.com")

    if not (api_key and app_key):
        print("Need DD_API_KEY and DD_APP_KEY in env.", file=sys.stderr)
        return 2

    events = _search(api_key, app_key, site)
    if events is None:
        return 1
    if not events:
        print("No JCStream logs in the last hour. Ingest is not yet flowing.")
        print("Checklist:")
        print("  1. DD_API_KEY is set in the GitHub Actions sweep job env.")
        print("  2. A sweep has run since the secret was added.")
        print("  3. scraper/ddlog.py emit() is reached on this run's code path.")
        return 1

    _report(events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
