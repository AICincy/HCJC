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
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

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


def append_block_evidence(record: dict, path: Path = WAF_BLOCK_LOG_PATH) -> None:
    """Append one timestamped record to the WAF-block evidence log (atomic).

    Each record carries ``prev_sha256`` (SHA-256 of the prior record's canonical
    JSON, ``None`` for the first), forming a hash chain so the append-only log
    self-verifies independent of git history.
    """
    entries = load_block_log(path)
    record["prev_sha256"] = _record_sha256(entries[-1]) if entries else None
    entries.append(record)
    _atomic_write_text(path, json.dumps(entries, indent=2) + "\n")


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
        raise SnapshotCorruptError(
            f"top-level JSON is {type(raw).__name__}, expected object"
        )
    version = raw.get("schema_version", 1)
    if not isinstance(version, int) or version > SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotCorruptError(
            f"snapshot schema_version={version!r} is newer than reader max "
            f"{SNAPSHOT_SCHEMA_VERSION}"
        )
    try:
        return {i["inmate_number"]: Inmate(**i) for i in raw.get("inmates", [])}
    except (ValidationError, KeyError, TypeError, AttributeError) as e:
        raise SnapshotCorruptError(f"inmate deserialization failed: {e}") from e


def save_current(path: Path, inmates: Iterable[Inmate]) -> None:
    materialized = sorted(inmates, key=lambda i: (i.last_name, i.first_name, i.inmate_number))
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
      4. Write back. No CHANGELOG_LIMIT applies; this file grows forever.

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
            out[i] = _anonymize_event({
                "event": row.get("event"),
                "timestamp_utc": row.get("timestamp_utc"),
                "primary_tier": row.get("tier"),
                "primary_category": row.get("category"),
            })

    # Stable sort by date/timestamp, oldest first for append-only feel
    out.sort(key=lambda r: r.get("timestamp_utc") or r.get("date") or "")
    _atomic_write_text(path, json.dumps(out, indent=2))


def diff(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
) -> list[ChangeEvent]:
    """Compare previous vs current roster, emit booked/released/updated events."""
    now = utcnow_iso()
    events: list[ChangeEvent] = []

    # Defensive: a parser bug that synthesizes a duplicate inmate_number would
    # silently flatten records here. Dict construction in callers already
    # dedupes, so this is belt-and-suspenders — emit a warning if a caller
    # ever passes a mapping that doesn't agree with its records' own ids.
    for label, m in (("previous", previous), ("current", current)):
        bad = [iid for iid, inm in m.items() if inm.inmate_number != iid]
        if bad:
            log.warning("%s map has %d entries keyed under a different inmate_number", label, len(bad))

    for inmate_number, inm in current.items():
        if inmate_number not in previous:
            events.append(
                ChangeEvent(
                    event="booked",
                    inmate_number=inmate_number,
                    name=inm.full_name,
                    timestamp_utc=now,
                    note=f"booked {inm.booking_date}",
                )
            )
            continue
        prev = previous[inmate_number]
        if _materially_changed(prev, inm):
            events.append(
                ChangeEvent(
                    event="updated",
                    inmate_number=inmate_number,
                    name=inm.full_name,
                    timestamp_utc=now,
                )
            )

    for inmate_number, prev in previous.items():
        if inmate_number not in current:
            events.append(
                ChangeEvent(
                    event="released",
                    inmate_number=inmate_number,
                    name=prev.full_name,
                    timestamp_utc=now,
                    note="no longer on HCSO public roster",
                )
            )

    return events


def _materially_changed(a: Inmate, b: Inmate) -> bool:
    # Ignore last_seen_utc / first_seen_utc - only watch publicly-meaningful fields.
    scalar_keys = (
        "booking_number",
        "projected_release_date",
        "holder_status",
    )
    if any(getattr(a, k) != getattr(b, k) for k in scalar_keys):
        return True
    # Compare charges by canonical content, not by document order: HCSO
    # occasionally reshuffles the same charges in a different display order,
    # which would otherwise fire a wave of spurious `updated` events.
    a_charges = sorted(c.model_dump_json() for c in a.charges)
    b_charges = sorted(c.model_dump_json() for c in b.charges)
    return a_charges != b_charges
