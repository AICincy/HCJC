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
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from scraper.models import Inmate, ListRow

log = logging.getLogger("jcstream.sweep")

# ===== Roster-freeze alarm =====
# When the list-sweep guard refuses to write (keeping last-good data), the
# roster stops advancing but the workflow still exits 0. If that persists, the
# site silently shows stale data. Past this many hours since the last-good
# snapshot's generated_utc, the degraded-sweep log is escalated to a loud,
# greppable alarm so a multi-hour freeze surfaces instead of hiding.
ROSTER_STALE_ALARM_HOURS = 6.0

# Removal-SLA warning window. The FCRA-style target is to drop a released
# inmate within ~30 min, but normal effective sweep cadence tops out around
# 45 min, so a 30-min warning would fire on ordinary slightly-slow cycles.
# Past this many hours the roster is stale beyond what normal cadence explains
# (a slipped cron or an early WAF block), so the sweep emits a ::warning
# annotation: earlier, quieter visibility below the 6h freeze issue. It never
# opens an issue, so it cannot spam during a multi-day WAF block.
REMOVAL_SLA_HOURS = 1.0


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


def sweep_looks_healthy(prev_count: int, seen_count: int, n_surnames: int, n_failed: int) -> bool:
    """Heuristic: did the list sweep come back with a believable roster?

    A first/tiny run allows the size floor to be bypassed. However, we still reject
    the cycle if too many surname fetches errored (which indicates a network/WAF block).
    """
    if n_surnames > 0 and (n_failed / n_surnames) > SWEEP_MAX_FAILED_FRACTION:
        return False
    if prev_count < SWEEP_BOOTSTRAP_FLOOR:
        return True
    return seen_count >= SWEEP_MIN_ROSTER_FRACTION * prev_count


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
            named,
            attempts,
            100 * name_rate,
        )
    if photo_rate < DETAIL_WATCHDOG_PHOTO_FLOOR:
        log.warning(
            "detail watchdog: only %d/%d (%.0f%%) yielded a photo - HCSO may "
            "have changed the inline-image embedding; check scraper/parsers.py",
            with_photo,
            attempts,
            100 * photo_rate,
        )
    if attempts >= DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE and name_rate < DETAIL_WATCHDOG_BLOCK_NAME_FLOOR:
        log.error(
            "detail watchdog BLOCK: %d/%d (%.0f%%) named at >= %d attempts; "
            "refusing this cycle's write to keep last-good roster in place",
            named,
            attempts,
            100 * name_rate,
            DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE,
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
            len(doomed),
            len(existing),
            PHOTO_PRUNE_MAX_FRACTION * 100,
        )
        return
    for f in doomed:
        f.unlink()
    if doomed:
        log.info("pruned %d released-inmate photos", len(doomed))


# ===== WAF block detection =====
# Valid HCSO inmate-detail pages are 91-230 KB (2026-05-19 verification). The
# WAF returns truncated/blocked responses well under 5 KB to automated callers,
# and parse_detail_page silently yields an empty Inmate from them.
WAF_BLOCK_MAX_BYTES = 5000


def looks_like_waf_block(html: str, inm: Inmate, photo_bytes: bytes | None, photo_url: str | None) -> bool:
    """True when a detail response has the shape of a WAF block: a tiny body
    that parsed to no name, no charges, and no photo. Pure predicate, extracted
    from _fetch_one so the heuristic that drives the retry/backoff and the
    carry-forward is unit-testable in isolation."""
    return (
        len(html) < WAF_BLOCK_MAX_BYTES
        and not inm.last_name
        and not inm.first_name
        and not inm.charges
        and not photo_bytes
        and not photo_url
    )


def list_response_looks_blocked(html: str, rows: list[ListRow]) -> bool:
    """True when a surname-search response has the shape of a WAF block served
    as HTTP 200: a tiny body that parsed to zero rows. A legitimate no-results
    search still returns the full page chrome (tens of KB), so the size floor
    (``WAF_BLOCK_MAX_BYTES``) discriminates a block stub from a real empty
    result. This is the 200-mode sibling of the 403 path in ``_sweep_list``."""
    return not rows and len(html) < WAF_BLOCK_MAX_BYTES


