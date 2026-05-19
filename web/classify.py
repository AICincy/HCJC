"""Pure helpers for charge classification, data parsing, and display formatting.

This module provides reference data (degree regex, chapter/offense mappings,
tier/race/sex label expansions) and parsing/formatting functions consumed by
shape.py and web/build.py. No circular dependencies: shape/build import from
classify, never the reverse.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# ============================================================================
# Reference Data / Constants
# ============================================================================

# Regex to extract degree suffix (F1, F2, M1, etc.) from charge description.
# Matches " F1", " F2", " F3", " F4", " F5", " M1", " M2", " M3", " M4", " MM"
# at the end of the description string (or before closing paren).
_DEGREE_RE = re.compile(r"\b([FM]\d|MM)\b")

# Minimum inmates in a month-group before it's rendered as its own section.
# Smaller groups roll into "Earlier bookings" to avoid a long tail.
_MIN_MONTH_SIZE = 3

# Degree order (severity): lower index = more serious. Used for ranking charges.
_DEGREE_ORDER = ("F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM")

# Tier categories by degree (for CSS coloring and display grouping).
_TIER_MAX = {
    "F1": "F",
    "F2": "F",
    "F3": "F",
    "F4": "F",
    "F5": "F",
    "M1": "M",
    "M2": "M",
    "M3": "M",
    "M4": "M",
    "MM": "M",
}

# Primary offense categories by ORC chapter code (2903 = violence, 2925 = drugs, etc.)
# Used for primary charge ranking and chapter-level offense grouping.
_CHAPTER_LABEL = {
    # Violence / sex
    "2903": "Violence / Sex",
    "2905": "Violence / Sex",
    "2907": "Violence / Sex",
    # Theft / fraud
    "2913": "Theft / Fraud",
    "2914": "Theft / Fraud",
    "2915": "Theft / Fraud",
    # Drugs
    "2925": "Drugs",
    # Weapons
    "2923": "Weapons",
    # Damage / arson
    "2909": "Damage / Arson",
    # Robbery / burglary
    "2911": "Robbery / Burglary",
    # Disorderly / public
    "2917": "Disorderly / Public",
    # Family / domestic
    "2919": "Family / Domestic",
    # Obstruction
    "2921": "Obstruction",
    # Attempt / conspiracy
    "2923": "Weapons",
    # Traffic / DUI
    "4511": "Traffic / DUI",
    "4510": "Traffic / DUI",
    "4503": "Traffic / DUI",
    # Other
    "2901": "Other",
}

# Offense category rankings for primary charge selection.
# Lower rank = higher priority when multiple charges exist.
_CLS_RANK = {
    "2903": 0,   # Violence / homicide
    "2905": 1,   # Kidnapping
    "2907": 2,   # Sexual assault
    "2911": 3,   # Robbery / burglary
    "2909": 4,   # Arson
    "2913": 5,   # Theft
    "2925": 6,   # Drugs
    "2923": 7,   # Weapons
    "2921": 8,   # Obstruction
    "2919": 9,   # Family / domestic
    "2917": 10,  # Disorderly
    "4511": 11,  # Traffic / DUI
}

# Offense categorization: ORC code -> {label, cls} for display.
# The 'cls' field is used for CSS color classes and statistical grouping.
_OFFENSE_CATEGORY = {
    # Violence / homicide (chapter 2903)
    "2903": {"label": "Violence / Homicide", "cls": "2903"},
    # Sexual assault (chapter 2907)
    "2907": {"label": "Sexual Assault", "cls": "2907"},
    # Robbery / burglary (chapter 2911)
    "2911": {"label": "Robbery / Burglary", "cls": "2911"},
    # Theft (chapter 2913)
    "2913": {"label": "Theft / Fraud", "cls": "2913"},
    # Drugs (chapter 2925)
    "2925": {"label": "Drugs", "cls": "2925"},
    # Weapons (chapter 2923)
    "2923": {"label": "Weapons", "cls": "2923"},
    # Obstruction (chapter 2921)
    "2921": {"label": "Obstruction", "cls": "2921"},
    # Family / domestic (chapter 2919)
    "2919": {"label": "Family / Domestic", "cls": "2919"},
    # Disorderly (chapter 2917)
    "2917": {"label": "Disorderly", "cls": "2917"},
    # Traffic / DUI (chapters 4510, 4511, 4503)
    "4511": {"label": "Traffic / DUI", "cls": "traffic"},
    "4510": {"label": "Traffic / License", "cls": "traffic"},
    "4503": {"label": "Traffic / Registration", "cls": "traffic"},
    # Arson (chapter 2909)
    "2909": {"label": "Arson / Damage", "cls": "2909"},
    # Other (fallback)
    "other": {"label": "Other", "cls": "traffic"},
}

# Race code expansions (HCSO uses single letters for race classification).
_RACE_LABEL = {
    "W": "White",
    "B": "Black",
    "H": "Hispanic",
    "A": "Asian",
    "I": "Native American",
    "O": "Other",
}

# Sex code expansions (HCSO uses M/F for sex classification).
_SEX_LABEL = {
    "M": "Male",
    "F": "Female",
}

# ============================================================================
# Parsing / Conversion Functions
# ============================================================================

def _parse_book_date(date_str: str | None) -> datetime | None:
    """Parse booking date string (MM/DD/YY or MM/DD/YYYY format) to datetime.
    
    Returns None if the string is empty or unparseable. Sentinel dates like
    '1/1/70' (epoch) are treated as valid to avoid losing data, but are
    often filtered out downstream.
    """
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _parse_md_yy(date_str: str | None) -> datetime | None:
    """Alias for _parse_book_date, handling MM/DD/YY format."""
    return _parse_book_date(date_str)


def _parse_bond_amount(bond_str: str | None) -> int | None:
    """Extract numeric bond amount from string like '$50,000.00' or 'BOND $500'.
    
    Returns int (in dollars, truncated) or None if unparseable or empty.
    """
    if not bond_str:
        return None
    m = re.search(r"\$?([\d,]+(?:\.\d{2})?)", str(bond_str))
    if not m:
        return None
    try:
        return int(float(m.group(1).replace(",", "")))
    except ValueError:
        return None


def _display_date(date: datetime | None) -> str:
    """Format datetime for display (e.g., 'May 14, 2026')."""
    if not date:
        return ""
    try:
        return date.strftime("%b %d, %Y")
    except (ValueError, AttributeError):
        return ""


def _short_month_label(month_str: str) -> str:
    """Convert 'May 2026' to 'May '26' style (apostrophe year)."""
    if not month_str:
        return ""
    # Try to parse "Month YYYY" format.
    parts = month_str.rsplit(" ", 1)
    if len(parts) == 2:
        month, year = parts
        try:
            # Extract last 2 digits of year.
            year_int = int(year)
            year_short = year_int % 100
            return f"{month} '{year_short:02d}"
        except ValueError:
            pass
    return month_str


