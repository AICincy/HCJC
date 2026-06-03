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

LOOKUP_PATH = Path(__file__).resolve().parent.parent / "data" / "orc_offenses.json"
_CODE_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")

# Severity order: lower index = more serious.
DEGREE_ORDER = ("F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM")
UNKNOWN = "?"


def _parse_hamco_offenses() -> dict[str, dict]:
    """Parse scraped Clerk of Courts files in HAMCO/ to extract additional offenses."""
    hamco_dir = LOOKUP_PATH.parent.parent / "HAMCO"
    parsed_offenses: dict[str, dict] = {}
    if not hamco_dir.exists():
        return parsed_offenses

    criminal_file = hamco_dir / "www.courtclerk.org_records-search_criminal-case-listings-section-number_.json"
    traffic_file = hamco_dir / "www.courtclerk.org_records-search_traffic-case-listings-section-number_.json"

    line_re = re.compile(r"^([\w.-]+)\s+(?:nbsp;)?(ORCN|CMCN)\s+(.+)$")

    for file_path in (criminal_file, traffic_file):
        if not file_path.exists():
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            markdown = data.get("markdown", "")
            for line in markdown.splitlines():
                line = line.strip()
                m = line_re.match(line)
                if m:
                    raw_code, jurisdiction, desc = m.groups()
                    # Convert dashes in middle of codes to dots to enable normalize_code lookup
                    raw_code_dotted = raw_code.replace("-", ".")
                    norm_code = normalize_code(raw_code_dotted)
                    if not norm_code:
                        continue
                    deg = "MM" if jurisdiction == "CMCN" else "?"
                    desc_clean = desc.strip()
                    if desc_clean:
                        title = desc_clean.capitalize() if desc_clean.isupper() else desc_clean
                        parsed_offenses[norm_code] = {"title": title, "degree": deg}
        except Exception as e:
            log.warning(f"Failed to parse HAMCO file {file_path.name}: {e}")

    return parsed_offenses


@functools.lru_cache(maxsize=1)
def load_offenses(path: Path = LOOKUP_PATH) -> dict[str, dict]:
    """Return ``{normalized_code: {title, degree}}``. Cached: the file is read
    once per process. Templates + helpers call this potentially thousands of
    times per build (once per charge × inmate); without the cache that's
    ~3,500 redundant file reads on a typical roster. If the file changes
    between calls, `load_offenses.cache_clear()` invalidates."""
    offenses = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            offenses.update(raw.get("offenses", {}))
        except Exception as e:
            log.warning(f"Failed to load orc_offenses.json: {e}")

    # Dynamically enrich with HAMCO scraped listings
    try:
        hamco_offenses = _parse_hamco_offenses()
        for code, info in hamco_offenses.items():
            if code not in offenses or not offenses[code].get("title"):
                offenses[code] = info
    except Exception as e:
        log.warning(f"Failed to parse or merge HAMCO offenses: {e}")

    return offenses


def normalize_code(code: str) -> str:
    if not code:
        return ""
    dotted = code.replace("-", ".")
    m = _CODE_RE.search(dotted)
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
    """Return normalized input codes for which there's no title, deduped."""
    if offenses is None:
        offenses = load_offenses()
    seen: set[str] = set()
    missing: list[str] = []
    for c in codes:
        norm = normalize_code(c)
        if norm and not title_for(norm, offenses) and norm not in seen:
            missing.append(norm)
            seen.add(norm)
    return missing