# ===== Detail-fetch failure taxonomy =====
# Every detail-page fetch ends in exactly one of these modes. The taxonomy
# exists so a degraded HCSO front-end is described precisely (in logs, in the
# evidence record, and in the per-mode failure histogram) instead of collapsing
# to a bare "fetch failed". Modes also drive the retry policy: only modes
# where a retry can plausibly help (transient network, block-shaped bodies)
# are retried, and then exactly once, with the same identity, IP, and crawl
# delay. Nothing here rotates identity, changes headers, or otherwise evades
# a WAF or rate limit.
class DetailFailureMode(str, Enum):
    OK = "ok"
    WAF_BLOCK = "waf_block"  # tiny body + empty parse (false-200 block page)
    ZERO_BYTE = "zero_byte"  # 2xx with an empty body
    TRUNCATED = "truncated"  # 2xx with a suspiciously small non-empty body
    REDIRECT = "redirect"  # landed on an unexpected page (not the detail URL)
    HTTP_404 = "http_404"
    HTTP_429 = "http_429"
    HTTP_5XX = "http_5xx"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    ERROR = "error"  # unexpected exception; not retried


@dataclass(frozen=True)
class DetailOutcome:
    """The classified result of one detail-page fetch (after any retries)."""

    mode: DetailFailureMode
    http_status: int | None = None
    response_bytes: int = 0


def classify_detail_html(
    html: str,
    inm: Inmate,
    photo_bytes: bytes | None,
    photo_url: str | None,
    *,
    final_path: str | None,
    detail_path: str,
) -> DetailFailureMode:
    """Classify a completed (non-exception) detail fetch.

    ``final_path`` is the path of the final response URL after redirects (None
    when the client cannot report it, e.g. the legacy text-only path);
    ``detail_path`` is the expected inmate-detail path. A 2xx is assumed: the
    client raises on non-2xx before parsing, so non-2xx never reaches here.

    Precedence is deliberate: a final-URL path mismatch is definitive
    evidence we did not receive the detail page at all, so it outranks the
    body-shape heuristics (which assume we are on the right page). A
    redirect is not retried in-cycle — the same URL will redirect again —
    but the record is marked stale and re-attempted on the next cycle.
    """
    if final_path is not None and final_path.rstrip("/") != detail_path.rstrip("/"):
        return DetailFailureMode.REDIRECT
    if len(html) == 0:
        return DetailFailureMode.ZERO_BYTE
    if looks_like_waf_block(html, inm, photo_bytes, photo_url):
        return DetailFailureMode.WAF_BLOCK
    if len(html) < WAF_BLOCK_MAX_BYTES:
        # Tiny but parsed to something: not a block stub, but far below the
        # 91-230 KB shape of a valid detail page. Suspicious enough for one
        # bounded retry, not suspicious enough to call a block.
        return DetailFailureMode.TRUNCATED
    return DetailFailureMode.OK


def classify_http_status_error(status_code: int | None) -> DetailFailureMode:
    """Classify an httpx.HTTPStatusError by its status code."""
    if status_code == 404:
        return DetailFailureMode.HTTP_404
    if status_code == 429:
        return DetailFailureMode.HTTP_429
    if status_code is not None and 500 <= status_code < 600:
        return DetailFailureMode.HTTP_5XX
    return DetailFailureMode.ERROR


# ===== Systemic detail-failure guard =====
# The list sweep can be fully green while detail fetches collapse (the
# 2026-09-19 incident: 44/133 detail refreshes failed with 404s and 503s
# while the sweep exited 0). Past this failure fraction over a
# sample-meaningful number of attempts, the cycle is detail-degraded: the
# roster still writes (carry-forward keeps it correct), but the degradation
# is logged as an error, annotated on the workflow run, and recorded as
# durable evidence instead of reporting plain success.
DETAIL_DEGRADED_MIN_SAMPLE = 10
DETAIL_DEGRADED_MAX_FAILURE_FRACTION = 0.25


def check_detail_degraded(attempts: int, failure_counts: dict[str, int]) -> bool:
    """True when detail-page failures look systemic rather than transient.

    ``failure_counts`` maps failure-mode value -> count of fetches whose final
    outcome was that mode (i.e. excluding ``ok``). Below the minimum sample
    the guard stays silent; small refresh batches must not cry wolf.
    """
    n_failed = sum(failure_counts.values())
    if attempts < DETAIL_DEGRADED_MIN_SAMPLE or n_failed == 0:
        return False
    fraction = n_failed / attempts
    if fraction > DETAIL_DEGRADED_MAX_FAILURE_FRACTION:
        log.error(
            "detail degraded: %d/%d (%.0f%%) detail fetches failed %s; "
            "roster kept via carry-forward but this cycle did not refresh",
            n_failed,
            attempts,
            100 * fraction,
            dict(sorted(failure_counts.items())),
        )
        return True
    return False
