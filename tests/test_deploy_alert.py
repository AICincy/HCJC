"""Tests for the deploy-staleness alert. No network: the live fetch and the
GitHub API calls are monkeypatched, so only the lag maths and the send-gate
are exercised."""

import pytest

from scraper import deploy_alert

FRESH = "2026-07-04T12:00:00Z"
BEHIND_20 = "2026-07-04T11:40:00Z"  # 20 min behind FRESH
BEHIND_120 = "2026-07-04T10:00:00Z"  # 120 min behind FRESH (> threshold)


def test_deploy_lag_minutes_basic():
    assert deploy_alert.deploy_lag_minutes(FRESH, BEHIND_120) == pytest.approx(120.0)
    assert deploy_alert.deploy_lag_minutes(FRESH, FRESH) == pytest.approx(0.0)


def test_deploy_lag_minutes_inconclusive():
    assert deploy_alert.deploy_lag_minutes(FRESH, None) is None
    assert deploy_alert.deploy_lag_minutes(None, FRESH) is None
    assert deploy_alert.deploy_lag_minutes(FRESH, "not-a-date") is None


def test_alert_unknown_when_inconclusive():
    assert deploy_alert.alert(FRESH, None) == "unknown"


def test_alert_ok_within_threshold(monkeypatch):
    # A one-cycle lag must not fire; the current push has not deployed yet.
    monkeypatch.setattr(
        deploy_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call the API when fresh")),
    )
    assert deploy_alert.alert(FRESH, BEHIND_20) == "ok"


def test_alert_dry_run_without_token(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert deploy_alert.alert(FRESH, BEHIND_120) == "dry-run"
    # The ::error:: annotation must still be emitted for the Actions UI.
    assert "::error title=Deploy stale::" in capsys.readouterr().out


def test_alert_skips_when_issue_already_open(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.setattr(deploy_alert, "_open_issue_exists", lambda repo, token: True)
    monkeypatch.setattr(
        deploy_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not POST when an issue is already open")),
    )
    assert deploy_alert.alert(FRESH, BEHIND_120) == "exists"


def test_alert_creates_issue_when_none_open(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    posted = {}

    def _fake_gh(method, url, token, payload=None):
        posted["method"] = method
        posted["payload"] = payload
        return {"number": 1}

    monkeypatch.setattr(deploy_alert, "_open_issue_exists", lambda repo, token: False)
    monkeypatch.setattr(deploy_alert, "_gh", _fake_gh)
    assert deploy_alert.alert(FRESH, BEHIND_120) == "created"
    assert posted["method"] == "POST"
    assert posted["payload"]["title"] == deploy_alert.ISSUE_TITLE


def test_alert_swallows_api_errors(monkeypatch):
    import urllib.error

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")

    def _boom(repo, token):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(deploy_alert, "_open_issue_exists", _boom)
    # Must not raise; alerting failure can't break the sweep workflow.
    assert deploy_alert.alert(FRESH, BEHIND_120) == "dry-run"


def test_fetch_live_generated_none_on_error(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(deploy_alert.urllib.request, "urlopen", _boom)
    assert deploy_alert._fetch_live_generated("https://example.com") is None