def _approx_age(dob_str: str | None) -> int | None:
    """Estimate age from date-of-birth string (MM/DD/YY or MM/DD/YYYY format).
    
    Handles two-digit years using a ~25-year cutoff: if the year would make
    the person ~60+ years old, prepend 19; otherwise prepend 20. Returns None
    if the string is unparseable or represents an invalid date.
    """
    if not dob_str:
        return None
    dob_str = str(dob_str).strip()
    dob = _parse_book_date(dob_str)
    if not dob:
        return None
    today = datetime.now()
    # Rough age calculation (doesn't account for exact day yet).
    age = today.year - dob.year
    # Adjust if birthday hasn't occurred this year.
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age if age >= 0 else None


def _booking_seq(booking_date_str: str | None) -> str:
    """Extract booking sequence from booking_date string (e.g., '26002740' -> 'booking #2,740 of 2026').
    
    The first 2 digits are the year; the remaining digits are the sequence number.
    Returns empty string if unparseable.
    """
    if not booking_date_str:
        return ""
    s = str(booking_date_str).strip()
    if len(s) < 8 or not s.isdigit():
        return ""
    year = int(s[:2])
    seq = int(s[2:])
    # Interpret 2-digit year (70+ = 19XX, <70 = 20XX).
    full_year = 1900 + year if year >= 70 else 2000 + year
    return f"booking #{seq:,} of {full_year}"


