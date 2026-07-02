"""Bond context, peer comparisons, and summation shaping functions."""

from __future__ import annotations

import statistics

from scraper import orc as orc_mod
from scraper.models import Inmate
from web.classify import _DEGREE_RE, _charge_tier, _parse_bond_amount

from .common import RosterIndexes, _cached_offenses

_BOND_DEGREE_ORDER = ("F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM")

# Suppression floor for the bond-disparity page: statutes with fewer current
# bookings than this are omitted entirely, so no row can describe a single
# person's bond.
BOND_DISPARITY_MIN_N = 5


def _bond_disparity(indexes: RosterIndexes, offenses: dict, min_n: int = BOND_DISPARITY_MIN_N) -> list[dict]:
    """Per-statute bond dispersion rows for the /bond-disparity/ page.

    Consumes the pre-built ``bonds_by_code`` arrays (sorted, positive bond
    amounts of each inmate's first-listed charge). Statutes below ``min_n``
    are suppressed. Spread is Q3/Q1 (interquartile ratio); quartiles come
    from ``statistics.quantiles(n=4)``. Rows sort by spread descending,
    ties by sample size.
    """
    rows: list[dict] = []
    for code, vals in indexes.bonds_by_code.items():
        # max(min_n, 2): quantiles needs two points, and a floor below 2
        # would defeat the suppression purpose anyway.
        if len(vals) < max(min_n, 2):
            continue
        q1, med, q3 = statistics.quantiles(vals, n=4)
        rows.append(
            {
                "code": code,
                "title": orc_mod.title_for(code, offenses),
                "degree": orc_mod.degree_for(code, offenses),
                "n": len(vals),
                "min": vals[0],
                "q1": round(q1),
                "median": round(med),
                "q3": round(q3),
                "max": vals[-1],
                "spread": round(q3 / q1, 1) if q1 > 0 else None,
            }
        )
    rows.sort(key=lambda r: (-(r["spread"] or 0.0), -r["n"]))
    return rows


def _bond_primary_code_and_bond(target: Inmate, offenses: dict) -> tuple[str, int | None]:
    """Return (primary_code, my_bond) for target's most severe ORC code."""
    primary = None
    primary_idx = 99
    my_bond = None
    for c in target.charges:
        code = orc_mod.normalize_code((c.orc_code or "").strip())
        if not code or code.upper() == "NONE":
            continue
        m = _DEGREE_RE.search((c.description or "").strip())
        deg = m.group(1) if m else orc_mod.degree_for(code, offenses)
        idx = _BOND_DEGREE_ORDER.index(deg) if deg in _BOND_DEGREE_ORDER else 99
        if idx < primary_idx:
            primary, primary_idx = c, idx
            my_bond = _parse_bond_amount(c.bond_amount)
    if not primary:
        return "", None
    primary_code = orc_mod.normalize_code((primary.orc_code or "").strip())
    return primary_code, my_bond


def _bond_peer_amounts(
    target: Inmate,
    all_inmates: list[Inmate],
    primary_code: str,
    indexes: RosterIndexes | None = None,
) -> list[int]:
    """Return sorted peer bond amounts for the given ORC code."""
    if indexes is not None:
        all_bonds = indexes.bonds_by_code.get(primary_code, [])
        my_bond = _parse_bond_amount(
            next(
                (
                    c.bond_amount
                    for c in target.charges
                    if orc_mod.normalize_code((c.orc_code or "").strip()) == primary_code
                ),
                None,
            )
        )
        if my_bond is not None and my_bond > 0 and my_bond in all_bonds:
            result = list(all_bonds)
            result.remove(my_bond)
            return result
        return list(all_bonds)
    peers: list[int] = []
    for inm in all_inmates:
        if inm.inmate_number == target.inmate_number:
            continue
        for c in inm.charges:
            if orc_mod.normalize_code((c.orc_code or "").strip()) != primary_code:
                continue
            v = _parse_bond_amount(c.bond_amount)
            if v is not None and v > 0:
                peers.append(v)
                break  # one bond per peer for this stat
    peers.sort()
    return peers


def _sorted_pct(values: list[int], p: float) -> int:
    idx = max(0, min(len(values) - 1, int(round((len(values) - 1) * p))))
    return values[idx]


def _bond_context(
    target: Inmate,
    all_inmates: list[Inmate],
    offenses: dict | None = None,
    indexes: RosterIndexes | None = None,
) -> dict | None:
    """Percentile distribution of bond amounts across current peers charged
    under the target inmate's most-severe ORC section. Returns None when there
    aren't enough peers to draw a meaningful distribution (<5)."""
    if offenses is None:
        offenses = _cached_offenses()
    primary_code, my_bond = _bond_primary_code_and_bond(target, offenses)
    if not primary_code:
        return None
    peers = _bond_peer_amounts(target, all_inmates, primary_code, indexes=indexes)
    if len(peers) < 5:
        return None
    p10, p25, p50, p75, p90 = (_sorted_pct(peers, x) for x in (0.10, 0.25, 0.50, 0.75, 0.90))
    my_percentile = None
    if my_bond is not None and my_bond > 0:
        below = sum(1 for v in peers if v < my_bond)
        my_percentile = below / len(peers)
    return {
        "code": primary_code,
        "title": orc_mod.title_for(primary_code, offenses),
        "min": peers[0],
        "max": peers[-1],
        "p10": p10,
        "p25": p25,
        "p50": p50,
        "p75": p75,
        "p90": p90,
        "peer_count": len(peers),
        "my_bond": my_bond,
        "my_percentile": my_percentile,
    }


def _bond_by_tier(inmate: Inmate, offenses: dict | None = None) -> dict:
    """Sum bond amounts split by charge tier. Returns {felony, misdemeanor, other, total}."""
    if offenses is None:
        offenses = _cached_offenses()
    out = {"felony": 0, "misdemeanor": 0, "other": 0}
    for c in inmate.charges:
        amt = _parse_bond_amount(c.bond_amount)
        if amt is None:
            continue
        ct = _charge_tier(c, offenses)
        key = ct["kind"] if ct else "other"
        out[key] = out.get(key, 0) + amt
    out["total"] = out["felony"] + out["misdemeanor"] + out["other"]
    return {k: (f"${v:,}" if v else "$0") for k, v in out.items()}


def _bond_total(inmate: Inmate) -> str:
    """Sum the inmate's bond amounts where parseable, return a formatted string."""
    total = 0
    for c in inmate.charges:
        total += _parse_bond_amount(c.bond_amount) or 0
    return f"${total:,}" if total else ""
