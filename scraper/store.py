"""JSON persistence + diffing for current-roster snapshots.

JCStream mirrors HCSO's *current* public roster. After every sweep we replace
``data/current.json`` wholesale; we never archive released individuals. The
changelog keeps the last N change events (booked / released / charge-changed)
so the front page can show a live feed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from .diff import diff  # noqa: F401 — re-exported for sweep.py, test_store.py
from .models import (
    SNAPSHOT_SCHEMA_VERSION,
    ChangeEvent,
    Inmate,
    Snapshot,
    utcnow_iso,
)


class SnapshotCorruptError(Exception):
    """Raised when ``data/current.json`` exists but cannot be deserialized.

    Distinct from "file missing" (load_current returns ``{}`` for that case so
    a real bootstrap is still possible). Callers like ``scraper.sweep.run``
    that must NOT canonicalize from a corrupt prior should use
    ``load_current_or_raise`` instead of ``load_current``.
    """


log = logging.getLogger(__name__)

# Phase 9: raised from 500 to 10000. The old 500 cap was a 2024 instinct to
# keep the file under a megabyte; at ~176 bytes/event that lets us run ~8
# days of public activity (~1.7 MB), which makes the RSS streams and the
# homepage feed actually useful for tracking institutional behavior.
# A public-records mirror shouldn't be the bottleneck on how far back the
# public can see.
CHANGELOG_LIMIT = 10000


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via a tmp file + os.replace.

    Prevents a half-written current.json / changelog.json from being published
    if the process is killed mid-write (GH Actions cancel, OOM, etc.). The
    rename is atomic on POSIX.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


# Durable, git-committed record that HCSO's WAF is blocking automated
# public-records access. Each blocked sweep cycle and each recovery is appended
# here, so the denial is preserved as timestamped evidence beyond GitHub
# Actions' ~90-day log retention. Append-only by design: the growing,
# persisting record is the point (ORC 149.43 / mandamus support).
WAF_BLOCK_LOG_PATH = Path("data/waf_block_log.json")


def load_block_log(path: Path = WAF_BLOCK_LOG_PATH) -> list[dict]:
    """Load the append-only WAF-block evidence log. Returns [] when the file is
    missing or unreadable, so a first run or a corrupt file still proceeds."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _record_sha256(record: dict) -> str:
    """Canonical SHA-256 of one log record, for the append-only hash chain."""
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_evidence_lock = threading.Lock()


def _flock_exclusive(fh):
    """Acquire an exclusive advisory file lock (POSIX or Windows)."""
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(fh, fcntl.LOCK_EX)


def _flock_release(fh):
    """Release the advisory file lock."""
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fh, fcntl.LOCK_UN)


def append_block_evidence(record: dict, path: Path = WAF_BLOCK_LOG_PATH) -> None:
    """Append one timestamped record to the WAF-block evidence log (atomic).

    Each record carries ``prev_sha256`` (SHA-256 of the prior record's canonical
    JSON, ``None`` for the first), forming a hash chain so the append-only log
    self-verifies independent of git history.

    Uses both a threading lock and an advisory file lock to prevent TOCTOU
    races from concurrent callers (threads or processes).
    """
    with _evidence_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.touch(exist_ok=True)
        with open(lock_path, "r") as lock_fh:
            _flock_exclusive(lock_fh)
            try:
                entries = load_block_log(path)
                record["prev_sha256"] = _record_sha256(entries[-1]) if entries else None
                entries.append(record)
                _atomic_write_text(path, json.dumps(entries, indent=2) + "\n")
            finally:
                _flock_release(lock_fh)


