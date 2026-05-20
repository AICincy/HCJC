"""Health heuristics and safety guards for the sweep orchestrator.

Separated from ``scraper.sweep`` so threshold edits and orchestration edits
have different cadences. Each guard is a pure function (or near-pure: the
photo prune does filesystem I/O but is keyed only on inputs) over counts;
they are intentionally testable in isolation.

The thresholds in this module are deliberate, documented decisions tuned
against HCSO's real behavior. Do not change them lightly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("jcstream.sweep")

# ===== Roster-freeze alarm =====
# When the list-sweep guard refuses to write (keeping last-good data), the
# roster stops advancing but the workflow still exits 0. If that persists, the
# site silently shows stale data. Past this many hours since the last-good
# snapshot's generated_utc, the degraded-sweep log is escalated to a loud,
# greppable alarm so a multi-hour freeze surfaces instead of hiding.
ROSTER_STALE_ALARM_HOURS = 6.0


def roster_stale_hours(generated_utc: str | None) -> float | None:
    """Hours since a roster snapshot's ``generated_utc``, or None when the
    value is missing or unparseable. Lets the sweep escalate the
    degraded-roster log once the guard has been holding last-good data for an
    extended stretch (see ``ROSTER_STALE_ALARM_HOURS``)."""
    if not generated_utc:
        return None
    ts = generated_utc.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        last = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() / 3600

# ===== List-sweep degradation guards =====
# Reject the cycle (keep last-good roster) when too many surname fetches
# errored or the roster collapsed to less than half of prior. Below the
# bootstrap floor the guard accepts anything (first run, tiny dataset).
SWEEP_MAX_FAILED_FRACTION = 0.10
SWEEP_MIN_ROSTER_FRACTION = 0.5
SWEEP_BOOTSTRAP_FLOOR = 50

# ===== Detail-page watchdog =====
# Soft floors (WARN only): a sample-meaningful drop in named or photo
# extraction logs but does not block. They cover small fluctuations.
DETAIL_WATCHDOG_MIN_SAMPLE = 10
DETAIL_WATCHDOG_NAME_FLOOR = 0.70
DETAIL_WATCHDOG_PHOTO_FLOOR = 0.50
# Hard floors (BLOCK): large sample plus clearly collapsed name rate
# refuses the write so a HCSO detail-page redesign mid-cycle does not
# canonicalize a nameless roster.
DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE = 100
DETAIL_WATCHDOG_BLOCK_NAME_FLOOR = 0.60

# ===== Photo prune safety =====
# A real roster does not churn over half its photos in a single 30-min
# cycle, so a prune that would delete more is more likely a degraded sweep
# that slipped past the list-side guard than a legitimate release wave.
PHOTO_PRUNE_MAX_FRACTION = 0.5


def sweep_looks_healthy(
    prev_count: int, seen_count: int, n_surnames: int, n_failed: int
) -> bool:
    """Heuristic: did the list sweep come back with a believable roster?

    A first/tiny run is always accepted. Otherwise reject if too many surname
    fetches errored, or the roster shrank to less than half of what it was -
    both are symptoms of a degraded sweep rather than real jail churn.
    """
    if prev_count < SWEEP_BOOTSTRAP_FLOOR:
        return True
    if n_surnames > 0 and (n_failed / n_surnames) > SWEEP_MAX_FAILED_FRACTION:
        return False
    if seen_count < SWEEP_MIN_ROSTER_FRACTION * prev_count:
        return False
    return True


def check_detail_watchdog(attempts: int, named: int, with_photo: int) -> bool:
    """Log a WARNING if detail-page parse or photo extraction looks degraded.

    Catches the failure mode where the list sweep stays green but detail-page
    structure has shifted (e.g. HCSO mid-cutover on a new jail-management
    system), so the parser silently produces nameless or photoless records.

    Returns True when the cycle should still write its roster, False when
    the stricter BLOCK pair is breached (large sample + name rate well under
    floor) and the cycle should refuse to canonicalize.
    """
    if attempts < DETAIL_WATCHDOG_MIN_SAMPLE:
        return True
    name_rate = named / attempts
    photo_rate = with_photo / attempts
    if name_rate < DETAIL_WATCHDOG_NAME_FLOOR:
        log.warning(
            "detail watchdog: only %d/%d (%.0f%%) parsed a name - HCSO detail "
            "page structure may have changed; check scraper/parsers.py",
            named, attempts, 100 * name_rate,
        )
    if photo_rate < DETAIL_WATCHDOG_PHOTO_FLOOR:
        log.warning(
            "detail watchdog: only %d/%d (%.0f%%) yielded a photo - HCSO may "
            "have changed the inline-image embedding; check scraper/parsers.py",
            with_photo, attempts, 100 * photo_rate,
        )
    if (
        attempts >= DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE
        and name_rate < DETAIL_WATCHDOG_BLOCK_NAME_FLOOR
    ):
        log.error(
            "detail watchdog BLOCK: %d/%d (%.0f%%) named at >= %d attempts; "
            "refusing this cycle's write to keep last-good roster in place",
            named, attempts, 100 * name_rate, DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE,
        )
        return False
    return True


def prune_photos(photos_dir: Path, active_ids: set[str]) -> None:
    """Remove any photo whose inmate is no longer in the HCSO public roster.

    Skips the cycle entirely if more than ``PHOTO_PRUNE_MAX_FRACTION`` of
    the existing photos would be deleted at once - a real roster does not
    churn that fast, so this is more likely a partial sweep that the
    degraded-roster guard already let through on bootstrap than legitimate
    releases.
    """
    if not photos_dir.exists():
        return
    existing = list(photos_dir.glob("*.jpg"))
    if not existing:
        return
    doomed = [f for f in existing if f.stem not in active_ids]
    if doomed and len(doomed) / len(existing) > PHOTO_PRUNE_MAX_FRACTION:
        log.error(
            "photo prune would remove %d/%d photos (>%.0f%%) - skipping prune; "
            "this is usually a degraded sweep, not a real release wave",
            len(doomed), len(existing), PHOTO_PRUNE_MAX_FRACTION * 100,
        )
        return
    for f in doomed:
        f.unlink()
    if doomed:
        log.info("pruned %d released-inmate photos", len(doomed))
