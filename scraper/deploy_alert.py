"""Active alert when the deployed site lags the committed roster data.

Distinct from ``scraper.freeze_alert``: that fires when ``data/current.json``
itself stops updating (HCSO WAF). This fires the opposite case, the one that
went unnoticed for ~12 hours on 2026-07-04: ``current.json`` keeps updating on
``main`` every sweep, but the GitHub Pages deploy is stuck (the built-in
``pages-build-deployment`` failing with "Deployment failed, try again later"),
so the live site serves stale content while main is fresh.

The check compares the live site's ``/data/current.json`` ``generated_utc``
against the locally committed one. If the live deploy lags main by more than
``DEPLOY_STALE_ALARM_MINUTES`` (about two to three sweep cycles) it emits a
GitHub Actions ``::error`` annotation and opens a deduped GitHub issue.

Send-gate and dedupe mirror ``scraper.freeze_alert``: it dry-runs (logs only)
unless both ``GITHUB_TOKEN`` and ``GITHUB_REPOSITORY`` are set, and it opens at
most one issue while the marker title stays open. A live-fetch or parse failure
is inconclusive, not an alarm, so a transient network blip cannot false-fire.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .freeze_alert import API, _gh
from .sweep import CURRENT_PATH, _prev_generated_utc

log = logging.getLogger("jcstream.sweep")

# Sweep cadence is ~20-45 min, so 90 minutes is roughly two to three cycles.
# The deploy for the current push has not landed when this runs, so the live
# site is always ~1 cycle behind; the threshold sits above that to fire only on
# a genuinely stuck deploy, not the normal one-cycle lag.
DEPLOY_STALE_ALARM_MINUTES = 90
DEFAULT_SITE_URL = "https://www.aretheyinjail.com"
ISSUE_TITLE = "Site deploy is stale: live roster lags main"


def _parse_iso(s: str | None) -> datetime | None:
    """Parse an ISO 8601 ``generated_utc`` (trailing ``Z`` or offset) to an
    aware datetime. Returns None for empty or unparseable input."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def deploy_lag_minutes(local_generated: str | None, live_generated: str | None) -> float | None:
    """Minutes the live deploy lags the committed roster (local minus live).
    Returns None if either timestamp is missing or unparseable (inconclusive)."""
    local_dt = _parse_iso(local_generated)
    live_dt = _parse_iso(live_generated)
    if local_dt is None or live_dt is None:
        return None
    return (local_dt - live_dt).total_seconds() / 60.0


def _fetch_live_generated(site_url: str) -> str | None:
    """Fetch ``generated_utc`` from the live site's ``/data/current.json``.
    Returns None on any network/parse error (treated as inconclusive)."""
    url = site_url.rstrip("/") + "/data/current.json"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "jcstream-deploy-alert"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log.warning("deploy-alert: could not fetch live current.json (%s)", e)
        return None
    gen = data.get("generated_utc") if isinstance(data, dict) else None
    return gen if isinstance(gen, str) and gen else None


def _issue_body(lag_min: float, local_generated: str | None, live_generated: str | None) -> str:
    return (
        f"The live site's roster is **{lag_min:.0f} minutes** behind `main` "
        f"(alarm threshold {DEPLOY_STALE_ALARM_MINUTES} min, about two to three "
        f"sweep cycles).\n\n"
        f"- committed `data/current.json`: `{local_generated}`\n"
        f"- live `/data/current.json`: `{live_generated}`\n\n"
        "`current.json` keeps updating on `main` but the GitHub Pages deploy is "
        "not publishing. This is the stuck-deploy case (branch-serving "
        "`pages-build-deployment` failing GitHub-side), not a roster freeze.\n\n"
        "Next steps (see the deploy runbook in `CLAUDE.md`):\n"
        "1. Re-run the failed `pages build and deployment` run "
        "(`rerun_failed_jobs`); a fresh attempt usually succeeds.\n"
        "2. If retries keep failing, GitHub Pages is degraded for this repo; the "
        "next successful sweep push supersedes the stuck deploy.\n\n"
        "_Opened automatically by `scraper.deploy_alert`. It will not duplicate "
        "while open; close it once the live timestamp catches up._"
    )


def _open_issue_exists(repo: str, token: str) -> bool:
    """True if an open issue with the marker title already exists (search API,
    in-title query so a large open-issue backlog can't hide the marker)."""
    q = urllib.parse.quote(f'repo:{repo} is:issue is:open in:title "{ISSUE_TITLE}"')
    result = _gh("GET", f"{API}/search/issues?q={q}", token)
    items = result.get("items", []) if isinstance(result, dict) else []
    return any(isinstance(i, dict) and i.get("title") == ISSUE_TITLE for i in items)


def alert(local_generated: str | None, live_generated: str | None) -> str:
    """Emit the deploy-staleness alert. Returns the action taken for
    logging/testing: ``"unknown"`` (inconclusive), ``"ok"`` (within threshold),
    ``"dry-run"`` (stale, no token), ``"exists"`` (issue already open), or
    ``"created"``."""
    lag = deploy_lag_minutes(local_generated, live_generated)
    if lag is None:
        log.info(
            "deploy staleness inconclusive (local=%s live=%s)", local_generated, live_generated
        )
        return "unknown"
    if lag <= DEPLOY_STALE_ALARM_MINUTES:
        log.info("deploy freshness OK (site %.0f min behind main)", max(lag, 0.0))
        return "ok"

    # Stuck deploy: surface in the Actions UI regardless of token availability.
    print(
        f"::error title=Deploy stale::live roster is {lag:.0f} min behind main "
        f"(>= {DEPLOY_STALE_ALARM_MINUTES} min). Pages deploy likely stuck; see "
        f"the CLAUDE.md deploy runbook."
    )
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log.warning(
            "deploy stale %.0f min; GITHUB_TOKEN/GITHUB_REPOSITORY unset, not opening an issue (dry-run)",
            lag,
        )
        return "dry-run"
    try:
        if _open_issue_exists(repo, token):
            log.info("deploy stale %.0f min; issue already open, not duplicating", lag)
            return "exists"
        _gh(
            "POST",
            f"{API}/repos/{repo}/issues",
            token,
            {"title": ISSUE_TITLE, "body": _issue_body(lag, local_generated, live_generated)},
        )
        log.error("deploy stale %.0f min; opened a deploy-staleness issue on %s", lag, repo)
        return "created"
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        # Never fail the workflow on an alerting error.
        log.warning("deploy-alert issue API call failed: %s", e)
        return "dry-run"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    site_url = os.environ.get("JCSTREAM_SITE_URL", DEFAULT_SITE_URL)
    alert(_prev_generated_utc(CURRENT_PATH), _fetch_live_generated(site_url))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