def verify_block_chain(entries: list[dict]) -> list[str]:
    """Verify the ``prev_sha256`` hash chain over an in-order list of WAF-block
    log records. Returns a list of human-readable problems; an empty list means
    the chain is intact. The first record must carry ``prev_sha256 == None``;
    every later record's ``prev_sha256`` must equal the canonical SHA-256 of the
    record immediately before it. Detects in-place edits and out-of-band record
    removal from the middle of the file; wholesale file deletion is caught by
    git history, not the chain."""
    problems: list[str] = []
    for i, rec in enumerate(entries):
        expected = _record_sha256(entries[i - 1]) if i > 0 else None
        actual = rec.get("prev_sha256")
        if actual != expected:
            problems.append(
                f"record {i} (event={rec.get('event')!r}, "
                f"timestamp_utc={rec.get('timestamp_utc')!r}): "
                f"prev_sha256={actual!r}, expected {expected!r}"
            )
    return problems


def load_current(path: Path) -> dict[str, Inmate]:
    """Load the previous snapshot keyed by inmate_number; empty dict if missing.

    Forgiving variant: corruption or schema mismatch logs an error and falls
    back to ``{}``. ``web/build.py`` uses this so a one-off bad file doesn't
    take the static site down.

    Sweep callers that must NOT canonicalize from a corrupt prior should use
    ``load_current_or_raise`` instead.
    """
    if not path.exists():
        return {}
    try:
        return _load_current_strict(path)
    except SnapshotCorruptError as e:
        log.error("could not deserialize %s (%s): treating as empty", path, e)
        return {}


def load_current_or_raise(path: Path) -> dict[str, Inmate]:
    """Strict variant of :func:`load_current` for the sweep orchestrator.

    Returns an empty dict only when the file is genuinely absent. If the file
    exists but cannot be deserialized (JSON error, schema mismatch, or
    schema_version above the reader's max), raises
    :class:`SnapshotCorruptError`. The sweep then refuses the cycle and the
    last-good file remains in place for human inspection.
    """
    if not path.exists():
        return {}
    return _load_current_strict(path)


def _load_current_strict(path: Path) -> dict[str, Inmate]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SnapshotCorruptError(f"JSON decode error: {e}") from e
    if not isinstance(raw, dict):
        raise SnapshotCorruptError(f"top-level JSON is {type(raw).__name__}, expected object")
    version = raw.get("schema_version", 1)
    if not isinstance(version, int) or version > SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotCorruptError(
            f"snapshot schema_version={version!r} is newer than reader max {SNAPSHOT_SCHEMA_VERSION}"
        )
    try:
        return {i["inmate_number"]: Inmate(**i) for i in raw.get("inmates", [])}
    except (ValidationError, KeyError, TypeError, AttributeError) as e:
        raise SnapshotCorruptError(f"inmate deserialization failed: {e}") from e


