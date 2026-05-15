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
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
API = "https://www.courtlistener.com/api/rest/v4/search/"
UA = "JCStream/1.0 (contact via github.com/AICincy/JCStream)"

# Strip a trailing alpha-numeric suffix so "2925.11A" and "2913.02A1" group
# with their base section. This mirrors scraper/orc.py:normalize_code.
_SUFFIX_RE = re.compile(r"[A-Z]\d*$")


def _normalize(code: str) -> str:
    code = (code or "").strip().upper()
    if not code or code in ("NONE", "OTHER"):
        return ""
    return _SUFFIX_RE.sub("", code)


def top_codes(limit: int = 30) -> list[str]:
    raw = json.loads((DATA / "current.json").read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for inm in raw.get("inmates", []):
        for ch in inm.get("charges", []):
            code = _normalize(ch.get("orc_code") or "")
            if code:
                counts[code] += 1
    return [c for c, _ in counts.most_common(limit)]


def fetch_for_code(code: str, max_results: int = 3) -> list[dict]:
    params = {
        "type": "o",
        "q": f'"{code}"',
        "court": "ohio ohioctapp",
        "stat_Published": "true",
        "order_by": "dateFiled desc",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    out = []
    for hit in payload.get("results", [])[:max_results]:
        cites = hit.get("citation") or []
        rel = hit.get("absolute_url") or ""
        out.append({
            "case_name": hit.get("caseName") or hit.get("caseNameFull") or "",
            "court": hit.get("court_citation_string") or hit.get("court") or "",
            "date_filed": hit.get("dateFiled") or "",
            "citation": cites[0] if cites else "",
            "neutral_cite": hit.get("neutralCite") or "",
            "url": ("https://www.courtlistener.com" + rel) if rel else "",
        })
    return out


def main() -> int:
    codes = top_codes(limit=30)
    print(f"refreshing case law for {len(codes)} ORC sections")
    by_code: dict[str, list[dict]] = {}
    for i, code in enumerate(codes, 1):
        try:
            hits = fetch_for_code(code)
            by_code[code] = hits
            print(f"  [{i:>2}/{len(codes)}] {code:10s}  {len(hits)} opinion(s)")
        except Exception as e:
            print(f"  [{i:>2}/{len(codes)}] {code:10s}  ERROR: {e}", file=sys.stderr)
            by_code[code] = []
        time.sleep(0.5)
    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "CourtListener REST API v4 (Ohio appellate courts, published opinions only)",
        "by_code": by_code,
    }
    target = DATA / "orc_caselaw.json"
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size:,} bytes, {sum(len(v) for v in by_code.values())} total opinions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
