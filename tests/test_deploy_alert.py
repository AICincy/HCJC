"""Tests for the deploy-staleness alert. No network: the live fetch and the
GitHub API calls are monkeypatched, so only the lag maths and the send-gate
are exercised."""

from datetime import datetime, timedelta, timezone

import pytest

from scraper import deploy_alert

FRESH = "2026-07-04T12:00:00Z"
BEHIND_20 = "2026-07-04T11:40:00Z"  # 20 min behind FRESH
BEHIND_120 = "2026-07-04T10:00:00Z"  # 120 min behind FRESH

FRESH_DT = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)
# "now" values relative to FRESH: how long main has held the FRESH snapshot.
JUST_PUSHED = FRESH_DT + timedelta(minutes=1)
STUCK = FRESH_DT + timedelta(minutes=deploy_alert.DEPLOY_PENDING_ALARM_MINUTES + 15)


def test_deploy_lag_minutes_basic():
    assert deploy_alert.deploy_lag_minutes(FRESH, BEHIND_120) == pytest.approx(120.0)
    assert deploy_alert.deploy_lag_minutes(FRESH, FRESH) == pytest.approx(0.0)


def test_deploy_lag_minutes_inconclusive():
    assert deploy_alert.deploy_lag_minutes(FRESH, None) is None
    assert deploy_alert.deploy_lag_minutes(None, FRESH) is None
    assert deploy_alert.deploy_lag_minutes(FRESH, "not-a-date") is None


def test_deploy_pending_minutes():
    # Live caught up (or ahead): nothing pending, however long ago the sweep was.
    assert deploy_alert.deploy_pending_minutes(FRESH, FRESH, STUCK) == 0.0
    assert deploy_alert.deploy_pending_minutes(BEHIND_20, FRESH, STUCK) == 0.0
    # Live behind: pending since the committed snapshot was generated.
    assert deploy_alert.deploy_pending_minutes(FRESH, BEHIND_120, JUST_PUSHED) == pytest.approx(1.0)
    assert deploy_alert.deploy_pending_minutes(FRESH, BEHIND_120, STUCK) == pytest.approx(
        deploy_alert.DEPLOY_PENDING_ALARM_MINUTES + 15
    )
    # Clock skew (committed snapshot "in the future") clamps to zero.
    assert deploy_alert.deploy_pending_minutes(FRESH, BEHIND_120, FRESH_DT - timedelta(minutes=5)) == 0.0
    assert deploy_alert.deploy_pending_minutes(FRESH, None, STUCK) is None


def test_issue_506_replay_does_not_fire(monkeypatch):
    """Regression: issue #506 was a false positive.

    The in-sweep alarm compared the just-committed snapshot against a site that
    had not deployed that push yet, so the "lag" was the gap since the previous
    sweep (258 min). Pages finished the deploy 27 s later. The watchdog checks
    the same timestamps at the moment the issue was opened and must stay quiet.
    """
    monkeypatch.setattr(
        deploy_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not open an issue")),
    )
    committed = "2026-09-24T03:53:52Z"
    live = "2026-09-23T23:35:42Z"
    opened_at = datetime(2026, 9, 24, 3, 54, 18, tzinfo=timezone.utc)
    assert deploy_alert.deploy_lag_minutes(committed, live) == pytest.approx(258.2, abs=0.1)
    assert deploy_alert.alert(committed, live, opened_at) == "ok"


def test_stuck_deploy_still_fires_after_grace(monkeypatch, capsys):
    """The same timestamps DO alarm if the deploy never lands."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    committed = "2026-09-24T03:53:52Z"
    live = "2026-09-23T23:35:42Z"
    later = datetime(2026, 9, 24, 4, 40, tzinfo=timezone.utc)
    assert deploy_alert.alert(committed, live, later) == "dry-run"
    assert "::error title=Deploy stale::" in capsys.readouterr().out


def test_alert_unknown_when_inconclusive():
    assert deploy_alert.alert(FRESH, None) == "unknown"


def test_alert_ok_within_threshold(monkeypatch):
    # A large timestamp gap must not fire while the newest push is still
    # inside the deploy grace window (the #506 false-positive shape).
    monkeypatch.setattr(
        deploy_alert,
        "_gh",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call the API when fresh")),
    )
    assert deploy_alert.alert(FRESH, BEHIND_120, JUST_PUSHED) == "ok"
    assert deploy_alert.alert(FRESH, BEHIND_20, JUST_PUSHED) == "ok"


def test_alert_dry_run_without_token(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert deploy_alert.alert(FRESH, BEHIND_120, STUCK) == "dry-run"
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
    assert deploy_alert.alert(FRESH, BEHIND_120, STUCK) == "exists"


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
    assert deploy_alert.alert(FRESH, BEHIND_120, STUCK) == "created"
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
    assert deploy_alert.alert(FRESH, BEHIND_120, STUCK) == "dry-run"


def test_fetch_live_generated_none_on_error(monkeypatch):
    def _boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(deploy_alert.urllib.request, "urlopen", _boom)
    assert deploy_alert._fetch_live_generated("https://example.com") is None


@pytest.mark.parametrize("site_url", ["https://example.com", "http://example.com/"])
def test_fetch_live_generated_accepts_http_schemes(monkeypatch, site_url):
    seen = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"generated_utc": "2026-07-04T12:00:00Z"}'

    def _ok(req, timeout=None):
        seen["url"] = req.full_url
        return _Resp()

    monkeypatch.setattr(deploy_alert.urllib.request, "urlopen", _ok)
    assert deploy_alert._fetch_live_generated(site_url) == FRESH
    assert seen["url"] == site_url.rstrip("/") + "/data/current.json"


@pytest.mark.parametrize(
    "site_url",
    [
        "file:///etc/passwd",
        "ftp://example.com",
        "gopher://example.com",
        "javascript:alert(1)",
        "data:text/plain,hello",
    ],
)
def test_fetch_live_generated_rejects_non_http_schemes(monkeypatch, site_url):
    def _boom(*a, **k):
        raise AssertionError("urlopen must not be called for non-http(s) URLs")

    monkeypatch.setattr(deploy_alert.urllib.request, "urlopen", _boom)
    assert deploy_alert._fetch_live_generated(site_url) is None
