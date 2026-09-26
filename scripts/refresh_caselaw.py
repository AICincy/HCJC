#!/usr/bin/env python3
"""Refresh data/orc_caselaw.json with recent Ohio appellate opinions citing
each ORC code on the current roster.

Run manually or on a separate (e.g. weekly) cron - NOT inside the 30-minute
sweep. CourtListener's public REST API is rate-limited (60 req/min for
unauthenticated traffic) and ORC sections do not change often enough to
justify per-sweep refresh.

Output schema:
    {
      "generated_utc": "2026-05-14T23:30:00Z",
      "by_code": {
        "2913.02": [
          {"case_name": ..., "court": ..., "date_filed": ...,
           "citation": ..., "neutral_cite": ..., "url": ...}
        ],
        ...
      }
    }

The build (web/build.py) reads this cache; if absent or malformed, the
statute page renders without the case-law block. Failure mode is silent.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Keep this script self-contained for GitHub Actions: it runs in a fresh venv
# created from requirements.txt and should not depend on repo-internal modules
# being importable as packages.
DEFAULT_UA = "HCJC-caselaw-refresh/1.0 (https://github.com/AICincy/HCJC; weekly refresh workflow)"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://www.courtlistener.com/api/rest/v4/search/"

# Per-request budget. The previous 30s timeout times three retries plus the
# 1.5s inter-code sleep can blow a 10-minute Actions job on a slow search.
REQUEST_TIMEOUT = httpx.Timeout(12.0, connect=8.0)
DEFAULT_BUDGET_SECONDS = 1200
THROTTLE_SECONDS = 1.5

sys.path.append(str(ROOT))
from scraper.orc import normalize_code  # noqa: E402


def _normalize(code: str | None) -> str:
    return normalize_code(code or "")


def _budget_seconds() -> float:
    raw = os.environ.get("CASELAW_BUDGET_SECONDS", str(DEFAULT_BUDGET_SECONDS))
    try:
        return max(30.0, float(raw))
    except ValueError:
        return float(DEFAULT_BUDGET_SECONDS)


def load_existing_cache(path: Path | None = None) -> dict[str, list[dict]]:
    target = path or (DATA / "orc_caselaw.json")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    by_code = raw.get("by_code") if isinstance(raw, dict) else None
    if not isinstance(by_code, dict):
        return {}
    out: dict[str, list[dict]] = {}
    for code, hits in by_code.items():
        if isinstance(hits, list):
            out[str(code)] = hits
    return out


def write_cache(by_code: dict[str, list[dict]], path: Path | None = None) -> Path:
    target = path or (DATA / "orc_caselaw.json")
    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "CourtListener REST API v4 (Ohio appellate courts, published opinions only)",
        "by_code": by_code,
    }
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def top_codes(limit: int = 30) -> list[str]:
    raw = json.loads((DATA / "current.json").read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for inm in raw.get("inmates") or []:
        for ch in inm.get("charges", []):
            code = _normalize(ch.get("orc_code") or "")
            if code:
                counts[code] += 1
    return [c for c, _ in counts.most_common(limit)]


def fetch_for_code(
    code: str,
    max_results: int = 3,
    max_retries: int = 3,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Fetch case law for a code with exponential backoff retry on 429."""
    params = {
        "type": "o",
        "q": f'"{code}"',
        "court": "ohio ohioctapp",
        "stat_Published": "on",
        "order_by": "dateFiled desc",
    }
    headers = {"User-Agent": DEFAULT_UA}

    own_client = client is None
    session = client or httpx.Client(timeout=REQUEST_TIMEOUT, headers=headers)
    try:
        for attempt in range(max_retries):
            try:
                r = session.get(API, params=params)
                r.raise_for_status()
                payload = r.json()
                out = []
                for hit in payload.get("results", [])[:max_results]:
                    cites = hit.get("citation") or []
                    rel = hit.get("absolute_url") or ""
                    out.append(
                        {
                            "case_name": hit.get("caseName") or hit.get("caseNameFull") or "",
                            "court": hit.get("court_citation_string") or hit.get("court") or "",
                            "date_filed": hit.get("dateFiled") or "",
                            "citation": cites[0] if cites else "",
                            "neutral_cite": hit.get("neutralCite") or "",
                            "url": ("https://www.courtlistener.com" + rel) if rel else "",
                        }
                    )
                return out
            except httpx.HTTPError as e:
                is_429 = isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429
                is_request_error = isinstance(e, httpx.RequestError)
                if (is_429 or is_request_error) and attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    backoff = 2 ** (attempt + 1)
                    print(f"    network error or rate limit ({e}), retrying in {backoff}s...", file=sys.stderr)
                    time.sleep(backoff)
                else:
                    raise
    finally:
        if own_client:
            session.close()

    # If all retries exhausted without a successful return, return empty list
    # so the caller receives a consistent `list[dict]` result and mypy is
    # satisfied that all code paths return the annotated type.
    return []


def main() -> int:
    try:
        codes = top_codes(limit=30)
    except FileNotFoundError:
        print(f"error: {DATA / 'current.json'} not found; run the roster sweep first", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"error: {DATA / 'current.json'} is not valid JSON ({e})", file=sys.stderr)
        return 2
    print(f"refreshing case law for {len(codes)} ORC sections")
    by_code = load_existing_cache()
    deadline = time.monotonic() + _budget_seconds()
    headers = {"User-Agent": DEFAULT_UA}
    with httpx.Client(timeout=REQUEST_TIMEOUT, headers=headers) as client:
        for i, code in enumerate(codes, 1):
            remaining = deadline - time.monotonic()
            if remaining < 20:
                print(
                    f"  budget exhausted with {len(codes) - i + 1} section(s) left; keeping prior cache",
                    file=sys.stderr,
                )
                break
            try:
                hits = fetch_for_code(code, client=client)
                by_code[code] = hits
                print(f"  [{i:>2}/{len(codes)}] {code:10s}  {len(hits)} opinion(s)")
            except Exception as e:
                print(f"  [{i:>2}/{len(codes)}] {code:10s}  ERROR: {e}", file=sys.stderr)
                by_code.setdefault(code, [])
            # Throttle between requests to stay well under 60 req/min limit
            time.sleep(THROTTLE_SECONDS)
    target = write_cache(by_code)
    print(f"wrote {target} ({target.stat().st_size:,} bytes, {sum(len(v) for v in by_code.values())} total opinions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
