"""WAF-block tracking and evidence logging helpers."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..store import WAF_BLOCK_LOG_PATH, append_block_evidence, load_block_log
from ..sweep_guards import roster_stale_hours
from ..models import utcnow_iso

log = logging.getLogger("jcstream.sweep")


def _prev_generated_utc(path: Path) -> str | None:
    """The ``generated_utc`` of the last-good roster file, or None if the file
    is missing/malformed. Used by the freeze alarm to measure how long the
    degraded-roster guard has been holding stale data."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    gen = data.get("generated_utc") if isinstance(data, dict) else None
    # Only a str is usable by roster_stale_hours (which calls .strip()); a
    # malformed non-str generated_utc degrades to None rather than crashing
    # the freeze-alarm path.
    return gen if isinstance(gen, str) else None


@dataclass(frozen=True)
class _BlockObservation:
    """One degraded-sweep observation, bundled so _record_block_evidence takes a
    single cohesive argument. ``block_sample`` is the forensic snapshot of the
    block response (status, body length + SHA-256, body sample, headers)."""

    prev_count: int
    seen_count: int
    n_surnames: int
    n_failed: int
    status_counts: dict[str, int]
    block_sample: dict | None = None


def _record_block_evidence(obs: _BlockObservation, paths: Any = None) -> None:
    """Append a 'blocked' record to the durable WAF-block evidence log when the
    degraded-roster guard fires. Do-not-evade posture: we document the denial
    rather than route around it."""
    if paths is None:
        from ..sweep import SweepPaths
        paths = SweepPaths()
    stale_h = roster_stale_hours(_prev_generated_utc(paths.current_path))
    append_block_evidence(
        {
            "timestamp_utc": utcnow_iso(),
            "event": "blocked",
            "prev_count": obs.prev_count,
            "seen_count": obs.seen_count,
            "surnames_total": obs.n_surnames,
            "surnames_failed": obs.n_failed,
            "failed_fraction": round(obs.n_failed / obs.n_surnames, 4) if obs.n_surnames else 0.0,
            "http_status_counts": obs.status_counts,
            "block_sample": obs.block_sample,
            "roster_stale_hours": round(stale_h, 1) if stale_h is not None else None,
            "note": "HCSO list sweep returned a degraded roster; last-good data kept.",
        },
        paths.waf_block_log_path,
    )


def _record_recovery_if_blocked(seen_count: int, waf_block_log_path: Path | None = None) -> None:
    """If the last evidence entry was 'blocked', append a single 'recovered'
    record so each denial period has a clean end-timestamp. No-op otherwise."""
    if waf_block_log_path is None:
        from ..sweep import WAF_BLOCK_LOG_PATH
        waf_block_log_path = WAF_BLOCK_LOG_PATH
    entries = load_block_log(waf_block_log_path)
    if entries and entries[-1].get("event") == "blocked":
        append_block_evidence(
            {
                "timestamp_utc": utcnow_iso(),
                "event": "recovered",
                "seen_count": seen_count,
                "note": "HCSO list sweep succeeded; automated access restored.",
            },
            waf_block_log_path,
        )


def _record_egress_evidence() -> None:
    """Best-effort: on a block, snapshot the runner egress IP against GitHub's
    published Actions ranges into data/egress_evidence.json, so the record shows
    which source IP HCSO blocked. Gated on JCSTREAM_CAPTURE_EGRESS=1 so it runs
    only in the CI sweep (it makes a network call), not in unit tests. Never
    raises: an egress-lookup failure must not break the sweep."""
    if os.environ.get("JCSTREAM_CAPTURE_EGRESS") != "1":
        return
    try:
        from .. import egress_ip

        rec = egress_ip.write_snapshot()
        log.info(
            "egress evidence captured: runner_ip=%s in_actions_range=%s",
            rec.get("runner_ip"),
            rec.get("runner_ip_in_actions_range"),
        )
    except Exception as e:
        log.warning("egress evidence capture failed (non-fatal): %s", e)


@dataclass
class WafBackoffTracker:
    """Thread-safe WAF-block backoff tracker, instantiated once per sweep run.

    Replaces the prior module-level globals (_waf_block_streak, _waf_block_lock)
    so each run() gets a clean instance and there is no stale-streak window:
    observe() atomically increments the streak AND computes the backoff inside
    the lock, returning the backoff seconds directly.
    """

    _BASE_S: float = 2.0
    _CAP_S: float = 30.0
    _streak: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def observe(self) -> tuple[int, float]:
        """Record a WAF-block-shaped response (thread-safe).

        Returns ``(streak, backoff_seconds)`` computed atomically so the
        caller never acts on a stale streak value.
        """
        with self._lock:
            self._streak += 1
            streak = self._streak
            backoff = min(self._BASE_S * (2 ** (streak - 1)), self._CAP_S)
        return streak, backoff

    def clear(self) -> None:
        """Reset the streak after a successful parse."""
        with self._lock:
            self._streak = 0

    @property
    def streak(self) -> int:
        with self._lock:
            return self._streak
