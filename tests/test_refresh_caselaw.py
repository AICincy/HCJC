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


def test_fetch_for_code_success(monkeypatch):
    import httpx

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "caseName": "State v. Test",
                        "court_citation_string": "1st Dist.",
                        "dateFiled": "2026-05-01",
                        "citation": ["2026-Ohio-1234"],
                        "neutralCite": "2026-Ohio-1234",
                        "absolute_url": "/opinion/123/state-v-test/",
                    }
                ]
            }

    def fake_get(self, url, params=None):
        return FakeResponse()

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    res = rc.fetch_for_code("2925.11")
    assert len(res) == 1
    assert res[0]["case_name"] == "State v. Test"
    assert res[0]["citation"] == "2026-Ohio-1234"
    assert res[0]["url"] == "https://www.courtlistener.com/opinion/123/state-v-test/"


def test_fetch_for_code_retry_on_429_then_success(monkeypatch):
    import httpx

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(rc.time, "sleep", fake_sleep)

    calls = 0

    class FakeResponseSuccess:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    def fake_get(self, url, params=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            req = httpx.Request("GET", url)
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError("Rate Limit", request=req, response=resp)
        return FakeResponseSuccess()

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    res = rc.fetch_for_code("2925.11", max_retries=3)
    assert res == []
    assert calls == 2
    assert sleep_calls == [2]


def test_fetch_for_code_retry_on_request_error_then_success(monkeypatch):
    import httpx

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(rc.time, "sleep", fake_sleep)

    calls = 0

    class FakeResponseSuccess:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": []}

    def fake_get(self, url, params=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            req = httpx.Request("GET", url)
            raise httpx.ConnectTimeout("Connection timed out", request=req)
        return FakeResponseSuccess()

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    res = rc.fetch_for_code("2925.11", max_retries=3)
    assert res == []
    assert calls == 2
    assert sleep_calls == [2]


def test_fetch_for_code_fail_fast_on_500(monkeypatch):
    import httpx
    import pytest

    def fake_get(self, url, params=None):
        req = httpx.Request("GET", url)
        resp = httpx.Response(500, request=req)
        raise httpx.HTTPStatusError("Internal Error", request=req, response=resp)

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        rc.fetch_for_code("2925.11", max_retries=3)


def test_fetch_for_code_max_retries_exhausted(monkeypatch):
    import httpx
    import pytest

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(rc.time, "sleep", fake_sleep)

    def fake_get(self, url, params=None):
        req = httpx.Request("GET", url)
        resp = httpx.Response(429, request=req)
        raise httpx.HTTPStatusError("Rate Limit", request=req, response=resp)

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        rc.fetch_for_code("2925.11", max_retries=3)

    assert len(sleep_calls) == 2  # sleep for 2s, then 4s, third attempt raises without sleeping
    assert sleep_calls == [2, 4]
