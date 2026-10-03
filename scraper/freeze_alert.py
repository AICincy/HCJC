"""Active alert when the inmate roster has been frozen past the alarm window.

The degraded-roster guard in ``scraper.sweep`` correctly keeps the last-good
``data/current.json`` and exits 0 when HCSO's WAF blocks the runner, so a
multi-hour freeze never fails the workflow. This module turns that silent hold
into an active notification: run after the sweep step, it emits a GitHub
Actions ``::error`` annotation and opens a GitHub issue so subscribers are
notified.

Two tiers. :func:`removal_sla_warn` emits a quieter ``::warning`` annotation
(no issue) once the roster is stale past ``REMOVAL_SLA_HOURS`` (~1h), covering
the sub-6h window the freeze issue misses. :func:`alert` escalates to the
``::error`` annotation and the GitHub issue at ``ROSTER_STALE_ALARM_HOURS``
(6h). The warning tier gives earlier, spam-free visibility into a slipped cron
or a developing WAF block; the FCRA context is that a released inmate is
dropped on the next successful sweep, and the warning flags when that has
slipped past normal cadence.

The alarm measures data age only; it cannot tell why the data stopped
updating. A WAF block is one cause, but issue #564 was a ``KeyError`` in the
sweep's "Build static site" step, so the issue body stays diagnosis-neutral and
points at the latest sweep run instead of guessing.

Send-gate (mirrors the PRA loop): it dry-runs (logs only) unless both
``GITHUB_TOKEN`` and ``GITHUB_REPOSITORY`` are set. Dedupe: if an open issue
with the marker title already exists it does nothing, so a cron firing every
~30 minutes during a long freeze does not spam new issues or comments.

Auto-close: with ``auto_close=True`` (the out-of-band staleness watchdog, which
reads the committed ``main``), a fresh roster closes any open alarm issue this
bot opened, with a comment naming the fresh ``generated_utc``. The in-sweep
step leaves it off: it runs before the build and commit steps and reads the
runner's uncommitted ``current.json``, so in a #564-style build failure it
would see "fresh" data that never reached ``main`` and close a live alarm.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .sweep import CURRENT_PATH, _prev_generated_utc
from .sweep_guards import REMOVAL_SLA_HOURS, ROSTER_STALE_ALARM_HOURS, roster_stale_hours

log = logging.getLogger("jcstream.sweep")

API = "https://api.github.com"
ISSUE_TITLE = "Roster frozen: HCSO sweep is not updating current.json"
# Author of issues opened with the workflow GITHUB_TOKEN. Auto-close only
# touches issues by this login, never a human-filed issue with the same title.
BOT_LOGIN = "github-actions[bot]"
SWEEP_WORKFLOW_FILE = "sweep.yml"


def _gh(method: str, url: str, token: str, payload: dict | None = None) -> list | dict:
    """Minimal GitHub REST call using stdlib urllib (no extra dependency)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"unsupported GitHub API URL: {url!r}")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    # The URL is validated above (https-only, non-empty netloc) and callers
    # pass only the hardcoded API constant plus operator-controlled repo names.
    # This cannot be used for file:// arbitrary reads.
    # nosemgrep: dynamic-urllib-use-detected
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _open_freeze_issue_exists(repo: str, token: str) -> bool:
    """True if an open issue with the marker title already exists. Uses the
    search API with an in-title query so it can't miss the marker behind a
    large backlog of open issues (a paginated /issues list could)."""
    q = urllib.parse.quote(f'repo:{repo} is:issue is:open in:title "{ISSUE_TITLE}"')
    result = _gh("GET", f"{API}/search/issues?q={q}", token)
    items = result.get("items", []) if isinstance(result, dict) else []
    return any(isinstance(i, dict) and i.get("title") == ISSUE_TITLE for i in items)


def _open_bot_alarm_issues(repo: str, token: str) -> list[dict]:
    """Open issues with the marker title that this bot opened (same search
    query as :func:`_open_freeze_issue_exists`, filtered to ``BOT_LOGIN``)."""
    q = urllib.parse.quote(f'repo:{repo} is:issue is:open in:title "{ISSUE_TITLE}"')
    result = _gh("GET", f"{API}/search/issues?q={q}", token)
    items = result.get("items", []) if isinstance(result, dict) else []
    return [
        i
        for i in items
        if isinstance(i, dict)
        and i.get("title") == ISSUE_TITLE
        and isinstance(i.get("number"), int)
        and isinstance(i.get("user"), dict)
        and i["user"].get("login") == BOT_LOGIN
    ]


def _close_issue(repo: str, token: str, number: int, comment: str) -> None:
    """Comment on, then close, one alarm issue."""
    _gh("POST", f"{API}/repos/{repo}/issues/{number}/comments", token, {"body": comment})
    _gh("PATCH", f"{API}/repos/{repo}/issues/{number}", token, {"state": "closed", "state_reason": "completed"})


