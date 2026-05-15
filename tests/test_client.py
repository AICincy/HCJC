"""Tests for the HCSO HTTP client retry behavior. Uses MockTransport so no
real network traffic happens."""
from __future__ import annotations

import httpx
import pytest

from scraper import client as client_mod


def _make_client_with_responses(responses):
    """Build an HcsoClient whose transport returns ``responses`` in order."""
    it = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return next(it)

    c = client_mod.HcsoClient(crawl_delay=0.0)
    # Bypass __enter__ wiring up a real transport.
    import threading

    c._lock = threading.Lock()
    c._client = httpx.Client(
        base_url=c.base_url,
        transport=httpx.MockTransport(handler),
    )
    return c


def test_get_returns_body_on_first_try():
    c = _make_client_with_responses([httpx.Response(200, text="hello")])
    try:
        assert c.get("/x") == "hello"
    finally:
        c._client.close()


def test_get_retries_on_5xx_then_succeeds(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: slept.append(s))
    c = _make_client_with_responses([
        httpx.Response(503, text="busy"),
        httpx.Response(200, text="ok"),
    ])
    try:
        assert c.get("/x") == "ok"
    finally:
        c._client.close()
    # Backoff fired exactly once with the first-attempt delay.
    assert slept == [0.5]


def test_get_raises_after_repeated_5xx(monkeypatch):
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    c = _make_client_with_responses([
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(503),
    ])
    try:
        with pytest.raises(httpx.HTTPStatusError):
            c.get("/x")
    finally:
        c._client.close()


def test_get_retries_on_429_honoring_retry_after(monkeypatch):
    # sec-net-F3: 429 must trigger the retry envelope (it didn't before).
    slept: list[float] = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: slept.append(s))
    c = _make_client_with_responses([
        httpx.Response(429, headers={"retry-after": "3"}, text="slow down"),
        httpx.Response(200, text="ok"),
    ])
    try:
        assert c.get("/x") == "ok"
    finally:
        c._client.close()
    # Slept exactly 3 seconds per the Retry-After header (capped at 30).
    assert slept == [3.0]


def test_get_caps_retry_after_at_30_seconds(monkeypatch):
    # sec-net-F3: a misbehaving upstream cannot extend the cron budget
    # indefinitely; Retry-After is capped at RETRY_AFTER_CAP_S.
    slept: list[float] = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: slept.append(s))
    c = _make_client_with_responses([
        httpx.Response(429, headers={"retry-after": "600"}, text="slow down"),
        httpx.Response(200, text="ok"),
    ])
    try:
        assert c.get("/x") == "ok"
    finally:
        c._client.close()
    assert slept == [client_mod.RETRY_AFTER_CAP_S]


def test_get_falls_back_to_one_second_when_retry_after_missing(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: slept.append(s))
    c = _make_client_with_responses([
        httpx.Response(429, text="slow down"),
        httpx.Response(200, text="ok"),
    ])
    try:
        assert c.get("/x") == "ok"
    finally:
        c._client.close()
    assert slept == [1.0]


def test_make_client_respects_env_overrides(monkeypatch):
    # tests-F8: make_client is the seam between local dev and the workflow.
    # A typo in any of the three env vars would silently fall back to default;
    # this test pins the contract.
    monkeypatch.setenv("JCSTREAM_BASE_URL", "https://example.test")
    monkeypatch.setenv("JCSTREAM_USER_AGENT", "TestAgent/1.0")
    monkeypatch.setenv("JCSTREAM_CRAWL_DELAY", "1.5")
    c = client_mod.make_client()
    assert c.base_url == "https://example.test"
    assert c.user_agent == "TestAgent/1.0"
    assert c.crawl_delay == 1.5


def test_make_client_uses_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("JCSTREAM_BASE_URL", raising=False)
    monkeypatch.delenv("JCSTREAM_USER_AGENT", raising=False)
    monkeypatch.delenv("JCSTREAM_CRAWL_DELAY", raising=False)
    c = client_mod.make_client()
    assert c.base_url == client_mod.DEFAULT_BASE
    assert c.user_agent == client_mod.DEFAULT_UA
    assert c.crawl_delay == client_mod.DEFAULT_CRAWL_DELAY
