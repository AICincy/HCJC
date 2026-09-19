"""End-to-end build smoke tests: fixture data -> build -> verify output structure.

Exercises the real web.build.build() against minimal fixture snapshots,
including the last-good atomic-swap behavior on render/promote failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from scraper.models import Charge, Inmate, Snapshot


@pytest.fixture(autouse=True)
def _no_orc_offenses_rewrite(monkeypatch):
    """Hermeticity: web.build.build() calls update_orc_offenses(), which reads
    the real repo's data/current.json and conditionally rewrites the committed
    data/orc_offenses.json via absolute ROOT_DIR paths. Neutralize it; the
    fixture snapshots written by these tests are complete on their own."""
    monkeypatch.setattr("scraper.update_orc_offenses.update_orc_offenses", lambda: None)


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
    # A missing template or data file is a real failure: let it raise loudly
    # rather than passing vacuously.
    build(out)
    assert (out / "index.html").exists()


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


def test_build_swap_failure_restores_last_good(tmp_path, monkeypatch):
    """If the final promote (build_dir -> out_dir) fails after out_dir was
    moved aside, the last-good site must be restored, not left missing."""
    import pathlib

    _make_minimal_snapshot(tmp_path)
    monkeypatch.chdir(tmp_path)

    from web import build as build_mod

    out = tmp_path / "docs"
    try:
        build_mod.build(out)
    except FileNotFoundError:
        pytest.skip("templates/data not available in this env")
    good = (out / "index.html").read_text(encoding="utf-8")

    real_replace = pathlib.Path.replace

    def flaky_replace(self, target):
        # Fail only the promote; build_dir is the ".build-tmp" sibling.
        if self.name.endswith(".build-tmp"):
            raise OSError("promote boom")
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", flaky_replace)
    with pytest.raises(OSError):
        build_mod.build(out)

    # The promote failed, but the last-good site was restored, not left blank.
    assert (out / "index.html").exists()
    assert (out / "index.html").read_text(encoding="utf-8") == good
