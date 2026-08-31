import json
import os
from pathlib import Path

from web.outputs import _copy_static, _write_manifest, _write_well_known


def test_write_well_known_defaults(tmp_path: Path):
    # Ensure environment is clean of GITHUB_REPOSITORY
    orig_repo = os.environ.get("GITHUB_REPOSITORY")
    if "GITHUB_REPOSITORY" in os.environ:
        del os.environ["GITHUB_REPOSITORY"]
    
    try:
        _write_well_known(tmp_path, "https://test.com", "2026-06-02T20:00:00Z")
        
        # Verify default repo issues link is written
        security_txt = (tmp_path / ".well-known" / "security.txt").read_text(encoding="utf-8")
        assert "Contact: https://github.com/AICincy/HCJC/issues" in security_txt

        humans_txt = (tmp_path / "humans.txt").read_text(encoding="utf-8")
        assert "https://github.com/AICincy/HCJC/issues" in humans_txt
    finally:
        if orig_repo is not None:
            os.environ["GITHUB_REPOSITORY"] = orig_repo


def test_write_well_known_from_env(tmp_path: Path):
    orig_repo = os.environ.get("GITHUB_REPOSITORY")
    os.environ["GITHUB_REPOSITORY"] = "custom-owner/custom-repo"
    
    try:
        _write_well_known(tmp_path, "https://test.com", "2026-06-02T20:00:00Z")
        
        # Verify custom repo issues link is written
        security_txt = (tmp_path / ".well-known" / "security.txt").read_text(encoding="utf-8")
        assert "Contact: https://github.com/custom-owner/custom-repo/issues" in security_txt
        
        humans_txt = (tmp_path / "humans.txt").read_text(encoding="utf-8")
        assert "https://github.com/custom-owner/custom-repo/issues" in humans_txt
    finally:
        if orig_repo is not None:
            os.environ["GITHUB_REPOSITORY"] = orig_repo
        elif "GITHUB_REPOSITORY" in os.environ:
            del os.environ["GITHUB_REPOSITORY"]


def test_copy_static_writes_favicon(tmp_path: Path):
    _copy_static(tmp_path)
    fav = tmp_path / "favicon.ico"
    apple = tmp_path / "apple-touch-icon.png"
    assert fav.is_file() and fav.stat().st_size > 0
    assert apple.is_file() and apple.stat().st_size > 0


def test_manifest_includes_icon(tmp_path: Path):
    _write_manifest(tmp_path, "")
    manifest = json.loads((tmp_path / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["icons"], "manifest must list at least one icon"
    assert manifest["icons"][0]["src"].endswith("/static/img/hcjc-seal-2x.png")
