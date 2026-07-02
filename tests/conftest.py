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
    from scraper import pra, pra_capias, pra_log, sweep

    monkeypatch.setattr(sweep, "WAF_BLOCK_LOG_PATH", tmp_path / "waf_block_log.json")
    # Note: store.WAF_BLOCK_LOG_PATH is NOT patched here on purpose. Its
    # consumers bind it as a def-time default, so an attribute patch does not
    # reach them and only desynchronizes tests that isolate via chdir.

    # append_pra_record's default path is bound at import time, so patching
    # the PRA_LOG_PATH constant is not enough; wrap the call in the modules
    # that imported it.
    pra_path = tmp_path / "pra_requests.json"
    monkeypatch.setattr(pra_log, "PRA_LOG_PATH", pra_path)

    def _append_to_tmp(record, path=None):
        pra_log.append_pra_record(record, pra_path)

    monkeypatch.setattr(pra, "append_pra_record", _append_to_tmp)
    monkeypatch.setattr(pra_capias, "append_pra_record", _append_to_tmp)