def _server_url() -> str:
    return (os.environ.get("GITHUB_SERVER_URL") or "https://github.com").rstrip("/")


def _sweep_runs_url(repo: str | None) -> str | None:
    """Actions page listing ``sweep.yml`` runs, newest first. Derived from the
    repo name alone, so it costs no API call or extra permission."""
    if not repo:
        return None
    return f"{_server_url()}/{repo}/actions/workflows/{SWEEP_WORKFLOW_FILE}"


def _current_run_url(repo: str | None) -> str | None:
    """URL of the Actions run raising this alarm (``GITHUB_RUN_ID``), if any.
    Inside ``sweep.yml`` that is the sweep run itself."""
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not repo or not run_id:
        return None
    return f"{_server_url()}/{repo}/actions/runs/{run_id}"


def _issue_body(stale_h: float, repo: str | None = None) -> str:
    runs_url = _sweep_runs_url(repo)
    run_url = _current_run_url(repo)
    if runs_url:
        where = f"Start with the latest `sweep` run: [sweep runs]({runs_url}) (newest first)."
    else:
        where = "Start with the latest `sweep` run in the Actions tab (workflow `sweep.yml`)."
    if run_url:
        where += f" This alarm was raised by [this run]({run_url})."
    return (
        f"The HCSO inmate roster data is stale: `data/current.json` has not updated "
        f"for **{stale_h:.1f} hours** (alarm threshold {ROSTER_STALE_ALARM_HOURS:.0f}h).\n\n"
        "This alarm measures data age only. It does not know why the data stopped "
        f"updating. {where}\n\n"
        "Possible causes (find the failing or degraded step in that run):\n"
        "- **Scrape or fetch failure** in the `HCSO inmate sweep` step. The "
        "degraded-roster guard keeps the last-good `data/current.json` and the step "
        "still exits 0, so look for `list sweep looks degraded` and the "
        "`N/M surname fetches failed` ratio. A WAF block on the runner IP shows up here.\n"
        "- **Build failure** in the `Build static site` step (for example a "
        "`KeyError` in `web.build`). The scrape succeeded but nothing was committed.\n"
        "- **Commit or push failure** in the `Commit generated source data and docs` "
        "step (rebase conflict or rejected push).\n"
        "- **No sweep ran at all** (stalled or dropped cron): the newest sweep run is "
        "older than the data.\n\n"
        "See the roster-frozen runbook in `CLAUDE.md`.\n\n"
        "_Opened automatically by `scraper.freeze_alert`. It will not duplicate while "
        "open, and the staleness watchdog closes it automatically once "
        "`data/current.json` on `main` is fresh again._"
    )


def _close_comment(stale_h: float, generated_utc: str | None) -> str:
    return (
        f"Data is fresh again: `data/current.json` on `main` was generated at "
        f"`{generated_utc or 'unknown'}` ({stale_h:.1f}h old, under the "
        f"{ROSTER_STALE_ALARM_HOURS:.0f}h alarm threshold). Closing automatically "
        f"(`scraper.freeze_alert`)."
    )


