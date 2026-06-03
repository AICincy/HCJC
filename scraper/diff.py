"""Roster diffing and material change detection.

Extracted from store.py to decouple pure logic from file IO.
"""

from __future__ import annotations

import logging

from .models import ChangeEvent, Inmate, utcnow_iso

log = logging.getLogger(__name__)


def diff(
    previous: dict[str, Inmate],
    current: dict[str, Inmate],
) -> list[ChangeEvent]:
    """Compare previous vs current roster, emit booked/released/updated events."""

    # HCSO emits "1/1/70" (epoch 0) when it has no booking date; don't bake that
    # sentinel into the human-readable event note.
    def _booked_note(booking_date: str | None) -> str:
        bd = (booking_date or "").strip()
        if bd in ("", "1/1/70", "01/01/70", "1/1/1970", "01/01/1970"):
            return "booked (date not reported)"
        return f"booked {bd}"

    now = utcnow_iso()
    events: list[ChangeEvent] = []

    # Defensive: a parser bug that synthesizes a duplicate inmate_number would
    # silently flatten records here. Dict construction in callers already
    # dedupes, so this is belt-and-suspenders - emit a warning if a caller
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
                    note=_booked_note(inm.booking_date),
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
