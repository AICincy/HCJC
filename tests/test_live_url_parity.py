"""Tests for the live-URL parity gate. No network: the probe fetch is
monkeypatched, so only the contract checks, the transient-retry policy, and
the recovery-mode decision (clobbered live serving no published data at all)
are exercised. Backoff sleep is monkeypatched, so retries cost no time."""

import json
import sys
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from scripts import verify_live_url_parity as parity

NAMES = ("current.json", "changelog.json", "history.json")
VALUE = {"generated_utc": "2026-09-22T21:17:03Z"}


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    """Record backoff delays instead of sleeping."""
    recorded: list[float] = []
    monkeypatch.setattr(parity, "sleep", recorded.append)
    return recorded


def _http_error(code: int, url: str, retry_after: str | None = None) -> HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(url, code, f"HTTP {code}", headers, None)


def _setup(tmp_path: Path, monkeypatch, live, local_names=NAMES, extra_argv=()):
    """Build a manifest + local artifact tree, patch the probe fetch, and
    return argv for ``parity.main``. ``live`` maps a file name to either a
    ``(status, content_type, body_bytes)`` tuple or an Exception to raise."""
    manifest = {
        "schema_version": 1,
        "description": "test",
        "files": [
            {"path": name, "source": f"data/{name}", "mode": "copy", "privacy": "t"}
            for name in NAMES
        ],
    }
    (tmp_path / "docs" / "data").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "public-data-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    for name in local_names:
        (tmp_path / "docs" / "data" / name).write_text(json.dumps(VALUE), encoding="utf-8")

    def fake_fetch(url, timeout):
        name = url.rsplit("/", 1)[-1]
        result = live[name]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(parity, "fetch", fake_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            parity.__file__,
            "--site",
            "https://example.test",
            "--manifest",
            str(tmp_path / "config" / "public-data-manifest.json"),
            "--local",
            str(tmp_path / "docs" / "data"),
            *extra_argv,
        ],
    )
    return manifest


def _ok(name):
    return (200, "application/json", json.dumps(VALUE).encode())


def test_all_live_ok_passes(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {name: _ok(name) for name in NAMES})
    assert parity.main() == 0
    assert "live URL parity OK" in capsys.readouterr().out


def test_all_404_enters_recovery_mode(tmp_path, monkeypatch, capsys):
    # Clobbered-live signature: every manifest path 404s. The gate warns and
    # passes so this deploy can restore the contract.
    live = {name: _http_error(404, f"https://example.test/data/{name}") for name in NAMES}
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 0
    out = capsys.readouterr().out
    assert "recovery mode" in out
    assert "::warning title=Live parity gate (recovery mode)::-" in out
    assert "/data/current.json" in out


def test_partial_404_still_fails(tmp_path, monkeypatch, capsys):
    # A rename/removal 404s only the affected path while the rest probe OK.
    live = {name: _ok(name) for name in NAMES}
    live["history.json"] = _http_error(404, "https://example.test/data/history.json")
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 1
    assert "recovery mode" not in capsys.readouterr().out


def test_404_plus_network_error_still_fails(tmp_path, monkeypatch, capsys):
    # An unreachable site is not the clobber signature; stay fail-closed.
    live = {name: _ok(name) for name in NAMES}
    live["current.json"] = _http_error(404, "https://example.test/data/current.json")
    live["changelog.json"] = URLError("connection reset")
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 1
    assert "recovery mode" not in capsys.readouterr().out


def test_all_500_still_fails(tmp_path, monkeypatch):
    live = {name: _http_error(500, f"https://example.test/data/{name}") for name in NAMES}
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 1


def test_compare_bytes_never_recovers(tmp_path, monkeypatch, capsys):
    # Frozen release validation is always strict, even on a clobbered live.
    live = {name: _http_error(404, f"https://example.test/data/{name}") for name in NAMES}
    _setup(tmp_path, monkeypatch, live, extra_argv=("--compare-bytes",))
    assert parity.main() == 1
    assert "recovery mode" not in capsys.readouterr().out


def test_shape_mismatch_still_fails(tmp_path, monkeypatch):
    live = {
        "current.json": _ok("current.json"),
        "changelog.json": _ok("changelog.json"),
        "history.json": (200, "application/json", json.dumps({"renamed": True}).encode()),
    }
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 1


def test_local_missing_blocks_recovery(tmp_path, monkeypatch):
    # A local artifact gap is a non-404 error, so the all-404 signature does
    # not hold even when the live 404s every path.
    live = {name: _http_error(404, f"https://example.test/data/{name}") for name in NAMES}
    _setup(tmp_path, monkeypatch, live, local_names=("current.json", "changelog.json"))
    assert parity.main() == 1


