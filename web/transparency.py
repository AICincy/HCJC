"""Aggregate the WAF-block evidence ledger into public scorecard metrics.

Drives the /transparency/ page and the ``docs/data/transparency_metrics.json``
mirror, so the numbers cited in public-records filings regenerate from the
ledger on every build. Read-only over the hash-chained ledger
(``data/waf_block_log.json``): the sweep appends one ``blocked`` record per
degraded list cycle and one ``recovered`` record when a healthy sweep closes
the denial period; detail-phase failures are recorded per inmate as
``detail_page_waf_block`` (deduped per inmate/failure-mode over 24h) and per
sweep as ``detail_degraded`` when systemic. Other event types sharing the
ledger (photo-integrity observations) do not participate in these metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scraper.sweep_guards import ROSTER_STALE_ALARM_HOURS

# Trailing window for detail-denial evidence. Matches the 24h per-inmate
# dedup window in scraper.sweep._record_detail_page_block (M-1): a healthy
# detail phase writes no failure records, so an open detail denial is only
# claimed while failure evidence is fresh.
DETAIL_DENIAL_WINDOW_HOURS = 24.0

# A trailing systemic detail failure at or above this fraction is a full
# denial (BLOCKED); below it the detail phase is DEGRADED. Sustained
# per-inmate blocks below the systemic threshold also read as DEGRADED.
DETAIL_BLOCKED_FRACTION = 0.9


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


def _stamps(recs: list[dict]) -> list[str]:
    """Non-empty ``timestamp_utc`` strings from ledger records, in order."""
    return [ts for e in recs if isinstance((ts := e.get("timestamp_utc")), str) and ts]


def _resolve_now(
    generated_utc: str | None,
    last_healthy_sweep_utc: str | None,
    now: datetime | None,
) -> datetime:
    """Resolve the reference clock for deterministic builds.

    When ``now`` is explicitly supplied (tests, diagnostics) it wins.
    Otherwise the data vintage (``generated_utc``) is the source of truth,
    falling back to ``last_healthy_sweep_utc`` for older snapshots, and only
    finally to wall-clock time. This makes ``transparency_metrics.json`` and
    the transparency page byte-identical for identical inputs, fixing the
    non-deterministic ``computed_utc`` / ``SHA256SUMS`` drift noted in the
    2026-09-24 full-stack audit (Option B: anchor to data vintage).
    """
    if now is not None:
        return now
    for candidate in (generated_utc, last_healthy_sweep_utc):
        parsed = _parse_utc(candidate)
        if parsed is not None:
            return parsed
    return datetime.now(timezone.utc)


def detail_denial_context(entries: list[dict], now: datetime | None = None) -> dict:
    """Detail-retrieval denial state derived from the evidence ledger.

    Read-only. Returns ``status`` (HEALTHY/DEGRADED/BLOCKED), ``open``
    (whether a detail denial period is currently open), ``since_utc`` (first
    ``detail_page_waf_block`` of the open window, falling back to the first
    ``detail_degraded``), totals, and ``last_failure_utc``. Shared by the
    transparency scorecard and the site-wide staleness banner so both read
    the same derivation (precursor of the graded per-source manifest).

    ``now`` is the trailing-window reference. When omitted it defaults to
    wall-clock time for backward compatibility; callers that need deterministic
    builds (``_roster_stale_context`` and ``compute_transparency_metrics``)
    should pass an anchored clock derived from the snapshot vintage.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=DETAIL_DENIAL_WINDOW_HOURS)

    def _in_window(e: dict) -> bool:
        ts = _parse_utc(e.get("timestamp_utc"))
        return ts is not None and ts >= window_start

    degraded = [e for e in entries if e.get("event") == "detail_degraded" and _in_window(e)]
    blocks = [e for e in entries if e.get("event") == "detail_page_waf_block" and _in_window(e)]

    status = "HEALTHY"
    if degraded:
        latest_frac = degraded[-1].get("failure_fraction") or 0.0
        status = "BLOCKED" if latest_frac >= DETAIL_BLOCKED_FRACTION else "DEGRADED"
    elif blocks:
        status = "DEGRADED"

    since_utc = None
    block_stamps = _stamps(blocks)
    if block_stamps:
        since_utc = min(block_stamps)
    else:
        degraded_stamps = _stamps(degraded)
        if degraded_stamps:
            since_utc = min(degraded_stamps)

    all_stamps = _stamps(degraded + blocks)
    last_failure_utc = max(all_stamps) if all_stamps else None

    return {
        "status": status,
        "open": status != "HEALTHY",
        "since_utc": since_utc,
        "total_block_events": sum(1 for e in entries if e.get("event") == "detail_page_waf_block"),
        "total_degraded_events": sum(1 for e in entries if e.get("event") == "detail_degraded"),
        "last_failure_utc": last_failure_utc,
    }


