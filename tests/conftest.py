"""Shared fixtures.

The hash-chained evidence logs (data/waf_block_log.json, data/pra_requests.json)
are court-evidence files. Several production functions write to them via
module-level default paths, so any test that exercises those paths from the
repo root would append fixture rows to the real logs. The autouse fixture
below redirects both logs to tmp_path for every test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_evidence_logs(tmp_path, monkeypatch):
    from scraper import pra, pra_capias, pra_log, store, sweep

    monkeypatch.setattr(sweep, "WAF_BLOCK_LOG_PATH", tmp_path / "waf_block_log.json")
    # Note: store.WAF_BLOCK_LOG_PATH is NOT patched here on purpose. Its
    # consumers bind it as a def-time default, so an attribute patch does not
    # reach them and only desynchronizes tests that isolate via chdir.
    # Instead, wrap store.append_block_evidence so calls that omit the path
    # (parsers._record_empty_photo_event does) land in tmp_path. Explicit
    # paths pass through untouched.
    _real_append = store.append_block_evidence

    def _append_evidence_to_tmp(record, path=None):
        _real_append(record, path if path is not None else tmp_path / "waf_block_log.json")

    monkeypatch.setattr(store, "append_block_evidence", _append_evidence_to_tmp)

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

    # append_pra_record's default path is bound at import time, so patching
    # the PRA_LOG_PATH constant is not enough; wrap the call in the modules
    # that imported it.
    pra_path = tmp_path / "pra_requests.json"
    monkeypatch.setattr(pra_log, "PRA_LOG_PATH", pra_path)

    def _append_to_tmp(record, path=None):
        pra_log.append_pra_record(record, pra_path)

    monkeypatch.setattr(pra, "append_pra_record", _append_to_tmp)
    monkeypatch.setattr(pra_capias, "append_pra_record", _append_to_tmp)
