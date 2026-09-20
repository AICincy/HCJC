"""Dispatch-point extraction for the homepage map.

Extracted from ``web/build.py`` to keep each module under one concern.
"""

from __future__ import annotations

import logging

log = logging.getLogger("jcstream.site")


def _dispatch_points(cfs_rows: list[dict], shooting_rows: list[dict], limit: int = 600) -> list[dict]:
    """Geocoded points for the homepage map: recent CPD arrest/citation/report
    dispatches plus reported shootings that carry coordinates.

    Compact keys keep dispatches.json small: la/lo (lat/lon), k (kind:
    'cfs'|'shooting'), d (disposition/type), a (address/block), n (neighborhood),
    t (timestamp as the source prints it).
    """

    def _coord(row: dict) -> tuple[float, float] | None:
        lat_raw = row.get("latitude_x")
        lon_raw = row.get("longitude_x")
        if lat_raw is None or lon_raw is None:
            return None
        try:
            la = float(lat_raw)
            lo = float(lon_raw)
        except (TypeError, ValueError):
            return None
        # Greater-Cincinnati sanity box — drops 0,0 and obviously bad rows.
        if not (38.0 < la < 40.0 and -85.5 < lo < -83.5):
            return None
        return (round(la, 5), round(lo, 5))

    cfs_pts: list[dict] = []
    for r in cfs_rows:
        c = _coord(r)
        if not c:
            continue
        cfs_pts.append(
            {
                "la": c[0],
                "lo": c[1],
                "k": "cfs",
                "d": str(r.get("disposition_text") or "").strip(),
                "a": str(r.get("address_x") or "").strip(),
                "n": str(r.get("cpd_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                "t": str(r.get("create_time_incident") or "").strip(),
            }
        )
    shooting_pts: list[dict] = []
    for r in shooting_rows:
        c = _coord(r)
        if not c:
            continue
        shooting_pts.append(
            {
                "la": c[0],
                "lo": c[1],
                "k": "shooting",
                "d": str(r.get("type") or "SHOOTING").strip() or "SHOOTING",
                "a": str(r.get("streetblock") or "").strip(),
                "n": str(r.get("sna_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                "t": str(r.get("datetimeoccured") or r.get("dateoccurred") or "").strip(),
            }
        )
    # Interleave the feeds so the point cap cannot starve either one: a heavy
    # CFS feed used to crowd every shooting point out of the map. Deterministic
    # (CFS first in each pair); order within each feed is preserved.
    pts: list[dict] = []
    for i in range(max(len(cfs_pts), len(shooting_pts))):
        if i < len(cfs_pts):
            pts.append(cfs_pts[i])
        if i < len(shooting_pts):
            pts.append(shooting_pts[i])
    return pts[:limit]
