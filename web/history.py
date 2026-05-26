"""Roster-size history tracking for the JCStream sparkline / trend display.

Extracted from ``web/build.py`` to keep each module under one concern.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from scraper.models import HistoryRecord, Snapshot

log = logging.getLogger("jcstream.site")


def _update_history(snapshot: Snapshot, booked_24h: int, released_24h: int) -> dict:
    """Append/replace today's roster-size record in data/history.json (committed
    by the cron) and return a small `trend` dict for the homepage:
      {today, yesterday, delta, spark: [counts...], spark_dates: [...]}
    History is a series of *counts*, not of individuals — it doesn't archive
    anyone, so it's consistent with 'we mirror, we don't archive'.
    """
    path = Path("data/history.json")
    # data-F7: validate each record on load via HistoryRecord. A structurally
    # valid but wrong-typed file (e.g. count as a string) would otherwise
    # crash _compute_stats or drive a bogus sparkline. Drop invalid records
    # rather than failing the build; the next write self-heals.
    raw: list[dict] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for entry in data:
                    try:
                        raw.append(HistoryRecord(**entry).model_dump())
                    except Exception as e:
                        log.warning("dropping invalid history.json record %r: %s", entry, e)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("could not read history.json (%s); starting fresh", e)
    hist = raw
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rec = HistoryRecord(
        date=today,
        count=snapshot.inmate_count,
        booked_24h=booked_24h,
        released_24h=released_24h,
    ).model_dump()
    if hist and hist[-1].get("date") == today:
        hist[-1] = rec
    else:
        hist.append(rec)
    hist = hist[-400:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hist, separators=(",", ":")), encoding="utf-8")
    # build the trend
    counts = [h.get("count", 0) for h in hist]
    today_n = counts[-1] if counts else snapshot.inmate_count
    yest_n = counts[-2] if len(counts) >= 2 else None
    spark = hist[-60:]
    last7 = hist[-7:]
    return {
        "today": today_n,
        "yesterday": yest_n,
        "delta": (today_n - yest_n) if yest_n is not None else None,
        "spark": [h.get("count", 0) for h in spark],
        "spark_dates": [h.get("date", "") for h in spark],
        "days_tracked": len(hist),
        "booked_7d": sum(h.get("booked_24h", 0) for h in last7),
        "released_7d": sum(h.get("released_24h", 0) for h in last7),
        "churn_days": len(last7),
    }
