"""Active alert when the deployed site lags the committed roster data.

Distinct from ``scraper.freeze_alert``: that fires when ``data/current.json``
itself stops updating (HCSO WAF, or a stalled sweep cron). This fires the
opposite case, the one that went unnoticed for ~12 hours on 2026-07-04:
``current.json`` keeps updating on ``main`` every sweep, but the GitHub Pages
deploy is stuck (the built-in ``pages-build-deployment`` failing with
"Deployment failed, try again later"), so the live site serves stale content
while main is fresh.

What is measured
----------------
The alarm metric is how long ``main`` has held roster data the live site does
not serve (:func:`deploy_pending_minutes`): if the live ``generated_utc`` is
older than the committed one, the deploy has been pending since the committed
snapshot was generated. It fires past ``DEPLOY_PENDING_ALARM_MINUTES``.

It deliberately does NOT alarm on the raw timestamp gap (committed minus live,
:func:`deploy_lag_minutes`). That gap equals the interval between the last two
sweeps whenever the newest push has not deployed yet, and Actions cron drifts
3.5-5.5h in practice before the current twice-hourly :07/:37 schedule, so a
gap-based alarm fired on essentially every sweep (issue #506: "258 minutes
behind" at 03:54:18Z; Pages finished the deploy 27s later). The gap is still
reported in the issue body for context.

Where it runs
-------------
``.github/workflows/staleness-watchdog.yml``, on its own schedule, via
``scraper.staleness_watchdog``. It used to run as the last step of
``sweep.yml``, which shared a failure domain with the thing it watches: when the
sweep cron stalled, the alarm stalled with it. Run inside a sweep it could not
work anyway -- its own push has not deployed yet.

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

# A healthy branch-serve Pages build finishes in under a minute after the push,
# and the Pages CDN may cache /data/current.json for up to ~10 minutes. Thirty
# minutes clears both with room for one automatic retry, while still catching a
# stuck deploy within one watchdog cycle.
DEPLOY_PENDING_ALARM_MINUTES = 30
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


def deploy_pending_minutes(
    local_generated: str | None,
    live_generated: str | None,
    now: datetime | None = None,
) -> float | None:
    """Minutes ``main`` has held roster data the live site does not serve.

    ``0.0`` when the live site is caught up (or ahead). Otherwise the time since
    the committed snapshot was generated, which is when its deploy became due.
    Returns None if either timestamp is missing or unparseable (inconclusive).
    """
    lag = deploy_lag_minutes(local_generated, live_generated)
    if lag is None:
        return None
    if lag <= 0:
        return 0.0
    local_dt = _parse_iso(local_generated)
    assert local_dt is not None  # guaranteed by deploy_lag_minutes above
    current = now if now is not None else datetime.now(timezone.utc)
    return max((current - local_dt).total_seconds() / 60.0, 0.0)


def _fetch_live_generated(site_url: str) -> str | None:
    """Fetch ``generated_utc`` from the live site's ``/data/current.json``.
    Returns None on any network/parse error (treated as inconclusive)."""
    url = site_url.rstrip("/") + "/data/current.json"
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        log.warning("deploy-alert: refusing to fetch non-http(s) site URL")
        return None
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "jcstream-deploy-alert"})
        # Reviewed: the http/https scheme allowlist above rejects file://
        # and other non-http(s) schemes, which is the arbitrary-file-read
        # vector this audit rule guards against. site_url is
        # env-or-constant controlled (JCSTREAM_SITE_URL / DEFAULT_SITE_URL).
        # nosemgrep: dynamic-urllib-use-detected
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        log.warning("deploy-alert: could not fetch live current.json (%s)", e)
        return None
    gen = data.get("generated_utc") if isinstance(data, dict) else None
    return gen if isinstance(gen, str) and gen else None


def _issue_body(pending_min: float, lag_min: float, local_generated: str | None, live_generated: str | None) -> str:
    return (
        f"`main` has held roster data the live site does not serve for "
        f"**{pending_min:.0f} minutes** (alarm threshold "
        f"{DEPLOY_PENDING_ALARM_MINUTES} min; a healthy Pages deploy lands in "
        f"about a minute).\n\n"
        f"- committed `data/current.json`: `{local_generated}`\n"
        f"- live `/data/current.json`: `{live_generated}` "
        f"({lag_min:.0f} min older)\n\n"
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


def alert(
    local_generated: str | None,
    live_generated: str | None,
    now: datetime | None = None,
) -> str:
    """Emit the deploy-staleness alert. Returns the action taken for
    logging/testing: ``"unknown"`` (inconclusive), ``"ok"`` (within threshold),
    ``"dry-run"`` (stale, no token), ``"exists"`` (issue already open), or
    ``"created"``."""
    pending = deploy_pending_minutes(local_generated, live_generated, now)
    lag = deploy_lag_minutes(local_generated, live_generated)
    if pending is None or lag is None:
        log.info("deploy staleness inconclusive (local=%s live=%s)", local_generated, live_generated)
        return "unknown"
    if pending <= DEPLOY_PENDING_ALARM_MINUTES:
        log.info(
            "deploy freshness OK (newest committed roster pending deploy for %.0f min; site %.0f min older)",
            pending,
            max(lag, 0.0),
        )
        return "ok"

    # Stuck deploy: surface in the Actions UI regardless of token availability.
    print(
        f"::error title=Deploy stale::main has held undeployed roster data for "
        f"{pending:.0f} min (> {DEPLOY_PENDING_ALARM_MINUTES} min; live is "
        f"{lag:.0f} min older). Pages deploy likely stuck; see the CLAUDE.md "
        f"deploy runbook."
    )
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log.warning(
            "deploy stale %.0f min; GITHUB_TOKEN/GITHUB_REPOSITORY unset, not opening an issue (dry-run)",
            pending,
        )
        return "dry-run"
    try:
        if _open_issue_exists(repo, token):
            log.info("deploy stale %.0f min; issue already open, not duplicating", pending)
            return "exists"
        _gh(
            "POST",
            f"{API}/repos/{repo}/issues",
            token,
            {"title": ISSUE_TITLE, "body": _issue_body(pending, lag, local_generated, live_generated)},
        )
        log.error("deploy stale %.0f min; opened a deploy-staleness issue on %s", pending, repo)
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