def _load_takedowns(data_dir: Path) -> set[str]:
    """Inmate numbers sealed/expunged per ORC 2953.32, read from
    ``<data_dir>/takedowns.json`` (a JSON array of inmate_number strings).

    Returns an empty set when the file is absent or unreadable, so sealing is
    opt-in and never blocks a write. Enforced at the write boundary so a sealed
    number never persists into current.json or the changelog (and therefore not
    into git history going forward), not only the rendered site.
    """
    path = data_dir / "takedowns.json"
    if not path.exists():
        return set()
    try:
        return {str(n) for n in json.loads(path.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        log.warning("could not load %s (%s): no records sealed this cycle", path, e)
        return set()


def save_current(path: Path, inmates: Iterable[Inmate]) -> None:
    # Note: for rosters significantly larger than ~5k, consider streaming
    # serialization to avoid holding the full JSON string in memory.
    sealed = _load_takedowns(path.parent)
    materialized = sorted(
        (i for i in inmates if i.inmate_number not in sealed),
        key=lambda i: (i.last_name, i.first_name, i.inmate_number),
    )
    snapshot = Snapshot(
        generated_utc=utcnow_iso(),
        inmate_count=len(materialized),
        inmates=materialized,
    )
    _atomic_write_text(path, snapshot.model_dump_json(indent=2))


def load_changelog(path: Path) -> list[ChangeEvent]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [ChangeEvent(**e) for e in raw]
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError, AttributeError) as e:
        log.error("could not deserialize %s (%s): treating as empty", path, e)
        return []


def save_changelog(path: Path, events: list[ChangeEvent]) -> None:
    # Stable sort by (timestamp_utc, insertion_index) before trimming so a
    # non-monotonic wall clock (NTP slew, container restart) can't leave the
    # rolling feed out of order. Insertion-order is the tiebreaker, so the
    # diff() emission sequence within a single timestamp is preserved.
    sealed = _load_takedowns(path.parent)
    if sealed:
        events = [e for e in events if e.inmate_number not in sealed]
    indexed = list(enumerate(events))
    indexed.sort(key=lambda iv: (iv[1].timestamp_utc, iv[0]))
    ordered = [e for _, e in indexed]
    trimmed = ordered[-CHANGELOG_LIMIT:]
    _atomic_write_text(
        path,
        json.dumps([e.model_dump() for e in trimmed], indent=2),
    )


# Phase 11: PII expiry window for anon_changelog. Events older than this lose
# their name + inmate_number + booking_number; only event_type + timestamp
# (date-only) + tier + primary_charge_category survive. The rationale: a
# public-records mirror should be able to surface long-term institutional
# patterns ("bookings on Friday vs Tuesday", "F1 share of roster over 6 months")
# without keeping individual records visible after release. Seven days gives
# the rolling RSS streams and homepage feed enough overlap with the live
# changelog to feel continuous, while still expiring identifying info quickly.
ANON_EXPIRY_DAYS = 7
# Compaction horizon: anonymized records older than this are collapsed into
# monthly summary counts (one row per month+event+tier+category). Preserves
# aggregate signal for long-term institutional trend analysis while bounding
# file growth. At ~30-min cron cadence, 365 days ≈ 17k raw anon rows before
# compaction; afterwards each month compresses to a handful of summary rows.
ANON_COMPACTION_MAX_DAYS = 365
# Hard cap on anon_changelog.json entries after compaction. At ~30-min cadence,
# 365 days produces ~17k raw rows pre-compaction; after compaction each month
# collapses to a handful of summary rows. 50k allows ~2-3 years of data with
# room for recent un-compacted entries (~400 bytes/row → ~20 MB worst case).
ANON_CHANGELOG_LIMIT = 50000


def _anonymize_event(e: dict, charge_lookup: dict[str, dict] | None = None) -> dict:
    """Return a PII-stripped copy of a changelog event row.

    Keeps: event type, date (day only, not minute), tier if known, primary
    charge category if known. Drops: name, inmate_number, booking_number,
    bond, court_date, anything that could re-identify."""
    ts = e.get("timestamp_utc") or ""
    return {
        "event": e.get("event"),
        "date": ts[:10] if ts else None,
        "tier": e.get("primary_tier"),
        "category": e.get("primary_category"),
    }


def _anon_dedup_key(row: dict) -> tuple:
    """Content key for anon-changelog dedup, branching on row shape so a
    re-emitted row matches its stored twin. Recent rows carry a full
    timestamp_utc + inmate_number; anonymized rows carry only a day-level
    date + tier + category. Keying both with one uniform shape (the prior
    bug) meant recent rows never matched and accumulated a duplicate every
    sweep until they aged out."""
    if row.get("timestamp_utc"):
        return ("full", row.get("event"), row.get("timestamp_utc"), row.get("inmate_number"))
    return ("anon", row.get("event"), row.get("date"), row.get("tier"), row.get("category"))


def _compact_anon_entries(entries: list[dict]) -> list[dict]:
    """Compact old anonymized records into monthly summary counts.

    Records newer than ``ANON_COMPACTION_MAX_DAYS`` pass through unchanged.
    Older records are grouped by (year-month, event type, tier, category) and
    replaced with a single summary dict per group carrying a ``count``.
    Already-compacted summary rows (``event_summary: True``) are merged into
    the same grouping so re-runs are idempotent.
    """
    from collections import Counter
    from datetime import datetime, timedelta, timezone

    compact_cutoff = (datetime.now(timezone.utc) - timedelta(days=ANON_COMPACTION_MAX_DAYS)).strftime("%Y-%m-%d")

    recent: list[dict] = []
    old_groups: Counter = Counter()

    for row in entries:
        if row.get("event_summary"):
            month = row.get("month")
            count = row.get("count", 1)
        else:
            ts = row.get("timestamp_utc") or row.get("date") or ""
            date_str = ts[:10] if ts else ""
            if not date_str or date_str >= compact_cutoff:
                recent.append(row)
                continue
            month = date_str[:7]
            count = 1
        key = (month, row.get("event"), row.get("tier"), row.get("category"))
        old_groups[key] += count

    summaries: list[dict] = []
    for (month, event, tier, category), count in sorted(old_groups.items()):
        summaries.append(
            {
                "event_summary": True,
                "month": month,
                "event": event,
                "tier": tier,
                "category": category,
                "count": count,
            }
        )

    return summaries + recent


def save_anon_changelog(
    path: Path,
    full_events: list[ChangeEvent],
    enrichment: dict[str, dict] | None = None,
) -> None:
    """Maintain ``data/anon_changelog.json``: rolling all-time append-only
    log where any event older than ``ANON_EXPIRY_DAYS`` has been stripped of
    identifying information.

    Strategy:
      1. Read the existing anon file (already-anonymized older events).
      2. For each event in the live ``full_events`` argument:
           - If newer than the expiry cutoff, keep PII for now.
           - If older, anonymize before merging.
      3. Stable-dedupe by a content key (event + timestamp + inmate hash
         within retention, or just event + date + tier + category for older
         rows).
      4. Write back, capped at ANON_CHANGELOG_LIMIT (oldest summaries dropped first).

    The enrichment dict, if provided, maps inmate_number -> {tier, category}
    derived from current.json at sweep time so we can anonymize without
    losing the aggregate signal.
    """
    enrichment = enrichment or {}
    # Read existing anon entries
    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except (json.JSONDecodeError, OSError):
            existing = []

    # Determine cutoff
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=ANON_EXPIRY_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build a set of (event, timestamp_utc) keys already in existing so we
    # don't double-add when a sweep re-emits the same row.
    seen_keys: set[tuple] = set()
    for row in existing:
        if isinstance(row, dict):
            seen_keys.add(_anon_dedup_key(row))

    out = list(existing)
    for ce in full_events:
        d = ce.model_dump() if hasattr(ce, "model_dump") else dict(ce)
        # enrich from current.json at this moment if we have it
        enr = enrichment.get(d.get("inmate_number") or "", {})
        d.setdefault("primary_tier", enr.get("tier"))
        d.setdefault("primary_category", enr.get("category"))

        if (d.get("timestamp_utc") or "") < cutoff:
            row = _anonymize_event(d)
        else:
            row = {
                "event": d.get("event"),
                "timestamp_utc": d.get("timestamp_utc"),
                "inmate_number": d.get("inmate_number"),
                "name": d.get("name"),
                "tier": d.get("primary_tier"),
                "category": d.get("primary_category"),
                "note": d.get("note"),
            }
        key = _anon_dedup_key(row)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append(row)

    # Re-anonymize any retained rows that have crossed the expiry boundary.
    for i, row in enumerate(out):
        if "timestamp_utc" in row and row["timestamp_utc"] and row["timestamp_utc"] < cutoff:
            out[i] = _anonymize_event(
                {
                    "event": row.get("event"),
                    "timestamp_utc": row.get("timestamp_utc"),
                    "primary_tier": row.get("tier"),
                    "primary_category": row.get("category"),
                }
            )

    # Stable sort by date/timestamp, oldest first for append-only feel
    out.sort(key=lambda r: r.get("timestamp_utc") or r.get("date") or "")
    out = _compact_anon_entries(out)
    if len(out) > ANON_CHANGELOG_LIMIT:
        out = out[-ANON_CHANGELOG_LIMIT:]
    _atomic_write_text(path, json.dumps(out, indent=2))



