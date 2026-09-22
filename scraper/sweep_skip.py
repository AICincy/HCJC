"""Skip-gate for scraper.sweep.run.

Keyed off generated_utc age, not file mtime. A manual refresh or --force
must still scrape even when the snapshot is younger than 20 minutes.
"""

from __future__ import annotations

import os

MIN_SWEEP_INTERVAL_S = 20 * 60


def should_skip_sweep(
    stale_seconds: float | None,
    *,
    refresh_known: bool = False,
    force: bool = False,
    min_interval_s: int = MIN_SWEEP_INTERVAL_S,
) -> bool:
    if refresh_known or force:
        return False
    if os.environ.get("JCSTREAM_FORCE_SWEEP") == "1":
        return False
    if stale_seconds is None:
        return False
    return stale_seconds < min_interval_s
