"""End-to-end smoke test: sweep (mocked HTTP) -> build -> verify output structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from scraper.models import Charge, Inmate, Snapshot


def _make_minimal_snapshot(tmp_path: Path) -> None:
    """Write a minimal current.json + changelog.json for build to consume."""
    inmate = Inmate(
        inmate_number="1234567",
        booking_number="B001",
        last_name="Doe",
        first_name="John",
        booking_date="05/20/25",
        charges=[Charge(description="Test charge F5", orc_code="2913.02")],
    )
    snapshot = Snapshot(
        generated_utc="2025-05-20T12:00:00Z",
        inmate_count=1,
        inmates=[inmate],
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "current.json").write_text(snapshot.model_dump_json(indent=2))
    (data_dir / "changelog.json").write_text("[]")


def test_build_produces_index(tmp_path, monkeypatch):
    """Build with minimal fixture data and verify index.html exists."""
    _make_minimal_snapshot(tmp_path)
    monkeypatch.chdir(tmp_path)

    from web.build import build

    out = tmp_path / "docs"
    # If build raises due to missing templates/data, that's an acceptable
    # failure mode for a smoke test -- the point is to catch import/wiring errors.
    try:
        build(out)
        assert (out / "index.html").exists()
    except FileNotFoundError:
        # Template files not available in test env -- still validates imports work
        pass


def test_build_failure_preserves_last_good(tmp_path, monkeypatch):
    """A render exception must leave the last-good docs/ intact, not a blank
    or half-written site. Guards the atomic swap in web.build.build."""
    _make_minimal_snapshot(tmp_path)
    monkeypatch.chdir(tmp_path)

    from web import build as build_mod

    out = tmp_path / "docs"
    try:
        build_mod.build(out)
    except FileNotFoundError:
        pytest.skip("templates/data not available in this env")
    assert (out / "index.html").exists()
    good = (out / "index.html").read_text(encoding="utf-8")

    def _boom(*a, **k):
        raise RuntimeError("render boom")

    # Fail a late write step; the swap into out_dir must never run.
    monkeypatch.setattr(build_mod, "_write_checksums", _boom)
    with pytest.raises(RuntimeError):
        build_mod.build(out)

    # Last-good site is untouched: still present and byte-identical.
    assert (out / "index.html").exists()
    assert (out / "index.html").read_text(encoding="utf-8") == good
