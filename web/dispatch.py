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

    pts: list[dict] = []
    for r in cfs_rows:
        c = _coord(r)
        if not c:
            continue
        pts.append(
            {
                "la": c[0],
                "lo": c[1],
                "k": "cfs",
                "d": (r.get("disposition_text") or "").strip(),
                "a": (r.get("address_x") or "").strip(),
                "n": (r.get("cpd_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                "t": (r.get("create_time_incident") or "").strip(),
            }
        )
    for r in shooting_rows:
        c = _coord(r)
        if not c:
            continue
        pts.append(
            {
                "la": c[0],
                "lo": c[1],
                "k": "shooting",
                "d": (r.get("type") or "SHOOTING").strip() or "SHOOTING",
                "a": (r.get("streetblock") or "").strip(),
                "n": (r.get("sna_neighborhood") or r.get("community_council_neighborhood") or "").strip(),
                "t": (r.get("datetimeoccured") or r.get("dateoccurred") or "").strip(),
            }
        )
    return pts[:limit]