def _avatar_initials(name_str: str) -> str:
    """Extract first two letters from a name for display in an avatar badge.
    
    Takes the first letter of the first word and the first letter of the last word.
    For single-word names, returns first two letters. Returns '?' for empty input.
    """
    if not name_str:
        return "?"
    parts = name_str.strip().split()
    if not parts:
        return "?"
    if len(parts) == 1:
        # Single word: take first 2 letters
        return parts[0][:2] if len(parts[0]) >= 2 else parts[0]
    # Multiple words: first letter of first + first letter of last
    return parts[0][0] + parts[-1][0]


def _expand_race(code: str) -> str:
    """Expand single-letter race code to full name (e.g., 'W' -> 'White').
    
    Unknown codes pass through unchanged.
    """
    if not code:
        return "—"
    return _RACE_LABEL.get(code.upper(), code.upper())


def _expand_sex(code: str) -> str:
    """Expand single-letter sex code to full name (e.g., 'M' -> 'Male').
    
    Unknown codes pass through unchanged.
    """
    if not code:
        return "—"
    return _SEX_LABEL.get(code.upper(), code.upper())


def _pct_ordinal(pct: float | None) -> str:
    """Convert percentile (0.0-1.0) to ordinal string (e.g., 0.50 -> '50th').
    
    Handles English ordinal rules (1st, 2nd, 3rd, 21st, 22nd, 23rd, 11th-13th exception).
    Returns '0th' for None or 0.
    """
    if pct is None or pct <= 0:
        return "0th"
    n = int(round(pct * 100))
    if n > 100:
        n = 100
    # English ordinal suffix rules.
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        last = n % 10
        if last == 1:
            suffix = "st"
        elif last == 2:
            suffix = "nd"
        elif last == 3:
            suffix = "rd"
        else:
            suffix = "th"
    return f"{n}{suffix}"


def _rfc822(iso_date_str: str | None) -> str:
    """Convert ISO 8601 timestamp to RFC 822 format (e.g., 'Thu, 14 May 2026 17:16:37 +0000').
    
    Handles trailing 'Z' (UTC) or '+00:00' offset. Naive datetimes are treated as UTC.
    Returns empty string for unparseable input.
    """
    if not iso_date_str:
        return ""
    iso_date_str = str(iso_date_str).strip()
    # Remove trailing Z and replace +00:00 with nothing.
    iso_date_str = iso_date_str.rstrip("Z").replace("+00:00", "")
    try:
        dt = datetime.fromisoformat(iso_date_str)
        # Format: "Day, DD Mon YYYY HH:MM:SS +0000"
        day_name = dt.strftime("%a")
        month_name = dt.strftime("%b")
        return f"{day_name}, {dt.day:02d} {month_name} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0000"
    except (ValueError, AttributeError):
        return ""


def _chap_slug(chapter_label: str) -> str:
    """Slugify a chapter label for use as a CSS class or URL parameter.
    
    Converts to lowercase and replaces non-alphanumeric characters with dashes.
    """
    if not chapter_label:
        return ""
    s = str(chapter_label).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _codes_ohio_url(code: str) -> str:
    """Generate a link to the Ohio Revised Code online (codes.ohio.gov).
    
    Returns empty string if code is empty or malformed.
    """
    if not code:
        return ""
    norm = re.sub(r"[^\d.]", "", str(code))
    if not norm:
        return ""
    return f"https://codes.ohio.gov/ohio-revised-code/section-{norm}"


# ============================================================================
# Offense Classification / Tier Helpers
# ============================================================================

def _offense_for_code(code: str | None) -> dict | None:
    """Return offense dict {label, cls} for an ORC code.
    
    Extracts the chapter (first 4 chars, e.g., '2903' from '2903.02') and
    looks up in _OFFENSE_CATEGORY. Falls back to generic 'traffic' for
    unknowns to ensure templates never see a missing color class.
    """
    if not code:
        return None
    code = str(code).strip()
    # Extract chapter from code (e.g., "2903.02" -> "2903").
    m = re.match(r"(\d+)", code)
    if not m:
        return _OFFENSE_CATEGORY.get("other")
    chap = m.group(1)[:4]  # Get up to first 4 digits.
    return _OFFENSE_CATEGORY.get(chap, _OFFENSE_CATEGORY.get("other"))


