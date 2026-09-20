"""Human-readable Cincinnati Open Data summaries, computed at build time.

Reads the pulled feed JSON files from ``data/`` (whatever is on disk; this
module never triggers a pull) and builds the template contexts for the
``/safety/`` page and the homepage teaser. Every raw code, disposition, and
category is translated to plain English here so templates never render a raw
Socrata code to readers.

Privacy: contexts built here NEVER include ``citizen_id``,
``unique_case_number``, ``license_plate_state``, ``event_number``, ``rms_no``,
or ``shootid``. Locations are block-level only. See ``FORBIDDEN_COLUMNS`` and
``tests/test_feed_integration.py``.

An empty or missing feed file yields an empty summary, never an exception:
the template renders a "no data in this pull" note instead.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Columns that must never appear in a rendered context. The aggregation
# functions below select only the columns they need; this set is asserted
# in tests/test_feed_integration.py as defense in depth.
FORBIDDEN_COLUMNS = frozenset(
    {
        "citizen_id",
        "unique_case_number",
        "license_plate_state",
        "event_number",
        "rms_no",
        "shootid",
    }
)

# Per-feed publication metadata shown next to each section. Status is a
# property of the *source*, not of our pull: "live" updates at the source,
# "paused" is the city's own word for the PDI use-of-force dataset, "frozen"
# means the city stopped publishing new rows (the file holds the most recent
# rows on record, not current activity).
FEED_META: dict[str, dict[str, str]] = {
    "cfs_recent.json": {
        "label": "CPD/CFD calls for service",
        "dataset_id": "qiik-bpks",
        "status": "live",
        "status_note": "",
    },
    "cfs_pdi_recent.json": {
        "label": "PDI police calls for service",
        "dataset_id": "gexm-h6bt",
        "status": "live",
        "status_note": "",
    },
    "shootings_recent.json": {
        "label": "CPD reported shootings",
        "dataset_id": "sfea-4ksu",
        "status": "live",
        "status_note": "",
    },
    "crime_stars_recent.json": {
        "label": "Reported crime (STARS)",
        "dataset_id": "7aqy-xrv9",
        "status": "live",
        "status_note": "",
    },
    "traffic_stops_drivers_recent.json": {
        "label": "Traffic stops (contact cards)",
        "dataset_id": "w2kv-5pdg",
        "status": "frozen",
        "status_note": (
            "No new contact cards have been published since 2025. "
            "This is the most recent ~5,000 on file, not current activity."
        ),
    },
    "pedestrian_stops_recent.json": {
        "label": "Pedestrian stops (contact cards)",
        "dataset_id": "swrz-ak2i",
        "status": "frozen",
        "status_note": (
            "No new contact cards have been published since 2024. "
            "This is the most recent ~5,000 on file, not current activity."
        ),
    },
    "use_of_force_pdi_recent.json": {
        "label": "PDI use of force",
        "dataset_id": "8us8-wi2w",
        "status": "paused",
        "status_note": (
            "The police department paused this dataset while transferring to "
            "a new records system. These are the most recent ~5,000 incidents "
            "on file."
        ),
    },
}

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_WHEN_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%Y%m%d",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y",
)


def _parse_when(raw: object) -> datetime | None:
    """Parse the feed datetime formats seen in the wild. Returns None (never
    raises) so one malformed timestamp can't break a whole section.

    Aware stamps (trailing Z or numeric offset) are normalized to naive UTC
    before the format loop so a feed that starts emitting offsets doesn't
    silently sort its rows to the bottom of "newest first"."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    if re.search(r"[+-]\d{2}:?\d{2}$", s):
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            dt = None
        if dt is not None:
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
    for fmt in _WHEN_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _display_when(dt: datetime | None, raw: object) -> str:
    """'Sep 18, 1:01 AM'. Falls back to the raw string when unparseable."""
    if dt is None:
        return str(raw or "").strip()
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return f"{_MONTHS[dt.month - 1]} {dt.day}, {dt.year}"
    return f"{_MONTHS[dt.month - 1]} {dt.day}, {hour}:{dt.minute:02d} {ampm}"


def vintage_of(data_dir: Path, filename: str) -> str:
    """A feed file's generated_utc stamp ("" when missing/unreadable)."""
    return _load_feed(data_dir, filename)["generated_utc"]


