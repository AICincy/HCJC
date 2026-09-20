"""Shared fixtures.

The hash-chained evidence log (data/waf_block_log.json) is a
court-evidence file. Several production functions write to it via
module-level default paths, so any test that exercises those paths from the
repo root would append fixture rows to the real log. The autouse fixture
below redirects the log to tmp_path for every test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_evidence_logs(tmp_path, monkeypatch):
    from scraper import store, sweep

    monkeypatch.setattr(sweep, "WAF_BLOCK_LOG_PATH", tmp_path / "waf_block_log.json")
    # Note: store.WAF_BLOCK_LOG_PATH is NOT patched here on purpose. Its
    # consumers bind it as a def-time default, so an attribute patch does not
    # reach them and only desynchronizes tests that isolate via chdir.
    # Instead, wrap store.append_block_evidence so calls that omit the path
    # (parsers._record_empty_photo_event does) land in tmp_path. Explicit
    # paths pass through untouched.
    _real_append = store.append_block_evidence

    def _append_evidence_to_tmp(record, *args, **kwargs):
        # Default the evidence-log path to tmp_path, but let explicit callers
        # (positional or keyword) pass through untouched.
        if not args and "path" not in kwargs:
            kwargs["path"] = tmp_path / "waf_block_log.json"
        _real_append(record, *args, **kwargs)

    monkeypatch.setattr(store, "append_block_evidence", _append_evidence_to_tmp)

    # Same treatment for the deduped variant: parsers._record_empty_photo_event
    # calls it without a path, so the dedup check and the append both land in
    # tmp_path under test instead of reading the real 137k-record log.
    _real_append_deduped = store.append_block_evidence_deduped

    def _append_deduped_to_tmp(record, *args, **kwargs):
        if not args and "path" not in kwargs:
            kwargs["path"] = tmp_path / "waf_block_log.json"
        return _real_append_deduped(record, *args, **kwargs)

    monkeypatch.setattr(store, "append_block_evidence_deduped", _append_deduped_to_tmp)

    # Sweep data-file defaults: SweepPaths default_factory and the module-level
    # fallbacks resolve these globals at call time, so patching them removes
    # the reliance on every sweep.run() test remembering its own monkeypatch.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(sweep, "CURRENT_PATH", tmp_path / "current.json")
    monkeypatch.setattr(sweep, "CHANGELOG_PATH", tmp_path / "changelog.json")
    monkeypatch.setattr(sweep, "ANON_CHANGELOG_PATH", tmp_path / "anon_changelog.json")
    # Egress evidence capture makes a live network call and writes
    # data/egress_evidence.json; never allow it under test.
    monkeypatch.delenv("JCSTREAM_CAPTURE_EGRESS", raising=False)

    # httpx.Client() parses proxy env vars at construction (trust_env=True).
    # A sandbox proxy URL with URL-hostile credential characters makes
    # construction raise httpx.InvalidURL before any request is issued, which
    # breaks tests that build real clients (even with mocked transports).
    # The suite is offline by design, so strip proxy config for every test.
    for _proxy_var in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "NO_PROXY",
        "no_proxy",
    ):
        monkeypatch.delenv(_proxy_var, raising=False)
