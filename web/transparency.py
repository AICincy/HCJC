"""Aggregate the WAF-block evidence ledger into public scorecard metrics.

Drives the /transparency/ page and the ``data/transparency_metrics.json``
mirror, so the numbers cited in public-records filings regenerate from the
ledger on every build. Read-only over the hash-chained ledger
(``data/waf_block_log.json``): the sweep appends one ``blocked`` record per
degraded cycle and one ``recovered`` record when a healthy sweep closes the
denial period. Other event types sharing the ledger (photo-integrity
observations) do not participate in these metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone

from scraper.sweep_guards import ROSTER_STALE_ALARM_HOURS


def _parse_utc(ts: str | None) -> datetime | None:
    """Parse a ledger/snapshot UTC timestamp (``...Z`` or ISO offset form).
    Returns None when missing or unparseable; naive values are taken as UTC."""
    if not ts:
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_transparency_metrics(
    entries: list[dict],
    generated_utc: str | None,
    now: datetime | None = None,
) -> dict:
    """Scorecard metrics from the in-order ledger ``entries``.

    A denial period runs from the first ``blocked`` record of a run to the
    ``recovered`` record that closes it; a period still open at the end of
    the ledger accrues denied hours up to ``now``. Records with unparseable
    timestamps still count as events but are skipped for duration math.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    blocked = [e for e in entries if e.get("event") == "blocked"]
    first_block_utc = blocked[0].get("timestamp_utc") if blocked else None
    last_block_utc = blocked[-1].get("timestamp_utc") if blocked else None

    current_streak = 0
    longest_streak = 0
    denied_hours = 0.0
    period_start: datetime | None = None
    for e in entries:
        event = e.get("event")
        if event == "blocked":
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
            ts = _parse_utc(e.get("timestamp_utc"))
            if period_start is None and ts is not None:
                period_start = ts
        elif event == "recovered":
            ts = _parse_utc(e.get("timestamp_utc"))
            if period_start is not None and ts is not None:
                denied_hours += max(0.0, (ts - period_start).total_seconds() / 3600)
            period_start = None
            current_streak = 0
    if period_start is not None:
        denied_hours += max(0.0, (now - period_start).total_seconds() / 3600)

    last_block_dt = _parse_utc(last_block_utc)
    days_since_last_block = max(0, int((now - last_block_dt).total_seconds() // 86400)) if last_block_dt else None

    gen_dt = _parse_utc(generated_utc)
    freshness_hours = (now - gen_dt).total_seconds() / 3600 if gen_dt else None

    if freshness_hours is not None and freshness_hours >= ROSTER_STALE_ALARM_HOURS:
        status = "BLOCKED" if current_streak > 0 else "STALE"
    else:
        status = "FRESH"

    return {
        "status": status,
        "total_block_events": len(blocked),
        "first_block_utc": first_block_utc,
        "last_block_utc": last_block_utc,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "denied_hours_total": round(denied_hours, 1),
        "days_since_last_block": days_since_last_block,
        "freshness_hours": round(freshness_hours, 1) if freshness_hours is not None else None,
        "stale_alarm_hours": ROSTER_STALE_ALARM_HOURS,
        "roster_generated_utc": generated_utc,
        "computed_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
