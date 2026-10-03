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


# --- Diagnosis-neutral body (issue #564: the cause was a build KeyError, not a WAF block) ---


def test_issue_body_is_diagnosis_neutral(monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    body = freeze_alert._issue_body(9.6, "AICincy/HCJC")
    assert "9.6 hours" in body
    # No hard-coded single theory.
    assert "almost always" not in body
    assert "WAF blocking" not in body
    # Points at the latest sweep run...
    assert "https://github.com/AICincy/HCJC/actions/workflows/sweep.yml" in body
    # ...and lists the possible causes.
    assert "Scrape or fetch failure" in body
    assert "Build failure" in body
    assert "Build static site" in body
    assert "Commit or push failure" in body
    assert "closes it automatically" in body


def test_issue_body_links_raising_run_when_known(monkeypatch):
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    body = freeze_alert._issue_body(7.0, "AICincy/HCJC")
    assert "https://github.com/AICincy/HCJC/actions/runs/12345" in body


def test_issue_body_without_repo_still_points_at_sweep(monkeypatch):
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    body = freeze_alert._issue_body(7.0)
    assert "sweep.yml" in body
    assert "https://" not in body


def test_error_annotation_is_diagnosis_neutral(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 1)
    out = capsys.readouterr().out
    assert "::error title=Roster frozen::" in out
    assert "WAF" not in out
    assert "build" in out


def test_created_issue_body_links_sweep_runs(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)
    posted = {}
    monkeypatch.setattr(freeze_alert, "_open_freeze_issue_exists", lambda repo, token: False)

    def _fake_gh(method, url, token, payload=None):
        posted["payload"] = payload
        return {"number": 1}

    monkeypatch.setattr(freeze_alert, "_gh", _fake_gh)
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 5) == "created"
    assert "https://github.com/AICincy/HCJC/actions/workflows/sweep.yml" in posted["payload"]["body"]


# --- Auto-close when fresh again ---

FRESH_GEN = "2026-10-03T19:44:00Z"


def _search_result(*items):
    return {"items": list(items)}


def _issue(number, title=freeze_alert.ISSUE_TITLE, login=freeze_alert.BOT_LOGIN):
    return {"number": number, "title": title, "user": {"login": login}}


def _recording_gh(search_result):
    calls = []

    def _fake_gh(method, url, token, payload=None):
        calls.append((method, url, payload))
        if method == "GET":
            return search_result
        return {}

    return calls, _fake_gh


def test_fresh_closes_open_bot_alarm_issue(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    calls, fake = _recording_gh(
        _search_result(
            _issue(564),
            _issue(570, login="JaredKrass"),  # human-filed, same title: leave it alone
            _issue(571, title="Roster frozen: something else"),  # not the marker title
        )
    )
    monkeypatch.setattr(freeze_alert, "_gh", fake)
    assert freeze_alert.alert(0.3, FRESH_GEN, auto_close=True) == "closed"

    writes = [(m, u, p) for m, u, p in calls if m != "GET"]
    assert [(m, u) for m, u, _ in writes] == [
        ("POST", f"{freeze_alert.API}/repos/AICincy/HCJC/issues/564/comments"),
        ("PATCH", f"{freeze_alert.API}/repos/AICincy/HCJC/issues/564"),
    ]
    assert FRESH_GEN in writes[0][2]["body"]
    assert writes[1][2]["state"] == "closed"


def test_fresh_with_nothing_open_is_ok(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    calls, fake = _recording_gh(_search_result())
    monkeypatch.setattr(freeze_alert, "_gh", fake)
    assert freeze_alert.alert(0.3, FRESH_GEN, auto_close=True) == "ok"
    assert [m for m, _, _ in calls] == ["GET"]


def test_fresh_without_auto_close_makes_no_api_calls(monkeypatch):
    # The in-sweep step reads uncommitted data; it must never close (see #564).
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.setattr(
        freeze_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call the API without auto_close")),
    )
    assert freeze_alert.alert(0.3, FRESH_GEN) == "ok"


def test_unknown_staleness_never_closes(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.setattr(
        freeze_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("unknown freshness must not close")),
    )
    assert freeze_alert.alert(None, None, auto_close=True) == "ok"


def test_auto_close_dry_run_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(
        freeze_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call the API without a token")),
    )
    assert freeze_alert.alert(0.3, FRESH_GEN, auto_close=True) == "ok"


def test_auto_close_swallows_api_errors(monkeypatch):
    import urllib.error

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")

    def _boom(*a, **k):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(freeze_alert, "_gh", _boom)
    assert freeze_alert.alert(0.3, FRESH_GEN, auto_close=True) == "ok"


def test_still_frozen_with_auto_close_does_not_close(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "AICincy/HCJC")
    monkeypatch.setattr(freeze_alert, "_open_freeze_issue_exists", lambda repo, token: True)
    monkeypatch.setattr(
        freeze_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write while still frozen")),
    )
    assert freeze_alert.alert(ROSTER_STALE_ALARM_HOURS + 1, FRESH_GEN, auto_close=True) == "exists"
