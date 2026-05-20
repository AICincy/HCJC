"""Smoke tests for the generic Cincinnati Open Data client.

These don't hit the network — they verify URL/param construction so the
GH Actions workflow can't silently regress.
"""

import json
import logging
import urllib.parse

from scraper.cincy_open import (
    dumps_rows_per_line,
    prev_row_count,
    resource_url,
    since_iso,
    warn_on_row_drop,
)


def test_resource_url_format():
    assert resource_url("qiik-bpks") == "https://data.cincinnati-oh.gov/resource/qiik-bpks.json"


def test_since_iso_is_naive_utc_timestamp():
    s = since_iso(hours=24)
    # Must be parseable by Socrata as a floating timestamp.
    assert "T" in s
    assert len(s) == 19  # YYYY-MM-DDTHH:MM:SS


def test_url_encoding_is_compatible_with_socrata():
    # Socrata accepts colons unencoded in $where.
    params = {"$where": "create_time_incident > '2026-05-10T00:00:00'", "$limit": "1"}
    qs = urllib.parse.urlencode(params, safe=":")
    assert "2026-05-10T00:00:00" in qs
    assert "%3A" not in qs  # colons remain literal


def _write_feed(path, row_count, rows=None):
    path.write_text(json.dumps({
        "generated_utc": "2026-05-20T13:39:27Z",
        "dataset_id": "gexm-h6bt",
        "row_count": row_count,
        "rows": rows if rows is not None else [{"i": i} for i in range(row_count)],
    }), encoding="utf-8")


def test_prev_row_count_reads_existing(tmp_path):
    p = tmp_path / "feed.json"
    _write_feed(p, 3230)
    assert prev_row_count(p) == 3230


def test_prev_row_count_none_when_missing_or_malformed(tmp_path):
    assert prev_row_count(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert prev_row_count(bad) is None


def test_warn_on_row_drop_fires_on_collapse(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("PDI CFS", 3230, 100)
    assert any("dropped sharply" in r.message for r in caplog.records)


def test_warn_on_row_drop_silent_on_normal_churn(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("PDI CFS", 3230, 3207)  # the real -23 churn
    assert caplog.records == []


def test_warn_on_row_drop_silent_with_no_prior(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("PDI CFS", None, 0)  # no prior snapshot
    assert caplog.records == []


def test_dumps_rows_per_line_is_valid_and_one_row_per_line():
    payload = {
        "generated_utc": "2026-05-20T13:39:27Z",
        "dataset_id": "gexm-h6bt",
        "row_count": 2,
        "rows": [{"b": 2, "a": 1}, {"a": 3, "b": 4}],
    }
    text = dumps_rows_per_line(payload)
    assert json.loads(text) == payload  # valid, round-trips
    body = [ln for ln in text.splitlines() if ln.startswith("    {")]
    assert len(body) == 2  # one compact line per row
    assert '{"a":1,"b":2}' in body[0]  # keys sorted, no inter-key spaces


def test_dumps_rows_per_line_empty_rows_is_valid():
    payload = {"generated_utc": "2026-05-20T13:39:27Z", "row_count": 0, "rows": []}
    assert json.loads(dumps_rows_per_line(payload)) == payload


def test_warn_on_row_drop_silent_below_min_rows(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("CCA complaints", 30, 1)  # 97% drop, but tiny baseline
    assert caplog.records == []


def test_warn_on_row_drop_fires_at_min_rows_baseline(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("CFS", 111, 0)  # CFS-sized baseline, above the floor
    assert any("dropped sharply" in r.message for r in caplog.records)


def test_warn_on_row_drop_silent_when_prior_is_zero(caplog):
    with caplog.at_level(logging.WARNING):
        warn_on_row_drop("Use of Force", 0, 0)
    assert caplog.records == []