def _resolve(stale_h: float, generated_utc: str | None) -> str:
    """Close open bot alarm issues now that the roster is fresh. Returns
    ``"closed"`` if any were closed, else ``"ok"`` (none open, no token, or an
    API error, which is logged and never raised)."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return "ok"
    try:
        issues = _open_bot_alarm_issues(repo, token)
        for issue in issues:
            _close_issue(repo, token, issue["number"], _close_comment(stale_h, generated_utc))
            log.info("roster fresh (%.1fh); closed freeze issue #%s", stale_h, issue["number"])
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        log.warning("freeze-alert auto-close API call failed: %s", e)
        return "ok"
    return "closed" if issues else "ok"


def alert(stale_h: float | None, generated_utc: str | None = None, *, auto_close: bool = False) -> str:
    """Emit the freeze alert. Returns the action taken for logging/testing:
    ``\"ok\"`` (not frozen), ``\"closed\"`` (fresh, and ``auto_close`` closed
    an open alarm issue), ``\"dry-run\"`` (frozen, no token), ``\"exists\"``
    (issue already open), or ``\"created\"``.

    ``auto_close`` is only safe where ``generated_utc`` is the committed
    ``main`` value (the watchdog); see the module docstring."""
    if stale_h is None or stale_h < ROSTER_STALE_ALARM_HOURS:
        log.info("roster freshness OK (%s)", "unknown" if stale_h is None else f"{stale_h:.1f}h")
        if auto_close and stale_h is not None:
            return _resolve(stale_h, generated_utc)
        return "ok"

    # Frozen: surface in the Actions UI regardless of token availability.
    print(
        f"::error title=Roster frozen::current.json is {stale_h:.1f}h old "
        f"(>= {ROSTER_STALE_ALARM_HOURS:.0f}h). Check the latest sweep run for a "
        f"scrape, build, or commit/push failure; see the CLAUDE.md runbook."
    )
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log.warning(
            "roster frozen %.1fh; GITHUB_TOKEN/GITHUB_REPOSITORY unset, not opening an issue (dry-run)", stale_h
        )
        return "dry-run"
    try:
        if _open_freeze_issue_exists(repo, token):
            log.info("roster frozen %.1fh; freeze issue already open, not duplicating", stale_h)
            return "exists"
        _gh("POST", f"{API}/repos/{repo}/issues", token, {"title": ISSUE_TITLE, "body": _issue_body(stale_h, repo)})
        log.error("roster frozen %.1fh; opened a freeze issue on %s", stale_h, repo)
        return "created"
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
        # Never fail the workflow on an alerting error; the annotation already
        # fired and the open-data feeds must still commit.
        log.warning("freeze-alert issue API call failed: %s", e)
        return "dry-run"


# C-8: the ::warning annotation below fires once per sweep cycle while the
# roster sits in the removal-SLA window. During a multi-day WAF block that is
# one annotation per ~30-minute cycle with no change in state -- pure spam.
# Throttle: at most one emission per window. State lives in a small JSON file
# committed to the repo (the runner is ephemeral), so the throttle holds
# across cycles; the file only changes when a warning actually fires, so the
# sweep's commit step picks up at most one extra commit per throttle window.
_WARN_THROTTLE_HOURS = 6.0
_WARN_STATE_FILENAME = "freeze_alert_state.json"


def _warn_state_path() -> Path:
    override = os.environ.get("JCSTREAM_FREEZE_WARN_STATE")
    if override:
        return Path(override)
    return CURRENT_PATH.parent / _WARN_STATE_FILENAME


def _warn_throttled(state_path: Path) -> bool:
    """True when a warning was already emitted within the throttle window."""
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        last = float(raw.get("last_warn_utc", 0) or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return False
    return (time.time() - last) < _WARN_THROTTLE_HOURS * 3600


def removal_sla_warn(stale_h: float | None, *, state_path: Path | None = None) -> str:
    """Emit a GitHub Actions ``::warning`` when the roster is stale past the
    removal-SLA window but below the freeze alarm.

    This surfaces the sub-6h window the freeze issue does not cover, so a
    slipped cron or an early WAF block gets visibility before the 6h issue
    fires. It is a log annotation only (no issue), so it cannot spam during a
    multi-day WAF block; the FCRA context is that a released inmate is removed
    on the next successful sweep, and this flags when that has been delayed
    past normal cadence. Returns ``\"warn\"`` when the annotation fired, ``\"ok\"``
    otherwise (fresh, unknown, or already at the freeze threshold), and
    ``\"throttled\"`` when a warning was already emitted within the throttle
    window (C-8)."""
    if stale_h is None or stale_h < REMOVAL_SLA_HOURS or stale_h >= ROSTER_STALE_ALARM_HOURS:
        return "ok"
    # C-8: emit at most one warning per throttle window.
    path = state_path if state_path is not None else _warn_state_path()
    if _warn_throttled(path):
        log.info(
            "removal-SLA warning throttled (already emitted within the last %.0fh)",
            _WARN_THROTTLE_HOURS,
        )
        return "throttled"
    print(
        f"::warning title=Roster stale past removal SLA::current.json is "
        f"{stale_h:.1f}h old (>= {REMOVAL_SLA_HOURS:.1f}h removal-SLA window, "
        f"< {ROSTER_STALE_ALARM_HOURS:.0f}h freeze alarm). A released inmate may "
        f"still be listed until the next successful sweep. See the CLAUDE.md runbook."
    )
    log.warning(
        "roster stale %.1fh: past the %.1fh removal-SLA window (< %.0fh freeze)",
        stale_h,
        REMOVAL_SLA_HOURS,
        ROSTER_STALE_ALARM_HOURS,
    )
    # Best-effort: a state-write failure must never fail the workflow; the
    # worst case is one extra warning next cycle.
    try:
        path.write_text(
            json.dumps({"last_warn_utc": time.time(), "stale_hours": round(stale_h, 2)}),
            encoding="utf-8",
        )
    except OSError as e:
        log.warning("could not persist freeze-warn state (%s); warning still emitted", e)
    return "warn"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stale_h = roster_stale_hours(_prev_generated_utc(CURRENT_PATH))
    removal_sla_warn(stale_h)
    # No auto_close here: this is the in-sweep step, which reads the runner's
    # not-yet-committed current.json (see the module docstring).
    alert(stale_h)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
