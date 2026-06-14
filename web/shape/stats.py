"""Statistics calculations, top offenses tracking, and chapter listings."""

from __future__ import annotations

from scraper import orc as orc_mod
from scraper.models import Inmate, Snapshot
from web.classify import _chap_slug, _primary_chapter, _primary_degree
from .common import _cached_offenses


def _tier_breakdown(snapshot: Snapshot, offenses: dict | None = None) -> dict[str, int]:
    """Per-tier (F1..MM, UNK) counts: each inmate's most-severe degree."""
    if offenses is None:
        offenses = _cached_offenses()
    counts: dict[str, int] = {t: 0 for t in ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]}
    counts["UNK"] = 0
    for inm in snapshot.inmates:
        deg = _primary_degree(inm, offenses)
        if deg in counts:
            counts[deg] += 1
        else:
            counts["UNK"] += 1
    return counts


def _top_offenses_with_orc(snapshot: Snapshot, top_n: int = 12, offenses: dict | None = None) -> list[dict]:
    """Top-N ORC sections on the roster, with title + degree + count + share."""
    if offenses is None:
        offenses = _cached_offenses()
    counts: dict[str, int] = {}
    for inm in snapshot.inmates:
        seen: set[str] = set()
        for c in inm.charges:
            code = orc_mod.normalize_code((c.orc_code or "").strip())
            if not code or code.upper() == "NONE" or code in seen:
                continue
            seen.add(code)
            counts[code] = counts.get(code, 0) + 1
    n = max(1, len(snapshot.inmates))
    rows = []
    for code, count in sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]:
        title = orc_mod.title_for(code, offenses) or ""
        deg = orc_mod.degree_for(code, offenses) or "UNK"
        rows.append(
            {
                "code": code,
                "title": title,
                "degree": deg,
                "count": count,
                "pct": 100.0 * count / n,
            }
        )
    return rows


def _all_top_offenses(snapshot: Snapshot, offenses: dict | None = None) -> list[dict]:
    """Like _top_offenses_with_orc but unbounded - used for the statute page."""
    return _top_offenses_with_orc(snapshot, top_n=10_000, offenses=offenses)


def _distinct_chapters(inmates: list[Inmate]) -> list[tuple[str, str]]:
    """Distinct (slug, label) ORC chapters present on the roster, sorted by
    label, for the homepage filter dropdown."""
    chap: dict[str, str] = {}
    for inm in inmates:
        ch = _primary_chapter(inm)
        if ch:
            chap[_chap_slug(ch["label"])] = ch["label"]
    return sorted(chap.items(), key=lambda kv: kv[1])
