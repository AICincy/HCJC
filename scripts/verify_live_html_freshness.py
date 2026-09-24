"""Probe live HTML pages and fail when the deployed site is stale.

Every rendered page carries a machine-readable roster vintage stamp:

    <meta name="jcstream:generated-utc" content="2026-09-23T19:35:00Z">

(the same ``snapshot.generated_utc`` the footer renders in human form). This
gate fetches the live pages, extracts the stamp, and compares it with the
data vintage at the current tip (``data/current.json`` -> ``generated_utc``)
and with a freshly built candidate tree (``docs/``).

A live stamp older than the tip's vintage by more than ``--max-lag-hours``
is the signature of a silently broken deploy. The sweep pipeline rebuilds and
republishes the HTML tree on an hourly cadence with observed cron gaps of a
few hours, so a healthy deploy lags the tip by at most hours; 26 hours
absorbs the worst observed gap plus deploy lag while still catching a dead
pipeline inside the weekly ``live-url-parity`` cycle. This is the incident
class of issue #496, where every pages-build-deployment "succeeded" while the
live tree kept serving a frozen skeleton.

Unlike the JSON URL probe, there is no recovery mode here: this workflow
deploys nothing that could restore a broken tree, so its red run IS the
alert and every failure is fail-closed.

Failure modes (all exit 1):
- live page unreachable, non-200, or served as non-HTML;
- live page missing the stamp (a tree deployed before the marker rollout,
  i.e. stale by definition once the stamp has shipped);
- candidate page missing the stamp (a build/template regression);
- candidate vintage != tip vintage (the build rendered stale or foreign data);
- live vintage lagging the tip vintage past ``--max-lag-hours``;
- a live stamp that does not match the strict stamp shape (tampering).

A live stamp NEWER than the tip vintage is only a warning: it means the
checkout lagged a deploy, not that the live site is wrong.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# The build emits exactly one stamp per page with a fixed attribute order
# (web/templates/base.html); the match is tolerant of attribute reshuffles on
# the same tag so a benign template edit cannot split-brain the gate.
MARKER_RE = re.compile(
    r"<meta[^>]*name=[\"']jcstream:generated-utc[\"'][^>]*content=[\"']([^\"']*)[\"']"
)
_UTC_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "HCJC-live-parity/1.0", "Accept": "text/html"})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def extract_vintage(html: str) -> str | None:
    """Return the stamped vintage, or None when the page carries no stamp.

    An empty content attribute counts as absent: the bootstrap build (no
    data file yet) has no meaningful vintage to stamp.
    """
    match = MARKER_RE.search(html)
    if match is None:
        return None
    return match.group(1) or None


def parse_stamp(stamp: str) -> datetime:
    """Parse the strict YYYY-MM-DDTHH:MM:SSZ shape the data model enforces."""
    if not _UTC_STAMP_RE.match(stamp):
        raise ValueError(f"not a YYYY-MM-DDTHH:MM:SSZ stamp: {stamp!r}")
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def load_tip_vintage(data_path: Path) -> str:
    """Read the tip's roster vintage from data/current.json."""
    snapshot = json.loads(data_path.read_text(encoding="utf-8"))
    stamp = snapshot["generated_utc"]
    if not isinstance(stamp, str):
        raise ValueError(f"generated_utc must be a string, got {type(stamp).__name__}")
    parse_stamp(stamp)
    return stamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that live HTML reflects a fresh deploy.")
    parser.add_argument("--site", default="https://www.aretheyinjail.com")
    parser.add_argument("--local", type=Path, default=Path("docs"))
    parser.add_argument("--data", type=Path, default=Path("data/current.json"))
    parser.add_argument(
        "--page",
        action="append",
        help="HTML path below the site root to probe (repeatable; default index.html)",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--max-lag-hours",
        type=float,
        default=26.0,
        help="Fail when the live vintage lags the tip vintage by more than this many hours",
    )
    args = parser.parse_args()

    pages = args.page or ["index.html"]
    errors: list[str] = []
    warnings: list[str] = []

    try:
        repo_stamp = load_tip_vintage(args.data)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"::error title=Live HTML freshness::cannot read tip vintage from {args.data}: {exc}")
        print(f"ERROR: cannot read tip vintage from {args.data}: {exc}")
        return 1
    repo_dt = parse_stamp(repo_stamp)

    for page in pages:
        label = f"/{page}"
        candidate_path = args.local / page
        try:
            candidate_html = candidate_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{label}: candidate build unreadable ({candidate_path}): {exc}")
            continue
        candidate_stamp = extract_vintage(candidate_html)
        if candidate_stamp is None:
            errors.append(
                f"{label}: candidate {candidate_path} carries no jcstream:generated-utc stamp; "
                "the build/template no longer stamps pages"
            )
            continue
        if candidate_stamp != repo_stamp:
            errors.append(
                f"{label}: candidate vintage {candidate_stamp} != tip vintage {repo_stamp} "
                "(build ran on stale or foreign data)"
            )
            continue

        url = args.site.rstrip("/") + "/" + page
        try:
            status, content_type, body = fetch(url, args.timeout)
        except HTTPError as exc:
            errors.append(f"{label}: HTTP {exc.code} from {url}")
            continue
        except (URLError, TimeoutError) as exc:
            errors.append(f"{label}: live probe failed: {exc}")
            continue
        if status < 200 or status >= 300:
            errors.append(f"{label}: unexpected HTTP status {status}")
            continue
        if "html" not in content_type.lower():
            errors.append(f"{label}: unexpected content type {content_type!r}")
            continue
        live_stamp = extract_vintage(body.decode("utf-8", errors="replace"))
        if live_stamp is None:
            errors.append(
                f"{label}: live HTML carries no jcstream:generated-utc stamp; the deployed tree "
                "predates the stamp rollout (a deploy newer than the stamp is required)"
            )
            continue
        try:
            live_dt = parse_stamp(live_stamp)
        except ValueError as exc:
            errors.append(f"{label}: live vintage malformed: {exc}")
            continue

        lag_hours = (repo_dt - live_dt).total_seconds() / 3600.0
        if lag_hours > args.max_lag_hours:
            errors.append(
                f"{label}: live HTML is stale: vintage {live_stamp} lags tip vintage {repo_stamp} "
                f"by {lag_hours:.1f} h (max {args.max_lag_hours:g} h); the Pages deploy looks broken"
            )
        elif lag_hours < 0:
            warnings.append(
                f"{label}: live vintage {live_stamp} is newer than the tip vintage {repo_stamp} "
                "(checkout lagged the last deploy)"
            )
        else:
            print(f"  {label}: fresh (live {live_stamp}, tip {repo_stamp}, lag {lag_hours:.2f} h)")

    for warning in warnings:
        print(f"::warning title=Live HTML freshness::{warning}")
    if errors:
        for error in errors:
            print(f"::error title=Live HTML freshness::{error}")
        print(f"live HTML freshness failed: {len(errors)} error(s) across {len(pages)} page(s)")
        return 1
    print(
        f"live HTML freshness OK: {len(pages)} page(s) within {args.max_lag_hours:g} h "
        f"of the tip vintage {repo_stamp}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
