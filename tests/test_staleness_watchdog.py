"""Guards for the out-of-band staleness watchdog.

The deploy-staleness alarm used to run as the last step of sweep.yml, so a
stalled sweep cron silenced the alarm that should report it (issue #496), and
running inside the sweep made it compare against its own not-yet-deployed push
(issue #506 false positive). These tests pin the decoupling.
"""

from __future__ import annotations

from pathlib import Path

from scraper import deploy_alert, freeze_alert, staleness_watchdog

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _code_lines(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def test_sweep_no_longer_runs_deploy_alert() -> None:
    assert "scraper.deploy_alert" not in _code_lines(_workflow("sweep.yml")), (
        "deploy_alert must not run inside sweep.yml: it shares the sweep's failure "
        "domain and compares against its own undeployed push (#496, #506)."
    )


def test_watchdog_workflow_is_independent_and_read_only() -> None:
    text = _code_lines(_workflow("staleness-watchdog.yml"))
    assert "python -m scraper.staleness_watchdog" in text
    assert "schedule:" in text and "cron:" in text, "watchdog needs its own schedule"
    assert "workflow_dispatch" in text
    # Must not share the sweep's concurrency group (a queued sweep would block it).
    assert "jcstream-sweep" not in text
    # Read-only on contents; issues:write only.
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "issues: write" in text
    assert "git push" not in text


def test_run_isolates_check_failures(monkeypatch) -> None:
    def _boom(*a, **k):
        raise RuntimeError("freeze exploded")

    monkeypatch.setattr(freeze_alert, "alert", _boom)
    monkeypatch.setattr(deploy_alert, "_fetch_live_generated", lambda url: None)
    results = staleness_watchdog.run("2026-09-24T03:53:52Z", "https://example.com")
    assert results == {"freeze": "error", "deploy": "unknown"}


def test_run_reports_both_checks(monkeypatch) -> None:
    seen = {}

    def _freeze(stale_h, generated_utc=None, *, auto_close=False):
        seen["stale_h"] = stale_h
        seen["generated_utc"] = generated_utc
        seen["auto_close"] = auto_close
        return "ok"

    monkeypatch.setattr(freeze_alert, "alert", _freeze)
    monkeypatch.setattr(deploy_alert, "_fetch_live_generated", lambda url: "2026-09-24T03:53:52Z")
    # No token: the deploy auto-close path must stay a no-op.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    results = staleness_watchdog.run("2026-09-24T03:53:52Z", "https://example.com")
    assert results == {"freeze": "ok", "deploy": "ok"}
    assert seen["stale_h"] is not None
    # The watchdog reads committed main, so it is the path that auto-closes.
    assert seen["generated_utc"] == "2026-09-24T03:53:52Z"
    assert seen["auto_close"] is True


def test_run_passes_auto_close_to_deploy_check(monkeypatch) -> None:
    seen = {}

    def _deploy(local_generated, live_generated, now=None, *, auto_close=False):
        seen["auto_close"] = auto_close
        return "ok"

    monkeypatch.setattr(freeze_alert, "alert", lambda *a, **k: "ok")
    monkeypatch.setattr(deploy_alert, "_fetch_live_generated", lambda url: "2026-09-24T03:53:52Z")
    monkeypatch.setattr(deploy_alert, "alert", _deploy)
    staleness_watchdog.run("2026-09-24T03:53:52Z", "https://example.com")
    assert seen["auto_close"] is True
