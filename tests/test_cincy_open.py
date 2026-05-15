"""Smoke tests for the generic Cincinnati Open Data client.

These don't hit the network — they verify URL/param construction so the
GH Actions workflow can't silently regress.
"""

import urllib.parse

from scraper.cincy_open import resource_url, since_iso


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
