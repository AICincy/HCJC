"""Tests for the roster-freeze alert. No network: the GitHub API calls are
monkeypatched, so only the staleness gating and the send-gate are exercised."""
from scraper import freeze_alert
from scraper.sweep_guards import ROSTER_STALE_ALARM_HOURS


def test_alert_ok_when_fresh(caplog):
    assert freeze_alert.alert(1.0) == "ok"
    assert freeze_alert.alert(None) == "ok"


def test_alert_dry_run_without_token(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 1) == "dry-run"
    # The ::error:: annotation must still be emitted for the Actions UI.
    assert "::error title=Roster frozen::" in capsys.readouterr().out


def test_alert_skips_when_issue_already_open(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.setattr(freeze_alert, "_open_freeze_issue_exists", lambda repo, token: True)
    monkeypatch.setattr(freeze_alert, "_gh", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not POST when an issue is already open")))
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 5) == "exists"


def test_alert_creates_issue_when_none_open(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    posted = {}
    monkeypatch.setattr(freeze_alert, "_open_freeze_issue_exists", lambda repo, token: False)

    def _fake_gh(method, url, token, payload=None):
        posted["method"] = method
        posted["payload"] = payload
        return {"number": 1}

    monkeypatch.setattr(freeze_alert, "_gh", _fake_gh)
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 5) == "created"
    assert posted["method"] == "POST"
    assert posted["payload"]["title"] == freeze_alert.ISSUE_TITLE


def test_alert_swallows_api_errors(monkeypatch):
    import urllib.error

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")

    def _boom(repo, token):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(freeze_alert, "_open_freeze_issue_exists", _boom)
    # Must not raise; alerting failure can't break the sweep workflow.
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 5) == "dry-run"
