"""List sweep and list page fetching helpers."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from ..client import DEFAULT_CONCURRENCY, HcsoClient
from ..models import ListRow, utcnow_iso
from ..parsers import parse_list_page
from ..sweep_guards import list_response_looks_blocked

log = logging.getLogger("jcstream.sweep")

SEARCH_PATH = "/justice-center-services/inmate-search/"
_SENSITIVE_HEADERS = frozenset({"cookie", "set-cookie", "authorization", "proxy-authorization"})


def _redact_headers(headers: httpx.Headers) -> dict:
    """Copy request/response headers for the evidence log, replacing the value
    of any session or credential header with a placeholder. Preserves the presence of
    the header (forensically useful) but redacts values before writing to log."""
    return {k: ("[redacted]" if k.lower() in _SENSITIVE_HEADERS else v) for k, v in headers.items()}


def _forensic_sample(resp: httpx.Response) -> dict:
    """Forensic snapshot of a WAF-block response for the evidence log."""
    body = resp.content or b""
    body_text = (resp.text or "")[:1000]
    body_text = re.sub(r"[0-9a-fA-F]{32,}", "[redacted-token]", body_text)
    sample: dict = {
        "captured_utc": utcnow_iso(),
        "status": resp.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "body_sample": body_text,
        "headers": _redact_headers(resp.headers),
    }
    try:
        req = resp.request
    except RuntimeError:
        req = None
    if req is not None:
        sample["request"] = {
            "method": req.method,
            "url": str(req.url),
            "headers": _redact_headers(req.headers),
        }
    return sample


def _fetch_list_page(client: HcsoClient, surname: str) -> tuple[list[ListRow] | None, int | None, dict | None]:
    """Fetch one surname-search page for ``_sweep_list``. Returns
    ``(rows, status, sample)``. ``rows`` is None on a failed fetch.
    """
    try:
        resp = client.get_response(SEARCH_PATH, params={"last": surname})
    except httpx.HTTPStatusError as e:
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, e.response.status_code, _forensic_sample(e.response)
    except Exception as e:
        log.warning("list fetch failed for surname=%s: %s", surname, e)
        return None, None, None
    rows = parse_list_page(resp.text)
    if list_response_looks_blocked(resp.text, rows):
        log.warning(
            "list fetch for surname=%s looks WAF-blocked (HTTP %d, %d bytes, 0 rows)",
            surname,
            resp.status_code,
            len(resp.text),
        )
        return None, resp.status_code, _forensic_sample(resp)
    return rows, None, None


def _sweep_list(client: HcsoClient, surnames: list[str]) -> tuple[list[ListRow], int, dict[str, int], dict | None]:
    """Parallel surname search across the configured list.

    Returns ``(rows, n_failed, status_counts, block_sample)``.
    """
    aggregated: list[ListRow] = []
    seen: set[str] = set()
    failed = 0
    status_counts: dict[str, int] = {}
    block_sample: dict | None = None
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
        futures = {pool.submit(_fetch_list_page, client, s): s for s in surnames}
        for future in as_completed(futures):
            rows, status, sample = future.result()
            if block_sample is None and sample is not None:
                block_sample = sample
            if rows is None:
                failed += 1
                if status is not None:
                    key = str(status)
                    status_counts[key] = status_counts.get(key, 0) + 1
                continue
            for r in rows:
                if r.inmate_number not in seen:
                    seen.add(r.inmate_number)
                    aggregated.append(r)
    elapsed_s = round(time.monotonic() - t0, 2)
    log.info(
        "list phase: %d unique ids, %d/%d failed in %.1fs",
        len(seen),
        failed,
        len(surnames),
        elapsed_s,
    )
    return aggregated, failed, status_counts, block_sample