def _load_feed(data_dir: Path, filename: str) -> dict:
    """Load one feed file. Missing or corrupt files yield an empty feed with
    an empty vintage stamp; the caller renders a 'no data' note."""
    path = data_dir / filename
    empty = {"generated_utc": "", "row_count": 0, "rows": [], "dataset_id": ""}
    if not path.exists():
        return empty
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("feed %s unreadable (%s); treating as empty", filename, exc)
        return empty
    if not isinstance(payload, dict):
        return empty
    rows = payload.get("rows")
    try:
        row_count = int(payload.get("row_count") or 0)
    except (TypeError, ValueError):
        row_count = 0
    return {
        "generated_utc": str(payload.get("generated_utc") or ""),
        "row_count": row_count,
        "rows": rows if isinstance(rows, list) else [],
        "dataset_id": str(payload.get("dataset_id") or ""),
    }


# ---------------------------------------------------------------------------
# Plain-English mappings. Raw codes never reach a template untranslated.
#
# Two deliberate, different philosophies live here:
# - Fail loud: dispositions (_DISPOSITION_EN), STARS categories
#   (_STARS_CATEGORY_EN), and STARS types (_STARS_TYPE_EN) have a coverage
#   test that breaks the suite when the city introduces a new code, so it
#   gets a real translation instead of leaking raw.
# - Graceful: incident types and stop actions degrade via normalization
#   ("Other police call") or title-casing. A wrong-but-plausible label is
#   possible there; the property tests guard structure, not semantics.
# ---------------------------------------------------------------------------

_DISPOSITION_EN = {
    "301:OFFENSE REPORT": "Offense report filed",
    "CIT: CITED": "Citation issued",
    "ARR: ARREST": "Arrest made",
    "SOW: SENT ON WAY": "Sent on way",
    "OH: OH": "On hold",
    "ADV:ADVISED": "Advised",
    "CAN:CANCEL": "Cancelled",
    "INV: INV": "Investigation",
    "TOW: TOW RPRT": "Tow report",
}

# CAD incident-type codes need normalization, not enumeration: the two CFS
# feeds carry ~180 distinct bases plus timing/status suffixes like (NIP)
# "not in progress", (JO) "just occurred", (IP) "in progress", (E)/(W)
# "east/west", and caller-added "+"/"=" prefixes. The normalizer strips the
# suffixes/prefixes/system artifacts, expands known abbreviations, and
# title-cases readable phrases. Single-word tokens that are neither a known
# abbreviation nor a plain English word are opaque CAD codes; they render as
# "Other police call" rather than leaking an abbreviation a reader cannot
# decode. A new legitimate English word degrades to that bucket too
# (documented limitation: graceful rather than wrong).
_INCIDENT_ABBREV_EN = {
    "TSTOP": "Traffic stop",
    "THEFTR": "Theft",
    "ASSLT": "Assault",
    "ASSLTP": "Assault",
    "ASSLTR": "Assault",
    "CRDAMR": "Criminal damage",
    "DOMVIO": "Domestic violence",
    "ROBBR": "Robbery",
    "BER": "Breaking and entering",
    "BURG": "Burglary",
    "RBURG": "Burglary",
    "NRBURG": "Burglary",
    "MENACR": "Menace",
    "DISORD": "Disorderly conduct",
    "SEXR": "Sex offense",
    "SEX": "Sex offense",
    "ATL": "Attempt to locate",
    "FAMTRB": "Family trouble",
    "NBRTRB": "Neighbor trouble",
    "RAPER": "Rape",
    "MISS": "Missing person",
    "STALKR": "Stalking",
    "DRUGR": "Drug offense",
    "MHC": "Mental health crisis",
    "AUTO": "Vehicle incident",
    "PHONE": "Phone report",
    "CHILD": "Child-related call",
    "MEET": "Meet",
    "WANTED": "Wanted person",
}

