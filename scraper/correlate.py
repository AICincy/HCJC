"""Phase 11: Researcher-mode dispatch correlation.

For each booking on the current roster, find candidate Cincinnati Open Data
calls-for-service rows that *might* be the dispatch that led to it. Match
on: same day (UTC), within +/- 30 minutes of the booking_date if known, AND
a strong textual overlap between the CFS row's charge/disposition and the
inmate's primary charge category.

Output is a pure-data ``data/dispatch_correlations.json`` file. It contains:

  - inmate_number (key already public on the inmate's own page)
  - cfs_row_index (key already public in the cfs_recent.json + cfs_pdi_recent.json
    feeds)
  - signals dict explaining WHY this row was nominated
  - confidence score (0.0 to 1.0)

It deliberately does NOT contain:
  - The inmate's name
  - The dispatch incident's full address (only block-level if at all)
  - Any narrative or PII from either side
  - Any auto-published assertion that "X was arrested for Y"

A consumer (a journalist, a researcher) can join the correlation feed
against the public ``current.json`` and the public ``cfs_recent.json`` on
the documented keys to investigate further. This is the "raw data export"
backdoor recommended in Phase 10's bottleneck discussion: it provides
accountability-grade data without putting JCStream on the hook for
naming someone wrong.

The module is callable as ``python -m scraper.correlate`` and is gated
to run only when both ``data/current.json`` and at least one of the CFS
feeds are present. No external network calls. No fabrication.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path("data")
OUT_PATH = DATA_DIR / "dispatch_correlations.json"

# Match window: a booking on roster X often happens within an hour of the
# dispatch CFS row. Sweep cadence is 30 min, so the booking timestamp on
# our side has up to 30 min of latency on top of the actual booking.
WINDOW_MINUTES = 60

# Confidence floor: pairs below this are dropped before write. Keeps the
# output feed sparse (high-signal only).
MIN_CONFIDENCE = 0.35


@dataclass
class Candidate:
    inmate_number: str
    cfs_source: str  # "cfs_recent" or "cfs_pdi_recent"
    cfs_row_index: int
    confidence: float
    signals: dict


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("could not read %s: %s", path, e)
        return None


def _parse_booking_dt(s: str | None) -> datetime | None:
    """HCSO booking_date format is typically ``M/D/YY`` or ``M/D/YYYY``."""
    if not s:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _parse_cfs_dt(row: dict) -> tuple[datetime, bool] | None:
    """CFS feeds use slightly different timestamp fields per dataset.
    Try the common ones in order.

    Returns ``(datetime, has_time)`` where ``has_time`` is True when the
    Socrata string contained a 'T' separator (real time-of-day) and
    False when it was a date-only string that ``datetime.fromisoformat``
    defaulted to midnight UTC. Returns None when no field parses.

    The ``has_time`` flag lets the caller avoid the prior heuristic
    ``cfs_dt.hour != 0`` which mis-classified a legitimate midnight UTC
    row as date-only.
    """
    for key in ("event_datetime", "create_time_incident", "dispatch_time",
                "incident_date", "datereported", "eventdate", "interview_date"):
        v = row.get(key)
        if not v:
            continue
        s = str(v)
        has_time = "T" in s
        # Socrata returns ISO-8601 strings like '2026-05-15T18:23:00.000'
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00").split(".")[0])
            return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt), has_time
        except ValueError:
            continue
    return None


def _category_overlap(charge_desc: str, cfs_text: str) -> float:
    """Cheap textual signal: how many distinctive words from the charge
    description appear in the CFS row's disposition/incident-type fields.

    Returns 0.0 to 1.0. Stop-words and very-short tokens are dropped so
    'OF' and 'THE' don't inflate every score."""
    if not charge_desc or not cfs_text:
        return 0.0
    STOP = {"of", "the", "a", "an", "and", "or", "to", "in", "on", "for"}
    charge_tokens = {t for t in charge_desc.lower().split() if len(t) > 3 and t not in STOP}
    cfs_lower = cfs_text.lower()
    if not charge_tokens:
        return 0.0
    hits = sum(1 for t in charge_tokens if t in cfs_lower)
    return hits / len(charge_tokens)


