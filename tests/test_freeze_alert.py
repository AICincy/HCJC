"""Tests for the roster-freeze alert. No network: the GitHub API calls are
monkeypatched, so only the staleness gating and the send-gate are exercised."""

import json
import time

import pytest

from scraper import freeze_alert
from scraper.sweep_guards import REMOVAL_SLA_HOURS, ROSTER_STALE_ALARM_HOURS


def test_alert_ok_when_fresh():
    assert freeze_alert.alert(1.0) == "ok"
    assert freeze_alert.alert(None) == "ok"


def test_removal_sla_warn_ok_below_window():
    assert freeze_alert.removal_sla_warn(None) == "ok"
    assert freeze_alert.removal_sla_warn(REMOVAL_SLA_HOURS - 0.1) == "ok"


def test_removal_sla_warn_fires_in_window(tmp_path, capsys):
    mid = (REMOVAL_SLA_HOURS + ROSTER_STALE_ALARM_HOURS) / 2
    assert freeze_alert.removal_sla_warn(mid, state_path=tmp_path / "state.json") == "warn"
    assert "::warning title=Roster stale past removal SLA::" in capsys.readouterr().out


def test_removal_sla_warn_throttles_repeat_emissions(tmp_path, capsys):
    # C-8: a second warning inside the throttle window is suppressed.
    mid = (REMOVAL_SLA_HOURS + ROSTER_STALE_ALARM_HOURS) / 2
    state = tmp_path / "state.json"
    assert freeze_alert.removal_sla_warn(mid, state_path=state) == "warn"
    capsys.readouterr()
    assert freeze_alert.removal_sla_warn(mid, state_path=state) == "throttled"
    assert "::warning" not in capsys.readouterr().out
    # ...and fires again once the window has lapsed (backdate the state).
    raw = json.loads(state.read_text(encoding="utf-8"))
    raw["last_warn_utc"] = time.time() - (freeze_alert._WARN_THROTTLE_HOURS + 1) * 3600
    state.write_text(json.dumps(raw), encoding="utf-8")
    assert freeze_alert.removal_sla_warn(mid, state_path=state) == "warn"


def test_removal_sla_warn_state_write_failure_still_warns(tmp_path, capsys, monkeypatch):
    # A state-write failure must never fail the alerting path.
    mid = (REMOVAL_SLA_HOURS + ROSTER_STALE_ALARM_HOURS) / 2
    bad = tmp_path / "nope" / "state.json"  # parent dir does not exist
    assert freeze_alert.removal_sla_warn(mid, state_path=bad) == "warn"
    assert "::warning title=Roster stale past removal SLA::" in capsys.readouterr().out


def test_removal_sla_warn_silent_at_freeze_threshold(capsys):
    # At/after the freeze alarm the ::error tier owns it; no ::warning.
    assert freeze_alert.removal_sla_warn(ROSTER_STALE_ALARM_HOURS) == "ok"
    assert freeze_alert.removal_sla_warn(ROSTER_STALE_ALARM_HOURS + 2) == "ok"
    assert "::warning" not in capsys.readouterr().out


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
    monkeypatch.setattr(
        freeze_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not POST when an issue is already open")),
    )
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


def test_gh_rejects_non_https_urls():
    for bad_url in ("file:///tmp/x", "ftp://example.com/x", "mailto:test@example.com"):
        with pytest.raises(ValueError):
            freeze_alert._gh("GET", bad_url, "tok")