# Single-word bases that are plain English (title-cased as-is). Any other
# single-word all-caps token is an opaque CAD abbreviation.
_INCIDENT_ENGLISH_WORDS = frozenset(
    {
        "ABUSE", "ASSAULT", "BURGLARY", "CRASH", "CROWD", "DAMAGE", "FIGHT",
        "FORGERY", "FRAUD", "HOSTAGE", "MENACE", "MISCHIEF", "POLICE",
        "ROBBERY", "RUNAWAY", "SHOOTING", "STABBING", "STALKING", "THEFT",
        "THREAT",
    }
)

_ACTION_TAKEN_EN = {
    "CITATION TRAFFIC": "Traffic citation",
    "WARNING": "Warning, no citation",
    "NONE": "No action taken",
    "CITATION CAPIASWAR": "Citation on outstanding warrant",
    "ARREST CAPIASWAR": "Arrest on outstanding warrant",
    "ARREST MISD.": "Misdemeanor arrest",
    "CITATION MISD.": "Misdemeanor citation",
    "ARREST FELONY": "Felony arrest",
    "OTHER": "Other",
}

# Every STARS category on record, mapped explicitly (the coverage test fails
# loudly on a new one). Values are already readable English; the map exists
# to pin the presentation wording and to catch new codes.
_STARS_CATEGORY_EN = {
    "Agg Assault": "Aggravated assault",
    "Auto Theft": "Auto theft",
    "Burglary/BE": "Burglary / breaking and entering",
    "Homicide": "Homicide",
    "Part 2": "Part 2",
    "Personal/Other Theft": "Personal/other theft",
    "Rape": "Rape",
    "Robbery": "Robbery",
    "Strangulation": "Strangulation",
    "Theft from Auto": "Theft from auto",
}

# Every STARS type on record. Unknown values are NOT silently folded into
# "Part 2": they render as "Unclassified" so a new type is visible, and the
# coverage test fails loudly so it gets classified properly.
_STARS_TYPE_EN = {
    "Part 1 Violent": "Part 1 — violent",
    "Part 1 Property": "Part 1 — property",
    "Part 2": "Part 2",
}

# Fixed presentation order for stop outcomes (most common first), keyed on
# the English labels the page actually shows.
_ACTION_ORDER = (
    "Traffic citation",
    "Warning, no citation",
    "No action taken",
    "Citation on outstanding warrant",
    "Arrest on outstanding warrant",
    "Misdemeanor arrest",
    "Misdemeanor citation",
    "Felony arrest",
    "Other",
    "Not recorded",
)

# Race columns collapse to four presentation buckets; anything outside the big
# three is rare enough to aggregate honestly as "Other".
_RACE_BUCKETS = ("Black", "White", "Unknown", "Other")


def _race_en(raw: object) -> str:
    s = str(raw or "").strip().upper()
    if s == "BLACK":
        return "Black"
    if s == "WHITE":
        return "White"
    if s == "UNKNOWN":
        return "Unknown"
    if s:
        return "Other"
    return "Unknown"


def _sex_en(raw: object) -> str:
    s = str(raw or "").strip().upper()
    if s == "MALE":
        return "Male"
    if s == "FEMALE":
        return "Female"
    return "Unknown"


def _neighborhood_en(row: dict) -> str:
    for col in ("cpd_neighborhood", "community_council_neighborhood", "sna_neighborhood"):
        v = row.get(col)
        if isinstance(v, str) and v.strip():
            return v.strip().title()
    return ""


def _address_en(raw: object) -> str:
    """Title-case a block-level address while preserving the city's XX
    privacy masking: '1XX MAIN ST' renders '1XX Main St', not '1Xx Main St'."""
    s = str(raw or "").strip()
    if not s:
        return ""
    parts = []
    for tok in s.split():
        if re.fullmatch(r"\d*X{2,}", tok):
            parts.append(tok)
        else:
            parts.append(tok.title())
    return " ".join(parts)


def _disposition_en(raw: object) -> str:
    """Translate a compound disposition like 'ARR: ARREST,SOW: SENT ON WAY'.

    Fail loud: an untranslated code raises KeyError so it gets a real
    translation instead of leaking a title-cased raw code to readers.
    """
    parts = [p.strip() for p in str(raw or "").split(",") if p.strip()]
    out = []
    for p in parts:
        try:
            out.append(_DISPOSITION_EN[p])
        except KeyError:
            raise KeyError(
                f"untranslated disposition code {p!r}; add it to _DISPOSITION_EN"
            ) from None
    return "; ".join(out)


