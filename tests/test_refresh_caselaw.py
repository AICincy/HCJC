"""Tests for the offline logic in scripts/refresh_caselaw.py.

The script's network functions (`fetch_for_code`, `main`) hit the
CourtListener REST API and are integration-only, so they're intentionally
not covered here. The pure code-normalization and the roster-reading
`top_codes` aggregation are covered.
"""
import json

import scripts.refresh_caselaw as rc


def test_normalize_strips_suffix_like_orc():
    assert rc._normalize("2925.11A") == "2925.11"
    assert rc._normalize("2913.02A1") == "2913.02"
    assert rc._normalize("2903.02") == "2903.02"
    assert rc._normalize("  2903.02  ") == "2903.02"
    assert rc._normalize("") == ""
    assert rc._normalize("NONE") == ""
    assert rc._normalize("OTHER") == ""
    assert rc._normalize(None) == ""


def test_top_codes_counts_and_ranks(tmp_path, monkeypatch):
    current = {
        "inmates": [
            {"charges": [{"orc_code": "2913.02A"}, {"orc_code": "2903.02"}]},
            {"charges": [{"orc_code": "2913.02"}, {"orc_code": "NONE"}]},
            {"charges": [{"orc_code": "2913.02"}]},
        ]
    }
    (tmp_path / "current.json").write_text(json.dumps(current), encoding="utf-8")
    monkeypatch.setattr(rc, "DATA", tmp_path)

    codes = rc.top_codes(limit=10)
    # 2913.02 (x3, suffixes normalized together) ranks first; NONE dropped.
    assert codes[0] == "2913.02"
    assert "2903.02" in codes
    assert "" not in codes
