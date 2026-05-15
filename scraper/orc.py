"""Ohio Revised Code offense lookup: title + default degree per ORC section.

`codes.ohio.gov` publishes the canonical text but its robots.txt disallows
all automated access (`User-agent: *  Disallow: /`). We respect that. Statute
titles aren't copyrightable, and degree defaults are our best-effort
classification (the actual degree depends on the subsection / aggravating
factors, which the HCSO booking row doesn't expose). Use as a severity
heuristic, not as adjudication.

Ohio degrees in order of severity:
  F1 > F2 > F3 > F4 > F5 > M1 > M2 > M3 > M4 > MM > unknown
"""

from __future__ import annotations

import functools
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

LOOKUP_PATH = Path("data/orc_offenses.json")
_CODE_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")

# Severity order: lower index = more serious.
DEGREE_ORDER = ("F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM")
UNKNOWN = "?"


@functools.lru_cache(maxsize=1)
def load_offenses(path: Path = LOOKUP_PATH) -> dict[str, dict]:
    """Return ``{normalized_code: {title, degree}}``. Cached: the file is read
    once per process. Templates + helpers call this potentially thousands of
    times per build (once per charge × inmate); without the cache that's
    ~3,500 redundant file reads on a typical roster. If the file changes
    between calls, `load_offenses.cache_clear()` invalidates."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("offenses", {})


def normalize_code(code: str) -> str:
    if not code:
        return ""
    m = _CODE_RE.search(code)
    return m.group(0) if m else ""


def lookup(code: str, offenses: dict[str, dict] | None = None) -> dict:
    """Return ``{title, degree}`` for an ORC code; empty defaults if unknown."""
    if offenses is None:
        offenses = load_offenses()
    norm = normalize_code(code)
    return offenses.get(norm, {"title": "", "degree": UNKNOWN})


def title_for(code: str, offenses: dict[str, dict] | None = None) -> str:
    return lookup(code, offenses).get("title", "")


def degree_for(code: str, offenses: dict[str, dict] | None = None) -> str:
    return lookup(code, offenses).get("degree", UNKNOWN)


def primary_degree(codes: list[str], offenses: dict[str, dict] | None = None) -> str:
    """Return the most severe degree across a list of ORC codes."""
    if offenses is None:
        offenses = load_offenses()
    best_idx = len(DEGREE_ORDER) + 1
    best = UNKNOWN
    for c in codes:
        d = degree_for(c, offenses)
        if d == UNKNOWN:
            continue
        idx = DEGREE_ORDER.index(d) if d in DEGREE_ORDER else best_idx
        if idx < best_idx:
            best_idx = idx
            best = d
    return best


def codes_without_titles(codes: list[str], offenses: dict[str, dict] | None = None) -> list[str]:
    if offenses is None:
        offenses = load_offenses()
    seen: set[str] = set()
    missing: list[str] = []
    for c in codes:
        norm = normalize_code(c)
        if norm and norm not in offenses and norm not in seen:
            missing.append(norm)
            seen.add(norm)
    return missing
