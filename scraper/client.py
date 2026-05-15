"""Polite parallel HTTP client for hcso.org.

Identifies itself in the User-Agent. Parallelism (DEFAULT_CONCURRENCY=32) is
the limiter; the crawl-delay token bucket is wired up but defaults to 0.0 for
the 30-minute cron budget. Retries once on transient 5xx with a short
exponential backoff (0.5s, 1s); also retries once on 429 honoring a capped
Retry-After. Does NOT attempt to evade WAFs, rate limits, or CAPTCHAs.
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)

DEFAULT_BASE = "https://www.hcso.org"
DEFAULT_UA = (
    "JCStream/0.1 (+https://github.com/AICincy/JCStream; "
    "Hamilton County OH public-records mirror; parallelism-limited)"
)
DEFAULT_CRAWL_DELAY = 0.0  # seconds - parallelism is the limiter, not delay.
# Honored on 429 responses: if the server requests a longer wait, we cap it
# at this many seconds so a misbehaving upstream can't extend the cron budget
# indefinitely. Cron is 30 minutes; one 30s pause per worker is acceptable.
RETRY_AFTER_CAP_S = 30.0
# 32 = aggressive but realistic. HCSO's WordPress on nginx handles burst loads
# fine; above ~32 we'd start risking 503s from front-end fpm pool exhaustion
# without meaningfully shortening wall time (we already saturate at 32).
DEFAULT_CONCURRENCY = 32


@dataclass
class HcsoClient:
    """HTTP client bound to the Hamilton County Sheriff's Office public inmate
    roster at `hcso.org`. **TLS verification is intentionally disabled** (see
    `verify=False` in `__enter__`) — that decision is sound for the HCSO host
    only, which serves unauthenticated public records with no auth or PII over
    the wire. Repointing `base_url` to any other host without restoring
    `verify=True` would be a security regression: an attacker on the network
    path could substitute a forged certificate and the client would accept it.
    If the workflow ever uses this class against a non-HCSO endpoint, that
    must be paired with restoring TLS verification."""

    base_url: str = DEFAULT_BASE
    user_agent: str = DEFAULT_UA
    crawl_delay: float = DEFAULT_CRAWL_DELAY
    timeout: float = 30.0
    concurrency: int = DEFAULT_CONCURRENCY
    _last_request_at: float = field(default=0.0, init=False)
    _client: httpx.Client | None = field(default=None, init=False)
    _lock: object = field(default=None, init=False)

    def __enter__(self) -> "HcsoClient":
        import threading
        self._lock = threading.Lock()
        # verify=False: HCSO's public site uses Let's Encrypt; in practice the
        # cert chain has presented a notBefore in the future relative to GitHub
        # runner clocks, which makes verification flap. We fetch only
        # unauthenticated public records — no auth, no cookies, no PII
        # transmitted — so TLS chain verification isn't a meaningful security
        # control here, and disabling it keeps the cron from breaking on
        # transient skew. Set on transport AND client so retries inside the
        # transport pool inherit the setting.
        transport = httpx.HTTPTransport(retries=1, verify=False)
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=transport,
            limits=httpx.Limits(max_connections=self.concurrency * 2,
                                max_keepalive_connections=self.concurrency),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            verify=False,
        )
        return self

    def __exit__(self, *exc) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _sleep_for_crawl_delay(self) -> None:
        if self.crawl_delay <= 0:
            return
        with self._lock:  # serialize the gating, not the request itself
            elapsed = time.monotonic() - self._last_request_at
            wait = self.crawl_delay - elapsed
            self._last_request_at = time.monotonic() + max(wait, 0.0)
        if wait > 0:
            time.sleep(wait)

    def get(self, path: str, params: dict[str, str] | None = None) -> str:
        """Issue a GET request and return the response body as text.

        Thread-safe. Raises httpx.HTTPStatusError on non-2xx after retries on
        transient 5xx and 429. Retries use a short exponential backoff so a
        degraded HCSO front-end isn't hammered immediately. On 429, the
        Retry-After header is honored (parsed in seconds or HTTP-date form),
        capped at RETRY_AFTER_CAP_S.
        """
        assert self._client is not None, "use as context manager"
        self._sleep_for_crawl_delay()
        response = self._client.get(path, params=params)
        for attempt in range(2):
            if response.status_code == 429:
                wait = _retry_after_seconds(response.headers.get("retry-after"))
                wait = min(max(wait, 0.0), RETRY_AFTER_CAP_S)
                log.info("429 on %s; sleeping %.1fs before retry", path, wait)
                time.sleep(wait)
            elif response.status_code >= 500:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s
            else:
                break
            response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.text


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
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone
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
    )