def correlate(
    current: dict,
    cfs_rows: list[dict],
    cfs_source: str,
) -> list[Candidate]:
    """Walk every inmate currently on the roster and every recent CFS row,
    emit any (inmate, row) pair whose temporal + textual signals exceed
    ``MIN_CONFIDENCE``. Many bookings will have zero candidates; this is
    fine and expected."""
    out: list[Candidate] = []
    inmates = current.get("inmates", [])
    for inm in inmates:
        inum = inm.get("inmate_number")
        if not inum:
            continue
        booked = _parse_booking_dt(inm.get("booking_date"))
        if not booked:
            continue
        charges = inm.get("charges") or []
        if not charges:
            continue
        primary_desc = (charges[0].get("description") or "").strip()
        if not primary_desc:
            continue

        for idx, row in enumerate(cfs_rows):
            parsed = _parse_cfs_dt(row)
            if not parsed:
                continue
            cfs_dt, has_time = parsed
            # Same-day filter first (cheap)
            if abs((cfs_dt.date() - booked.date()).days) > 1:
                continue
            # If Socrata returned a real time-of-day (T-separator present),
            # drop pairs beyond a coarse 8x-window (8h) outer bound. This is
            # deliberately wider than the WINDOW_MINUTES*4 score-decay below
            # (line 184): inside 8h a strong text overlap can still clear
            # MIN_CONFIDENCE on its own even after the temporal score hits 0.
            # A legitimate midnight-UTC event keeps has_time=True and is bounded
            # correctly; a date-only response defaults to midnight and skips
            # this step (the same-day filter above already bounds it).
            dt_delta_min = abs((cfs_dt - booked).total_seconds()) / 60.0
            if has_time and dt_delta_min > WINDOW_MINUTES * 8:
                continue

            # Textual overlap on the disposition + incident type
            cfs_text = " ".join(str(row.get(k, "")) for k in (
                "disposition_text", "disposition", "incident_type_id",
                "incident_type_desc", "offense_classification", "offense_name",
            ))
            overlap = _category_overlap(primary_desc, cfs_text)

            # Confidence weights: temporal proximity 0.5 + textual overlap 0.5
            temporal_score = max(0.0, 1.0 - dt_delta_min / (WINDOW_MINUTES * 4))
            conf = 0.5 * temporal_score + 0.5 * overlap

            if conf < MIN_CONFIDENCE:
                continue

            out.append(Candidate(
                inmate_number=inum,
                cfs_source=cfs_source,
                cfs_row_index=idx,
                confidence=round(conf, 3),
                signals={
                    "dt_delta_minutes": round(dt_delta_min, 1),
                    "textual_overlap": round(overlap, 3),
                    "booked_date": inm.get("booking_date"),
                },
            ))
    return out


def run(write: bool = True) -> int:
    """Build and (optionally) write data/dispatch_correlations.json.
    Returns count of correlation pairs found."""
    current = _load_json(DATA_DIR / "current.json")
    if not isinstance(current, dict) or not current.get("inmates"):
        log.info("no current.json; skipping correlation")
        return 0

    all_candidates: list[Candidate] = []
    for src_name, src_path in (
        ("cfs_recent", DATA_DIR / "cfs_recent.json"),
        ("cfs_pdi_recent", DATA_DIR / "cfs_pdi_recent.json"),
    ):
        payload = _load_json(src_path)
        if not payload:
            continue
        rows = payload.get("rows") if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        if not isinstance(rows, list):
            continue
        cands = correlate(current, rows, src_name)
        log.info("%s: %d candidate pairs", src_name, len(cands))
        all_candidates.extend(cands)

    # Stable sort by confidence DESC, then inmate_number, then source index
    all_candidates.sort(key=lambda c: (-c.confidence, c.inmate_number, c.cfs_source, c.cfs_row_index))

    if write:
        out_payload = {
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "min_confidence": MIN_CONFIDENCE,
            "window_minutes": WINDOW_MINUTES,
            "count": len(all_candidates),
            "disclaimer": (
                "Researcher-mode output. Pairs are CANDIDATES only, not asserted "
                "matches. A high-confidence pair still requires human verification "
                "before any public claim is made that a specific dispatch led to a "
                "specific arrest. JCStream does not publish these joins on its own "
                "pages. Joining keys are inmate_number (vs current.json) and "
                "cfs_row_index (vs the cfs_recent.json or cfs_pdi_recent.json "
                "feed identified by cfs_source). Confidence weights: 50% temporal "
                "proximity within a +/- 60 minute window, 50% textual overlap "
                "between the charge description and the CFS row's disposition/"
                "incident-type fields."
            ),
            "pairs": [
                {
                    "inmate_number": c.inmate_number,
                    "cfs_source": c.cfs_source,
                    "cfs_row_index": c.cfs_row_index,
                    "confidence": c.confidence,
                    "signals": c.signals,
                }
                for c in all_candidates
            ],
        }
        OUT_PATH.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
        log.info("wrote %s (%d pairs)", OUT_PATH, len(all_candidates))
    return len(all_candidates)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return run(write=True)


if __name__ == "__main__":
    main()
