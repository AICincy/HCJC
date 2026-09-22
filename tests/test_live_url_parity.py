"""Tests for the live-URL parity gate. No network: the probe fetch is
monkeypatched, so only the contract checks and the recovery-mode decision
(clobbered live serving no published data at all) are exercised."""

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

from scripts import verify_live_url_parity as parity

NAMES = ("current.json", "changelog.json", "history.json")
VALUE = {"generated_utc": "2026-09-22T21:17:03Z"}


def _http_error(code: int, url: str) -> HTTPError:
    return HTTPError(url, code, f"HTTP {code}", {}, None)


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