def _charge_tier(charge, offenses: dict | None = None) -> dict | None:
    """Determine felony/misdemeanor tier for a charge.
    
    Returns {label: str, kind: 'felony' | 'misdemeanor'} or None.
    
    Extraction order:
    1. Degree suffix in charge description (e.g., "ASSAULT F4" -> F4)
    2. ORC lookup in offenses dict (if available)
    3. Venue inference: Common Pleas -> felony, Municipal -> misdemeanor
    4. None if no signal found
    """
    if hasattr(charge, "description") and charge.description:
        m = _DEGREE_RE.search(str(charge.description))
        if m:
            deg = m.group(1)
            kind = "felony" if deg.startswith("F") else "misdemeanor"
            return {"label": deg, "kind": kind}
    
    # Try ORC lookup.
    if offenses and hasattr(charge, "orc_code") and charge.orc_code:
        code = str(charge.orc_code).strip()
        if code.upper() != "NONE":
            from scraper import orc as orc_mod
            deg = orc_mod.degree_for(code, offenses)
            if deg and deg != "?":
                kind = "felony" if deg.startswith("F") else "misdemeanor"
                return {"label": deg, "kind": kind}
    
    # Fallback: infer from case number venue.
    if hasattr(charge, "common_pleas_case") and charge.common_pleas_case and str(charge.common_pleas_case).strip():
        return {"label": "F", "kind": "felony"}
    if hasattr(charge, "municipal_case") and charge.municipal_case and str(charge.municipal_case).strip():
        return {"label": "M", "kind": "misdemeanor"}
    
    return None


def _tier_counts(inmate, offenses: dict | None = None) -> dict[str, int]:
    """Count charges by tier for an inmate.
    
    Returns {felony: int, misdemeanor: int, unknown: int}.
    """
    counts = {"felony": 0, "misdemeanor": 0, "unknown": 0}
    for charge in inmate.charges:
        tier = _charge_tier(charge, offenses)
        if tier:
            key = "felony" if tier["kind"] == "felony" else "misdemeanor"
            counts[key] += 1
        else:
            counts["unknown"] += 1
    return counts


def _primary_tier(inmate, offenses: dict | None = None) -> dict | None:
    """Get the tier of the inmate's most serious charge.
    
    Returns {label, kind} or None if no charges have a determinable tier.
    """
    if not hasattr(inmate, "charges"):
        return None
    best_tier = None
    best_idx = len(_DEGREE_ORDER)
    for charge in inmate.charges:
        tier = _charge_tier(charge, offenses)
        if not tier or not tier.get("label"):
            continue
        deg = tier["label"]
        if deg in _DEGREE_ORDER:
            idx = _DEGREE_ORDER.index(deg)
            if idx < best_idx:
                best_tier, best_idx = tier, idx
    return best_tier


def _primary_degree(inmate, offenses: dict | None = None) -> str:
    """Get the degree (F1, M2, etc.) of the inmate's most serious charge."""
    tier = _primary_tier(inmate, offenses)
    return tier["label"] if tier else "UNK"


def _tier_max(inmate, offenses: dict | None = None) -> str:
    """Get the high-level tier (F or M) of the inmate's most serious charge."""
    tier = _primary_tier(inmate, offenses)
    if tier and tier.get("label"):
        deg = tier["label"]
        if deg.startswith("F"):
            return "F"
        elif deg.startswith("M"):
            return "M"
    return "UNK"


def _orc_frequency(code: str, offenses: dict | None = None) -> str:
    """Estimate frequency descriptor for an ORC code based on inmate roster.
    
    This is a stub; real implementation would gather statistics from data.
    """
    return "common"  # Placeholder


# ============================================================================
# Data Loading Helpers
# ============================================================================

def _load_explainers() -> dict:
    """Load explainer data from data/explainers.json.
    
    Returns {code: explanation_text, ...} or {} if file is missing/malformed.
    Used by templates to show contextual help for charge codes.
    """
    path = Path("data/explainers.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("explainers", {}) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        log.warning("Failed to parse data/explainers.json")
        return {}


def _load_caselaw_cache() -> dict:
    """Load caselaw index from data/orc_caselaw.json.
    
    Returns {code: [{name, cite}, ...], ...} or {} if file is missing/malformed.
    Used by the /statute/ page to display relevant case law.
    """
    path = Path("data/orc_caselaw.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("by_code", {}) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        log.warning("Failed to parse data/orc_caselaw.json")
        return {}