def _sequence_fetch(monkeypatch, results):
    """Patch the probe fetch to return/raise ``results`` in order (the last
    one repeats) and return the list of URLs it was called with."""
    calls: list[str] = []
    queue = list(results)

    def fake_fetch(url, timeout):
        calls.append(url)
        result = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(parity, "fetch", fake_fetch)
    return calls


URL = "https://example.test/data/current.json"


def test_503_then_200_passes_after_one_retry(tmp_path, monkeypatch, capsys, sleeps):
    # The 2026-10-04 publish-race signature: one 503, then the CDN serves it.
    _setup(tmp_path, monkeypatch, {name: _ok(name) for name in NAMES})
    calls = _sequence_fetch(monkeypatch, [_http_error(503, URL), _ok("current.json")])
    assert parity.main() == 0
    out = capsys.readouterr().out
    assert "live URL parity OK: 3 published JSON URL(s) checked" in out
    assert "RETRY: https://example.test/data/current.json: HTTP 503 on attempt 1/4; retrying in 2s" in out
    assert sleeps == [2.0]
    assert len(calls) == 4  # current.json twice, the other two once


def test_persistent_503_fails_after_max_attempts(capsys, monkeypatch, sleeps):
    calls = _sequence_fetch(monkeypatch, [_http_error(503, URL)])
    with pytest.raises(HTTPError) as exc_info:
        parity.fetch_with_retry(URL, 1.0, parity.RetryBudget())
    assert exc_info.value.code == 503
    assert len(calls) == parity.MAX_ATTEMPTS == 4
    assert sleeps == [2.0, 4.0, 8.0]
    assert capsys.readouterr().out.count("RETRY: ") == 3


def test_persistent_503_fails_the_gate(tmp_path, monkeypatch, capsys, sleeps):
    live = {name: _ok(name) for name in NAMES}
    live["history.json"] = _http_error(503, "https://example.test/data/history.json")
    _setup(tmp_path, monkeypatch, live)
    assert parity.main() == 1
    out = capsys.readouterr().out
    assert "ERROR: history.json: HTTP 503 from https://example.test/data/history.json" in out
    assert sleeps == [2.0, 4.0, 8.0]


def test_404_fails_without_retry(tmp_path, monkeypatch, capsys, sleeps):
    _setup(tmp_path, monkeypatch, {name: _ok(name) for name in NAMES})
    calls = _sequence_fetch(monkeypatch, [_http_error(404, URL), _ok("current.json")])
    assert parity.main() == 1
    out = capsys.readouterr().out
    assert "ERROR: current.json: HTTP 404 from" in out
    assert "RETRY" not in out
    assert sleeps == []
    assert len(calls) == 3  # one probe per file, no second current.json call


@pytest.mark.parametrize("code", [400, 403, 410, 429])
def test_other_4xx_never_retried(monkeypatch, sleeps, code):
    calls = _sequence_fetch(monkeypatch, [_http_error(code, URL), _ok("current.json")])
    with pytest.raises(HTTPError):
        parity.fetch_with_retry(URL, 1.0, parity.RetryBudget())
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize(
    "exc", [_http_error(500, URL), _http_error(502, URL), _http_error(504, URL), URLError("reset"), TimeoutError("t")]
)
def test_transient_failures_retried(monkeypatch, sleeps, exc):
    calls = _sequence_fetch(monkeypatch, [exc, _ok("current.json")])
    assert parity.fetch_with_retry(URL, 1.0, parity.RetryBudget()) == _ok("current.json")
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_retry_after_honored_and_capped(monkeypatch, sleeps):
    _sequence_fetch(
        monkeypatch,
        [
            _http_error(503, URL, retry_after="1"),
            _http_error(503, URL, retry_after="120"),
            _http_error(503, URL, retry_after="Wed, 21 Oct 2026 07:28:00 GMT"),
            _ok("current.json"),
        ],
    )
    parity.fetch_with_retry(URL, 1.0, parity.RetryBudget())
    # Seconds honored, capped at RETRY_AFTER_CAP; an HTTP-date falls back to backoff.
    assert sleeps == [1.0, parity.RETRY_AFTER_CAP, 8.0]


def test_run_retry_budget_bounds_total_retries(monkeypatch, capsys, sleeps):
    calls = _sequence_fetch(monkeypatch, [_http_error(503, URL)])
    budget = parity.RetryBudget(remaining=2)
    with pytest.raises(HTTPError):
        parity.fetch_with_retry(URL, 1.0, budget)
    assert len(calls) == 3
    assert sleeps == [2.0, 4.0]
    assert "run retry budget (8) exhausted" in capsys.readouterr().out
