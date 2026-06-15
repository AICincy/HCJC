"""Event feeds, changelog filtering, and RSS description helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scraper.models import ChangeEvent


def _events_for_inmate(events: list[ChangeEvent], inmate_number: str) -> list[ChangeEvent]:
    """Return the chronological list of changelog events for one inmate,
    oldest first. Empty list if the inmate has no events on file.
    """
    if not inmate_number:
        return []
    out = [e for e in events if e.inmate_number == inmate_number]
    out.sort(key=lambda e: e.timestamp_utc or "")
    return out


def _events_in_window(events: list[ChangeEvent], hours: int) -> list[ChangeEvent]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    keep: list[ChangeEvent] = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.timestamp_utc.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if ts >= cutoff:
            keep.append(e)
    return keep


def _events_for_recent(events: list[ChangeEvent], hours: int = 8) -> list[ChangeEvent]:
    """Recent activity feed: events JCStream observed within the window,
    AND for 'booked' events, the actual HCSO booking date must also be within
    the window. Without that second check the first-ever sweep seeds the feed
    with hundreds of 'booked' events for inmates who were actually booked
    weeks or months ago.
    """
    cutoff_ts = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_date = cutoff_ts.date()
    out: list[ChangeEvent] = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.timestamp_utc.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if ts < cutoff_ts:
            continue
        if e.event == "booked" and e.note.startswith("booked "):
            bd_str = e.note[len("booked ") :].strip()
            bd = None
            for fmt in ("%m/%d/%y", "%m/%d/%Y"):
                try:
                    bd = datetime.strptime(bd_str, fmt).date()
                    break
                except ValueError:
                    continue
            if bd is not None and bd < cutoff_date:
                continue
        out.append(e)
    return out


def _feed_description(event: str, name: str, inmate_number: str, note: str) -> str:
    """Build a readable per-item <description> for the RSS feeds. The template
    previously rendered "{event} {note}" verbatim, which produced strings like
    "released no longer on HCSO public roster" - grammatical noise. This shapes
    each event type into a complete sentence."""
    nm = (name or "Unknown").strip()
    n = (note or "").strip()
    if event == "booked":
        if n.startswith("booked "):
            return f"{nm} (#{inmate_number}) was {n} into the Hamilton County Justice Center."
        return f"{nm} (#{inmate_number}) was booked into the Hamilton County Justice Center."
    if event == "released":
        return f"{nm} (#{inmate_number}) is no longer on the HCSO public roster."
    if event == "updated":
        return f"{nm} (#{inmate_number}): record updated{(' - ' + n) if n else ''}."
    return f"{nm} (#{inmate_number}): {event}{(' - ' + n) if n else ''}."


def _clean_event_note(note: str | None) -> str:
    """Scrub the HCSO epoch-0 sentinel ('1/1/70') out of historical changelog
    notes so the status history never shows a 1970 date."""
    s = note or ""
    for sentinel in ("01/01/1970", "1/1/1970", "01/01/70", "1/1/70"):
        s = s.replace(sentinel, "date not reported")
    return s
