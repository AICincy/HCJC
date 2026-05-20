"""Active alert when the inmate roster has been frozen past the alarm window.

The degraded-roster guard in ``scraper.sweep`` correctly keeps the last-good
``data/current.json`` and exits 0 when HCSO's WAF blocks the runner, so a
multi-hour freeze never fails the workflow. This module turns that silent hold
into an active notification: run after the sweep step, it emits a GitHub
Actions ``::error`` annotation and opens a GitHub issue so subscribers are
notified.

Send-gate (mirrors the PRA loop): it dry-runs (logs only) unless both
``GITHUB_TOKEN`` and ``GITHUB_REPOSITORY`` are set. Dedupe: if an open issue
with the marker title already exists it does nothing, so a cron firing every
~15 minutes during a long freeze does not spam new issues or comments.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from .sweep import CURRENT_PATH, _prev_generated_utc
from .sweep_guards import ROSTER_STALE_ALARM_HOURS, roster_stale_hours

log = logging.getLogger("jcstream.sweep")

API = "https://api.github.com"
ISSUE_TITLE = "Roster frozen: HCSO sweep is not updating current.json"


def _gh(method: str, url: str, token: str, payload: dict | None = None) -> list | dict:
    """Minimal GitHub REST call using stdlib urllib (no extra dependency)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _open_freeze_issue_exists(repo: str, token: str) -> bool:
    """True if an open issue with the marker title already exists."""
    issues = _gh("GET", f"{API}/repos/{repo}/issues?state=open&per_page=100", token)
    return any(isinstance(i, dict) and i.get("title") == ISSUE_TITLE for i in issues)


def _issue_body(stale_h: float) -> str:
    return (
        f"The HCSO inmate roster has not updated for **{stale_h:.1f} hours** "
        f"(alarm threshold {ROSTER_STALE_ALARM_HOURS:.0f}h).\n\n"
        "The degraded-roster guard is keeping the last-good `data/current.json` "
        "and the sweep exits 0, so the site is stable but stale. This is almost "
        "always HCSO's WAF blocking the GitHub Actions runner IP.\n\n"
        "Next steps (see the runbook in `CLAUDE.md`):\n"
        "1. Check the latest `sweep` run log for `list sweep looks degraded` and "
        "the `N/M surname fetches failed` ratio.\n"
        "2. If it is a hard WAF block, set the `JCSTREAM_HTTP_PROXY` secret to a "
        "different egress, or wait for the block to rotate (24-72h).\n\n"
        "_This issue was opened automatically by `scraper.freeze_alert`. It will "
        "not be reopened while it stays open; close it once the roster recovers._"
    )


def alert(stale_h: float | None) -> str:
    """Emit the freeze alert. Returns the action taken for logging/testing:
    ``"ok"`` (not frozen), ``"dry-run"`` (frozen, no token), ``"exists"``
    (issue already open), or ``"created"``."""
    if stale_h is None or stale_h < ROSTER_STALE_ALARM_HOURS:
        log.info("roster freshness OK (%s)",
                 "unknown" if stale_h is None else f"{stale_h:.1f}h")
        return "ok"

    # Frozen: surface in the Actions UI regardless of token availability.
    print(
        f"::error title=Roster frozen::current.json is {stale_h:.1f}h old "
        f"(>= {ROSTER_STALE_ALARM_HOURS:.0f}h). HCSO WAF likely blocking the "
        f"runner IP; see the CLAUDE.md runbook."
    )
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log.warning("roster frozen %.1fh; GITHUB_TOKEN/GITHUB_REPOSITORY unset, "
                    "not opening an issue (dry-run)", stale_h)
        return "dry-run"
    try:
        if _open_freeze_issue_exists(repo, token):
            log.info("roster frozen %.1fh; freeze issue already open, not duplicating", stale_h)
            return "exists"
        _gh("POST", f"{API}/repos/{repo}/issues", token,
            {"title": ISSUE_TITLE, "body": _issue_body(stale_h)})
        log.error("roster frozen %.1fh; opened a freeze issue on %s", stale_h, repo)
        return "created"
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        # Never fail the workflow on an alerting error; the annotation already
        # fired and the open-data feeds must still commit.
        log.warning("freeze-alert issue API call failed: %s", e)
        return "dry-run"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    alert(roster_stale_hours(_prev_generated_utc(CURRENT_PATH)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
