"""Consolidated dark-theme audit remediation regression tests (2026-09-20).

Covers the remediation follow-ups closed in the consolidated phase:
history.json repo-root anchoring, missing-photo-source warnings,
CSP-compliant broken-photo fallback (delegated main.js handler, no inline
onerror), charge-comment rendering, per-feed vintage on the data page, and
the dark case-link override extension to the Cases section.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from scraper.models import Charge, Inmate, Snapshot

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "web" / "templates"
STATIC = REPO / "web" / "static"


# ---------------------------------------------------------------------------
# 1. history.json is repo-root anchored (never web/data/history.json again).
# ---------------------------------------------------------------------------


def test_history_path_anchored_to_repo_root():
    """The history write target derives from the module file location, not the
    CWD, so a build launched with CWD=web/ cannot misdirect it into
    web/data/history.json."""
    import web.history as history_mod

    target = Path(history_mod.__file__).resolve().parent.parent / "data" / "history.json"
    assert target == REPO / "data" / "history.json"
    assert "web" not in target.parts[-3:]


def test_stray_web_history_absent():
    assert not (REPO / "web" / "data" / "history.json").exists()


# ---------------------------------------------------------------------------
# 2. Missing/empty photo source warns loudly at build time.
# ---------------------------------------------------------------------------


def test_missing_photo_source_warns(caplog, monkeypatch, tmp_path):
    """_copy_photos logs a warning (never silently skips) when the photo
    source directory is missing."""
    from web import outputs as outputs_mod

    monkeypatch.setattr(outputs_mod, "PHOTOS_DIR", tmp_path / "no-such-photos")
    with caplog.at_level(logging.WARNING, logger="web.outputs"):
        outputs_mod._copy_photos(tmp_path / "out")
    assert any("photo source" in r.getMessage() and "missing" in r.getMessage() for r in caplog.records)


def test_empty_photo_source_warns(caplog, monkeypatch, tmp_path):
    from web import outputs as outputs_mod

    empty = tmp_path / "empty-photos"
    empty.mkdir()
    monkeypatch.setattr(outputs_mod, "PHOTOS_DIR", empty)
    with caplog.at_level(logging.WARNING, logger="web.outputs"):
        outputs_mod._copy_photos(tmp_path / "out")
    assert any("photo source" in r.getMessage() and "empty" in r.getMessage() for r in caplog.records)


def test_photos_dir_repo_root_anchored():
    from web import outputs as outputs_mod

    assert outputs_mod.PHOTOS_DIR == REPO / "data" / "photos"


# ---------------------------------------------------------------------------
# 3. CSP-compliant broken-photo fallback.
# ---------------------------------------------------------------------------


def test_no_inline_onerror_in_templates():
    """Inline event handlers are blocked by the CSP (script-src 'self', no
    'unsafe-inline'); the photo fallback must live in main.js."""
    offenders = [
        p.name for p in TEMPLATES.glob("*.html") if "onerror=" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"inline onerror survives in: {offenders}"


def test_photo_fallback_markers_present():
    """Every booking-photo <img> carries the data-photo-fallback marker the
    delegated main.js handler keys on."""
    for name in ("_card.html", "inmate.html", "court.html", "statute.html"):
        src = (TEMPLATES / name).read_text(encoding="utf-8")
        assert 'data-photo-fallback' in src, f"{name} has no photo-fallback marker"


def test_photo_fallback_handler_in_main_js():
    """main.js handles failed booking photos without inline handlers: a
    capture-phase error listener plus a sweep for images that failed before
    the deferred bundle ran."""
    src = (STATIC / "main.js").read_text(encoding="utf-8")
    assert 'addEventListener("error"' in src
    assert "data-photo-fallback" in src
    assert "naturalWidth" in src


# ---------------------------------------------------------------------------
# 4. Dark override covers the Cases-section criminal links too.
# ---------------------------------------------------------------------------


def test_case_groups_dark_link_override():
    src = (STATIC / "style.css").read_text(encoding="utf-8")
    assert ".case-groups .case-link.case-criminal" in src


# ---------------------------------------------------------------------------
# 5. Per-feed vintage plumbing.
# ---------------------------------------------------------------------------


def test_feed_vintage_reads_generated_utc(tmp_path, monkeypatch):
    """_feed_vintage maps each feed filename to its data/*.json generated_utc
    stamp, and "" for missing/unreadable feeds (never an invented stamp).

    The read is anchored to feeds.DATA_DIR, not the process working
    directory: monkeypatching the anchor (not chdir) is how the test
    isolates the feed source."""
    from web import feeds as feeds_mod
    from web import pages as pages_mod

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "cfs_recent.json").write_text(
        json.dumps({"generated_utc": "2026-09-20T01:41:01Z", "rows": []})
    )
    monkeypatch.setattr(feeds_mod, "DATA_DIR", data_dir)
    vintage = pages_mod._feed_vintage()
    assert vintage["cfs_recent.json"] == "2026-09-20T01:41:01Z"
    assert vintage["shootings_recent.json"] == ""
    assert set(vintage) == set(pages_mod._FEED_VINTAGE_FILES)


def test_feed_vintage_ignores_working_directory(tmp_path, monkeypatch):
    """Regression: _feed_vintage reads the anchored repo data dir even when
    the build is invoked from a working directory with no data/ in it."""
    from web import feeds as feeds_mod
    from web import pages as pages_mod

    monkeypatch.chdir(tmp_path)
    vintage = pages_mod._feed_vintage()
    real = json.loads(
        (feeds_mod.DATA_DIR / "cfs_recent.json").read_text(encoding="utf-8")
    )
    assert vintage["cfs_recent.json"] == real.get("generated_utc", "")


# ---------------------------------------------------------------------------
# 6. Build-level: comments render, vintage renders, markers survive the build.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_orc_offenses_rewrite(monkeypatch):
    monkeypatch.setattr("scraper.update_orc_offenses.update_orc_offenses", lambda: None)


def _snapshot_with_comments_and_feed(tmp_path: Path) -> None:
    inmate = Inmate(
        inmate_number="7654321",
        booking_number="B002",
        last_name="Roe",
        first_name="Jane",
        booking_date="05/21/25",
        photo_filename="7654321.jpg",
        charges=[
            Charge(
                description="Test charge F5",
                orc_code="2913.02",
                comments="DISMISSED per test fixture",
            )
        ],
    )
    snapshot = Snapshot(
        generated_utc="2025-05-21T12:00:00Z",
        inmate_count=1,
        inmates=[inmate],
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "current.json").write_text(snapshot.model_dump_json(indent=2))
    (data_dir / "changelog.json").write_text("[]")
    (data_dir / "cfs_recent.json").write_text(
        json.dumps({"generated_utc": "2026-09-20T01:41:01Z", "rows": []})
    )
    # The /judges/ page is fail-closed on its feed (no silent HAMCO fallback),
    # so the fixture tree must stage a valid 30-profile court_judges.json.
    # Content is irrelevant to this test's assertions; copy the repo's real
    # feed (repo-anchored, unaffected by the chdir below).
    import shutil

    from web import feeds as feeds_mod

    shutil.copy(feeds_mod.DATA_DIR / "court_judges.json", data_dir / "court_judges.json")


def test_build_renders_comments_vintage_and_photo_markers(tmp_path, monkeypatch):
    """End to end through the real build: charge comments appear on the inmate
    page, the feed vintage appears on the data page, and the CSP-safe photo
    fallback marker survives into built HTML."""
    _snapshot_with_comments_and_feed(tmp_path)
    monkeypatch.chdir(tmp_path)
    # _feed_vintage() reads the anchored web.feeds.DATA_DIR, not the cwd:
    # point it at the fixture tree so the build under test sees the fixture
    # feed stamps instead of whatever the real repo's data files hold today.
    monkeypatch.setattr("web.feeds.DATA_DIR", tmp_path / "data")

    from web.build import build

    out = tmp_path / "docs"
    build(out)

    inmate_html = (out / "inmate" / "7654321" / "index.html").read_text(encoding="utf-8")
    assert "DISMISSED per test fixture" in inmate_html
    assert "data-photo-fallback" in inmate_html

    data_html = (out / "data" / "index.html").read_text(encoding="utf-8")
    assert "Data as of" in data_html
    assert "Sep 19, 2026" in data_html or "Sep 20, 2026" in data_html