def _incident_type_en(raw: object) -> str:
    """Normalize a CAD incident type to plain English.

    Strips timing/status parentheticals ("(NIP)", "(JO)(W)(E)"), caller "+"
    prefixes, "=" prefixes, and system artifacts ("_2", "-COMBINED"); expands
    known abbreviations; title-cases readable phrases. Opaque single-word
    CAD codes fall back to "Other police call".
    """
    s = str(raw or "").strip()
    if not s:
        return "Incident"
    base = s.lstrip("+=").strip()
    base = re.sub(r"\([^)]*\)", "", base)
    base = re.sub(r"_2$", "", base)
    base = base.replace("-COMBINED", "")
    base = re.sub(r"\s+", " ", base).strip().upper()
    if not base:
        return "Incident"
    if base in _INCIDENT_ABBREV_EN:
        return _INCIDENT_ABBREV_EN[base]
    if re.search(r"[\s\-/]", base):
        # Multi-word phrase: expand embedded abbreviations, then title-case.
        if base.startswith("CRASH"):
            return "Traffic crash"
        expanded = " ".join(_INCIDENT_ABBREV_EN.get(w, w) for w in base.split(" "))
        return re.sub(r"\bCpd\b", "CPD", expanded.title())
    if base in _INCIDENT_ENGLISH_WORDS:
        return base.title()
    return "Other police call"


def _action_en(raw: object) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return "Not recorded"
    return _ACTION_TAKEN_EN.get(s, s.title())


def _stars_category_en(raw: object) -> str:
    """Map a STARS category to its plain-English bucket.

    Fail loud: an unmapped category raises KeyError so a new city code gets
    classified instead of rendering raw on the page. (STARS *types* are the
    deliberate contrast: they degrade to "Unclassified" by design.)
    """
    s = str(raw or "").strip()
    try:
        return _STARS_CATEGORY_EN[s]
    except KeyError:
        raise KeyError(
            f"untranslated STARS category {s!r}; add it to _STARS_CATEGORY_EN"
        ) from None


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def _count_by(rows: list[dict], keyfn) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for r in rows:
        label = keyfn(r)
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def latest_incidents(data_dir: Path = DATA_DIR, n: int = 30) -> list[dict]:
    """Newest incidents across CFS, shootings, and STARS as plain-English rows.

    Each row: {when_display, what, where, neighborhood}. Sorted newest first;
    unparseable timestamps sort last and display raw.
    """
    items: list[dict] = []
    seen_events: set[str] = set()

    def add(when_raw: object, what: str, where: str, neighborhood: str, dedup: str = "") -> None:
        if dedup:
            if dedup in seen_events:
                return
            seen_events.add(dedup)
        dt = _parse_when(when_raw)
        items.append(
            {
                "sort_key": dt.isoformat() if dt else "",
                "when_display": _display_when(dt, when_raw),
                "what": what,
                "where": where,
                "neighborhood": neighborhood,
            }
        )

    for filename in ("cfs_recent.json", "cfs_pdi_recent.json"):
        feed = _load_feed(data_dir, filename)
        for r in feed["rows"]:
            if not isinstance(r, dict):
                continue
            what = _incident_type_en(r.get("incident_type_id"))
            disp = _disposition_en(r.get("disposition_text"))
            if disp:
                what = f"{what} — {disp.lower()}"
            # Dedup only on a real identifier: rows with no event number are
            # always kept (an empty key would collapse distinct incidents).
            ev = str(r.get("event_number") or "").strip()
            add(
                r.get("create_time_incident"),
                what,
                _address_en(r.get("address_x")),
                _neighborhood_en(r),
                dedup=("cfs:" + ev) if ev else "",
            )

    shootings = _load_feed(data_dir, "shootings_recent.json")
    for r in shootings["rows"]:
        if not isinstance(r, dict):
            continue
        kind = str(r.get("type") or "").strip().lower()
        what = "Shooting — fatal" if kind == "fatal" else "Shooting — nonfatal" if kind == "nonfatal" else "Shooting"
        add(
            r.get("datetimeoccured") or r.get("dateoccurred"),
            what,
            _address_en(r.get("streetblock")),
            _neighborhood_en(r),
        )

    stars = _load_feed(data_dir, "crime_stars_recent.json")
    for r in stars["rows"]:
        if not isinstance(r, dict):
            continue
        add(
            r.get("datereported"),
            "Reported crime — " + _stars_category_en(r.get("stars_category")),
            _address_en(r.get("address_x")),
            _neighborhood_en(r),
        )

    items.sort(key=lambda i: i["sort_key"], reverse=True)
    return items[:n]


