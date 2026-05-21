"""Polite parallel HTTP client for hcso.org.

Identifies itself in the User-Agent. Parallelism (DEFAULT_CONCURRENCY=16)
and a 0.5s crawl-delay together keep the request profile well under HCSO's
WAF tripwires (the 2026-05-19 verification confirmed 32-worker no-delay was
hitting WAF blocks on truncated <5 KB responses). Retries once on transient
5xx with a 0.5s backoff; also retries once on 429 honoring a capped
Retry-After. Does NOT attempt to evade WAFs, rate limits,
or CAPTCHAs.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)

DEFAULT_BASE = "https://www.hcso.org"
DEFAULT_UA = (
    "JCStream/0.1 (+https://github.com/AICincy/JCStream; "
    "Hamilton County OH public-records mirror; parallelism-limited)"
)
DEFAULT_CRAWL_DELAY = 0.5  # seconds between requests per worker; gates the
# minimum spacing the WAF sees from a single IP. Raised from 0.0 on 2026-05-19
# after Claude.ai's HCSO verification confirmed WAF blocks on the no-delay
# 32-worker profile.
# Honored on 429 responses: if the server requests a longer wait, we cap it
# at this many seconds so a misbehaving upstream can't extend the cron budget
# indefinitely. Cron is */15 with a 20-min skip-gate; one 30s pause per worker
# is acceptable.
RETRY_AFTER_CAP_S = 30.0
# 16 (half of the prior 32) trades sweep wall-time for WAF-block reduction.
# HCSO's WordPress on nginx handles 16 concurrent connections without 503s,
# and the lower parallelism keeps us off the WAF's burst-rate heuristic.
DEFAULT_CONCURRENCY = 16


@dataclass
class HcsoClient:
    """HTTP client bound to the Hamilton County Sheriff's Office public inmate
    roster at `hcso.org`."""

    base_url: str = DEFAULT_BASE
    user_agent: str = DEFAULT_UA
    crawl_delay: float = DEFAULT_CRAWL_DELAY
    timeout: float = 30.0
    concurrency: int = DEFAULT_CONCURRENCY
    # Optional egress proxy (HTTP/HTTPS/SOCKS URL). When HCSO's WAF blocks the
    # GitHub Actions runner IP, the operator sets JCSTREAM_HTTP_PROXY to route
    # the HCSO fetches through a different egress. None = direct connection.
    # Scoped to HCSO only; the Socrata open-data feeds use their own client.
    proxy: str | None = None
    _last_request_at: float = field(default=0.0, init=False)
    _client: httpx.Client | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __enter__(self) -> "HcsoClient":
        # Route through the egress proxy when configured (credentials, if any,
        # stay in the env var and are never logged). The proxy is set on the
        # transport so the client's retry pool inherits it.
        if self.proxy:
            log.info("HcsoClient routing HCSO fetches through a configured egress proxy")
        transport = httpx.HTTPTransport(retries=1, proxy=self.proxy)
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=transport,
            limits=httpx.Limits(max_connections=self.concurrency * 2,
                                max_keepalive_connections=self.concurrency,
                                keepalive_expiry=30),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                # Honest browser-shape headers. Some WAFs treat missing
                # connection / upgrade-insecure-requests as a "non-browser"
                # signal even when the rest of the request profile is fine.
                # Sending them costs us nothing and doesn't impersonate
                # (UA still clearly identifies as JCStream/0.1).
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            follow_redirects=True,
        )
        return self

    def __exit__(self, *exc) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _sleep_for_crawl_delay(self) -> None:
        if self.crawl_delay <= 0:
            return
        with self._lock:  # serialize gating AND sleep so concurrent workers
            # cannot all read the same elapsed and burst simultaneously.
            elapsed = time.monotonic() - self._last_request_at
            wait = self.crawl_delay - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def get(self, path: str, params: dict[str, str] | None = None) -> str:
        """Issue a GET request and return the response body as text.

        Thread-safe. Raises httpx.HTTPStatusError on non-2xx after one retry on
        transient 5xx and 429. Uses a 0.5s backoff on 5xx so a degraded HCSO
        front-end isn't hammered immediately. On 429, the Retry-After header
        is honored (parsed in seconds or HTTP-date form), capped at
        RETRY_AFTER_CAP_S.
        """
        return self.get_response(path, params=params).text

    def get_response(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        """Same retry/backoff as ``get``, but return the raised-for-status
        ``httpx.Response`` instead of its text. Callers that need the status +
        headers (e.g. capturing a WAF-block forensic sample from an HTTP 200
        empty-page block) use this; ``get`` wraps it for the text-only path.
        """
        assert self._client is not None, "use as context manager"
        self._sleep_for_crawl_delay()
        response = self._client.get(path, params=params)
        # One inspection pass = at most one retry (429 or 5xx), then
        # raise_for_status below. The single 5xx backoff is 0.5s (attempt=0
        # only). Keep range(1): a higher range would issue additional
        # retries beyond the one this method documents.
        for attempt in range(1):
            if response.status_code == 429:
                wait = _retry_after_seconds(response.headers.get("retry-after"))
                wait = min(max(wait, 0.0), RETRY_AFTER_CAP_S)
                log.info("429 on %s; sleeping %.1fs before retry", path, wait)
                time.sleep(wait)
            elif response.status_code >= 500:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s (attempt=0 only)
            else:
                break
            response = self._client.get(path, params=params)
        response.raise_for_status()
        return response

    def get_bytes(self, url: str) -> bytes:
        """Fetch a URL and return raw bytes. Used for direct photo URLs."""
        assert self._client is not None, "use as context manager"
        self._sleep_for_crawl_delay()
        response = self._client.get(url)
        response.raise_for_status()
        return response.content


def _retry_after_seconds(header_value: str | None) -> float:
    """Parse a Retry-After header value into seconds.

    Accepts either an integer-seconds form or an HTTP-date form. Unknown or
    missing values fall back to 1.0 second so the retry still happens after
    a brief pause.
    """
    if not header_value:
        return 1.0
    try:
        return float(header_value)
    except ValueError:
        pass
    try:
        from datetime import datetime, timezone
        from email.utils import parsedate_to_datetime
        target = parsedate_to_datetime(header_value)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        delta = (target - datetime.now(timezone.utc)).total_seconds()
        return max(delta, 0.0)
    except (TypeError, ValueError):
        return 1.0


def make_client() -> HcsoClient:
    """Factory that respects env-var overrides (used by GH Actions)."""
    return HcsoClient(
        base_url=os.environ.get("JCSTREAM_BASE_URL", DEFAULT_BASE),
        user_agent=os.environ.get("JCSTREAM_USER_AGENT", DEFAULT_UA),
        crawl_delay=float(os.environ.get("JCSTREAM_CRAWL_DELAY", DEFAULT_CRAWL_DELAY)),
        proxy=os.environ.get("JCSTREAM_HTTP_PROXY") or None,
    )