def compute_transparency_metrics(
    entries: list[dict],
    generated_utc: str | None,
    now: datetime | None = None,
    last_healthy_sweep_utc: str | None = None,
) -> dict:
    """Scorecard metrics from the in-order ledger ``entries``.

    A roster denial period runs from the first ``blocked`` record of a run to
    the ``recovered`` record that closes it; a period still open at the end of
    the ledger accrues denied hours up to ``now``. Records with unparseable
    timestamps still count as events but are skipped for duration math.

    Detail-phase denial (``detail_page_waf_block`` / ``detail_degraded``) is
    denial evidence alongside roster-level ``blocked`` records: the overall
    ``status`` is BLOCKED when either channel has an open denial period.

    ``freshness_hours`` measures the last fully healthy sweep
    (``last_healthy_sweep_utc``), falling back to ``generated_utc`` for
    snapshots written before that field existed; ``roster_age_hours`` keeps
    the plain roster-vintage age for comparison.

    Determinism: when ``now`` is omitted the function anchors to
    ``generated_utc`` (or ``last_healthy_sweep_utc``) instead of wall-clock
    time, so identical ledger + snapshot inputs produce identical JSON. This
    is Option B from the audit (anchor to data vintage). Pass an explicit
    ``now`` in tests or when wall-clock semantics are required.
    """
    now = _resolve_now(generated_utc, last_healthy_sweep_utc, now)

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

    detail = detail_denial_context(entries, now=now)
    roster_denial_open = current_streak > 0

    last_block_dt = _parse_utc(last_block_utc)
    days_since_last_block = max(0, int((now - last_block_dt).total_seconds() // 86400)) if last_block_dt else None

    clock_dt = _parse_utc(last_healthy_sweep_utc or generated_utc)
    freshness_hours = (now - clock_dt).total_seconds() / 3600 if clock_dt else None
    gen_dt = _parse_utc(generated_utc)
    roster_age_hours = (now - gen_dt).total_seconds() / 3600 if gen_dt else None

    if roster_denial_open or detail["open"]:
        status = "BLOCKED"
    elif freshness_hours is not None and freshness_hours >= ROSTER_STALE_ALARM_HOURS:
        status = "STALE"
    else:
        status = "FRESH"

    return {
        "status": status,
        "roster_denial_open": roster_denial_open,
        "total_block_events": len(blocked),
        "first_block_utc": first_block_utc,
        "last_block_utc": last_block_utc,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "denied_hours_total": round(denied_hours, 1),
        "days_since_last_block": days_since_last_block,
        "freshness_hours": round(freshness_hours, 1) if freshness_hours is not None else None,
        "roster_age_hours": round(roster_age_hours, 1) if roster_age_hours is not None else None,
        "last_healthy_sweep_utc": last_healthy_sweep_utc or None,
        "detail_status": detail["status"],
        "detail_denial_open": detail["open"],
        "detail_denial_since_utc": detail["since_utc"],
        "total_detail_block_events": detail["total_block_events"],
        "total_detail_degraded_events": detail["total_degraded_events"],
        "last_detail_failure_utc": detail["last_failure_utc"],
        "stale_alarm_hours": ROSTER_STALE_ALARM_HOURS,
        "roster_generated_utc": generated_utc,
        "computed_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