def summarize_crime_stars(data_dir: Path = DATA_DIR) -> dict:
    """Reported-crime breakdown for the last ~30 days."""
    feed = _load_feed(data_dir, "crime_stars_recent.json")
    rows = [r for r in feed["rows"] if isinstance(r, dict)]
    # Evidence for the "last 30 days" heading: the actual date span of the
    # pull, so the claim goes stale visibly instead of silently if the sweep
    # window ever changes.
    dts = [
        dt
        for r in rows
        if (dt := _parse_when(r.get("datereported"))) is not None
    ]
    date_span = ""
    if dts:
        lo, hi = min(dts), max(dts)
        if lo.date() == hi.date():
            date_span = f"{_MONTHS[lo.month - 1]} {lo.day}, {lo.year}"
        else:
            date_span = (
                f"{_MONTHS[lo.month - 1]} {lo.day} to "
                f"{_MONTHS[hi.month - 1]} {hi.day}, {hi.year}"
            )
    return {
        "meta": FEED_META["crime_stars_recent.json"],
        "vintage": feed["generated_utc"],
        "total": len(rows),
        "date_span": date_span,
        "by_category": _count_by(rows, lambda r: _stars_category_en(r.get("stars_category"))),
        "by_type": _count_by(
            rows,
            lambda r: _STARS_TYPE_EN.get(str(r.get("type") or "").strip(), "Unclassified"),
        ),
        "empty": not rows,
    }


def _summarize_one_stop_feed(data_dir: Path, filename: str) -> dict:
    feed = _load_feed(data_dir, filename)
    rows = [r for r in feed["rows"] if isinstance(r, dict)]
    by_race = _count_by(rows, lambda r: _race_en(r.get("race")))
    by_sex = _count_by(rows, lambda r: _sex_en(r.get("sex")))
    # Aggregate by translated outcome label (not raw code). Distinct raw
    # values keep distinct rows ("OTHER" -> "Other", blank -> "Not
    # recorded"); outcomes-by-race is built in the same pass so the table
    # can never disagree with the bars.
    order = {label: i for i, label in enumerate(_ACTION_ORDER)}
    action_counts: Counter[str] = Counter()
    race_by_action: dict[str, Counter[str]] = {}
    for r in rows:
        action = _action_en(r.get("action_taken_cid"))
        action_counts[action] += 1
        bucket = race_by_action.setdefault(action, Counter())
        bucket[_race_en(r.get("race"))] += 1
    by_action = sorted(
        action_counts.items(), key=lambda kv: (order.get(kv[0], 99), kv[0])
    )
    table = [
        {
            "action": action,
            "counts": [race_by_action[action].get(b, 0) for b in _RACE_BUCKETS],
            "total": count,
        }
        for action, count in by_action
    ]

    return {
        "meta": FEED_META[filename],
        "vintage": feed["generated_utc"],
        "total": len(rows),
        "by_race": by_race,
        "by_sex": by_sex,
        "by_action": by_action,
        "race_columns": list(_RACE_BUCKETS),
        "race_action_table": table,
        "empty": not rows,
    }


def summarize_stops(data_dir: Path = DATA_DIR) -> dict[str, dict]:
    """Traffic and pedestrian stop summaries, keyed 'drivers' / 'pedestrian'."""
    return {
        "drivers": _summarize_one_stop_feed(data_dir, "traffic_stops_drivers_recent.json"),
        "pedestrian": _summarize_one_stop_feed(data_dir, "pedestrian_stops_recent.json"),
    }


def safety_context(data_dir: Path = DATA_DIR) -> dict:
    """Full template context for the /safety/ page."""
    incidents = latest_incidents(data_dir)
    return {
        "incidents": incidents,
        "stars": summarize_crime_stars(data_dir),
        "stops": summarize_stops(data_dir),
    }
