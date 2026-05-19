"""Static classification data + the lightweight regex used to detect explicit
charge-degree suffixes. Lives outside web/build.py so the orchestrator's file
size doesn't include 100+ lines of pure-data lookup tables. Imported by
web/build.py; consumers use the underscore-prefixed names exactly as they
appeared in build.py — no rename — so test_build.py's `build._FOO` accesses
keep resolving after we re-export at the bottom of build.py.

Constants here are read-only at runtime; they're hand-curated reference data,
not anything sourced from the live HCSO feed. To add an offense category, edit
the dict here and `data/orc_offenses.json` (which jcstream-orc-curator owns).
"""
from __future__ import annotations

import re


_DEGREE_RE = re.compile(r"\b(F[1-5]|M[1-4]|MM)\b\s*$")


# Coarse chapter labels — fallback only, for ORC sections not in the fine
# offense map below.
_CHAPTER_LABEL = {
    "2903": ("offense against persons", "2903"),
    "2905": ("kidnapping",              "2903"),
    "2907": ("sex offense",             "2903"),
    "2909": ("damage / arson",          "2911"),
    "2911": ("burglary / robbery",      "2911"),
    "2913": ("theft / fraud",           "2913"),
    "2917": ("disorderly",              "traffic"),
    "2919": ("family / domestic",       "family"),
    "2921": ("obstruction",             "traffic"),
    "2923": ("weapons",                 "2923"),
    "2925": ("drugs",                   "2925"),
}

# Fine-grained offense categories keyed on the normalized ORC section.
# (label, css-class). Color tracks severity feel, NOT chapter number — so
# Murder (red) and simple Assault (gray) never share a tag. cls reuses the
# existing chapter palette classes: 2903=red, 2911/2923=amber, 2913=teal,
# 2925=plum, family=tan, traffic=gray.
_OFFENSE_CATEGORY = {
    # homicide
    "2903.01": ("homicide",            "2903"), "2903.02": ("homicide", "2903"),
    "2903.03": ("homicide",            "2903"), "2903.04": ("homicide", "2903"),
    "2903.06": ("vehicular homicide",  "2903"), "2903.08": ("vehicular assault", "2903"),
    # assault — felony vs. misdemeanor split
    "2903.11": ("felonious assault",   "2903"), "2903.12": ("felonious assault", "2903"),
    "2903.18": ("strangulation",       "2903"),
    "2903.13": ("assault",             "traffic"), "2903.14": ("negligent assault", "traffic"),
    "2903.21": ("menacing / stalking", "traffic"), "2903.211": ("menacing / stalking", "traffic"),
    "2903.22": ("menacing / stalking", "traffic"),
    # kidnapping
    "2905.01": ("kidnapping / abduction", "2903"), "2905.02": ("kidnapping / abduction", "2903"),
    "2905.03": ("unlawful restraint",  "traffic"),
    # sex offenses — rape/sexual assault vs. lesser
    "2907.02": ("rape",                "2903"),
    "2907.03": ("sexual assault",      "2903"), "2907.04": ("sexual assault", "2903"),
    "2907.05": ("sexual assault",      "2903"),
    "2907.06": ("sex offense",         "traffic"), "2907.07": ("sex offense", "traffic"),
    "2907.09": ("public indecency",    "traffic"), "2907.25": ("prostitution", "traffic"),
    "2907.24": ("prostitution",        "traffic"), "2907.241": ("prostitution", "traffic"),
    "2907.322": ("child sexual exploitation", "2903"), "2907.323": ("child sexual exploitation", "2903"),
    # arson / damage / riot
    "2909.02": ("arson",               "2903"), "2909.03": ("arson", "2903"),
    "2909.05": ("criminal damage",     "2911"), "2909.06": ("criminal damage", "2911"),
    "2909.07": ("criminal damage",     "2911"),
    "2917.02": ("riot",                "2903"), "2917.31": ("inducing panic", "traffic"),
    # robbery / burglary / trespass
    "2911.01": ("robbery",             "2903"), "2911.02": ("robbery", "2903"),
    "2911.11": ("burglary",            "2911"), "2911.12": ("burglary", "2911"),
    "2911.13": ("breaking and entering", "2911"), "2911.21": ("trespass", "traffic"),
    # theft / fraud
    "2913.02": ("theft",               "2913"), "2913.03": ("theft", "2913"),
    "2913.51": ("receiving stolen property", "2913"), "2913.04": ("unauthorized use of property", "2913"),
    "2913.05": ("fraud / forgery",     "2913"), "2913.11": ("fraud / forgery", "2913"),
    "2913.21": ("fraud / forgery",     "2913"), "2913.31": ("fraud / forgery", "2913"),
    "2913.30": ("fraud / forgery",     "2913"), "2913.40": ("fraud / forgery", "2913"),
    "2913.41": ("fraud / forgery",     "2913"), "2913.49": ("identity fraud", "2913"),
    # public order
    "2917.11": ("disorderly conduct",  "traffic"), "2917.21": ("telecom harassment", "traffic"),
    # family / domestic
    "2919.25": ("domestic violence",   "family"), "2919.27": ("protection-order violation", "family"),
    "2919.22": ("child endangering",   "family"),
    # obstruction / tampering
    "2921.04": ("tampering / intimidation", "traffic"), "2921.12": ("tampering / intimidation", "traffic"),
    "2921.13": ("falsification",        "traffic"),
    "2921.29": ("obstruction / resisting", "traffic"), "2921.31": ("obstruction / resisting", "traffic"),
    "2921.33": ("obstruction / resisting", "traffic"),
    "2921.331": ("failure to comply",  "traffic"),
    "2921.34": ("escape / contraband", "traffic"), "2921.36": ("escape / contraband", "traffic"),
    "2921.38": ("escape / contraband", "traffic"),
    # weapons
    "2923.02": ("attempt",             "traffic"),
    "2923.12": ("weapons",             "2923"), "2923.13": ("weapons under disability", "2923"),
    "2923.15": ("weapons",             "2923"), "2923.16": ("weapons", "2923"),
    "2923.17": ("weapons",             "2923"), "2923.211": ("weapons", "2923"),
    "2923.24": ("possessing criminal tools", "2923"),
    "2923.161": ("discharging firearm", "2903"), "2923.162": ("discharging firearm", "2903"),
    # drugs
    "2925.03": ("drug trafficking",    "2925"), "2925.04": ("drug trafficking", "2925"),
    "2925.05": ("drug trafficking",    "2925"),
    "2925.11": ("drug possession",     "2925"), "2925.12": ("drug possession", "2925"),
    "2925.13": ("drug possession",     "2925"),
    "2925.14": ("drug paraphernalia",  "traffic"),
    "2925.22": ("drug fraud",          "2913"), "2925.23": ("drug fraud", "2913"),
    "2925.24": ("drug fraud",          "2913"),
    # probation / sex-offender registry / contempt
    "2951.08": ("probation violation", "traffic"),
    "2950.04": ("sex-offender registry", "2903"), "2950.05": ("sex-offender registry", "2903"),
    "2705.01": ("contempt of court",   "traffic"),
    # driving / traffic
    "4510.11": ("driving offense",     "traffic"), "4510.111": ("driving offense", "traffic"),
    "4510.12": ("driving offense",     "traffic"), "4510.14": ("driving offense", "traffic"),
    "4510.16": ("driving offense",     "traffic"), "4510.037": ("driving offense", "traffic"),
    "4510.21": ("driving offense",     "traffic"),
    "4511.19": ("OVI / DUI",           "traffic"), "4511.20": ("reckless operation", "traffic"),
    "4511.21": ("speeding",            "traffic"),
    "4549.02": ("hit-skip",            "traffic"), "4549.08": ("driving offense", "traffic"),
    "4301.62": ("open container",      "traffic"),
}

# severity rank for choosing an inmate's "primary" offense (lower = more serious)
_CLS_RANK = {"2903": 0, "2911": 1, "2923": 1, "2913": 2, "2925": 2, "family": 1, "traffic": 5}

# Statutory-max ladder labels keyed on degree, for the severity-ladder visual.
_TIER_MAX = {
    "F1": "life / 11y",
    "F2": "8 yrs",
    "F3": "5 yrs",
    "F4": "18 mo",
    "F5": "12 mo",
    "M1": "180 d",
    "M2": "90 d",
    "M3": "60 d",
    "M4": "30 d",
    "MM": "fine",
}

_RACE_LABEL = {"W": "White", "B": "Black", "H": "Hispanic", "A": "Asian",
               "I": "American Indian / Alaska Native", "P": "Pacific Islander",
               "U": "Unknown", "O": "Other", "": "—"}
_SEX_LABEL = {"M": "Male", "F": "Female", "U": "Unknown", "": "—"}

_MIN_MONTH_SIZE = 3   # months smaller than this get folded into "Earlier bookings"


# ----- Functions moved from web/build.py (arch-F1) ---------------------------
from collections import defaultdict
from datetime import datetime, timezone
import email.utils
import json
from pathlib import Path

from scraper import orc as orc_mod
from scraper.models import Inmate

def _offense_for_code(code: str) -> dict | None:
    """Return {label, cls} for an ORC section, fine map first then chapter."""
    norm = orc_mod.normalize_code(code) if code else ""
    if not norm or norm.upper() == "NONE":
        return None
    if norm in _OFFENSE_CATEGORY:
        label, cls = _OFFENSE_CATEGORY[norm]
        return {"label": label, "cls": cls}
    chapter = norm.split(".")[0][:4]
    if chapter in _CHAPTER_LABEL:
        label, cls = _CHAPTER_LABEL[chapter]
        return {"label": label, "cls": cls}
    if chapter.startswith("45") or chapter.startswith("50"):
        return {"label": "traffic / civil", "cls": "traffic"}
    if chapter.startswith("29") or chapter.startswith("39"):
        return {"label": "other criminal", "cls": "traffic"}
    return {"label": "other", "cls": "traffic"}

def _orc_frequency(all_inmates: list[Inmate]) -> dict[str, int]:
    """Map ``orc_code -> # of inmates currently charged under that code``."""
    out: dict[str, int] = {}
    for inm in all_inmates:
        seen_codes: set[str] = set()
        for c in inm.charges:
            code = orc_mod.normalize_code(c.orc_code)
            if code and code not in seen_codes:
                seen_codes.add(code)
        for code in seen_codes:
            out[code] = out.get(code, 0) + 1
    return out

def _codes_ohio_url(code: str) -> str:
    norm = orc_mod.normalize_code(code)
    if not norm:
        return ""
    return f"https://codes.ohio.gov/ohio-revised-code/section-{norm}"

def _chap_slug(label: str) -> str:
    """Make a URL-friendly slug from a chapter label."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")

def _charge_tier(charge, offenses: dict | None = None) -> dict | None:
    """Tier for a single charge: explicit degree suffix > ORC default > court venue.

    A NONE-coded charge (hold / warrant with no statutory charge yet) still
    carries a venue signal — a Common Pleas case# means felony court, a
    Municipal case# means misdemeanor court — so we don't bail on it.
    """
    if offenses is None:
        offenses = orc_mod.load_offenses()
    code = (getattr(charge, "orc_code", "") or "").strip()
    desc = (getattr(charge, "description", "") or "").strip()
    if code and code.upper() != "NONE":
        m = _DEGREE_RE.search(desc)
        if m:
            deg = m.group(1)
            return {"label": deg, "kind": "felony" if deg.startswith("F") else "misdemeanor"}
        deg = orc_mod.degree_for(code, offenses)
        if deg and deg != "?":
            return {"label": deg, "kind": "felony" if deg.startswith("F") else "misdemeanor"}
    # Venue fallback (also covers NONE-coded holds).
    if (getattr(charge, "common_pleas_case", "") or "").strip():
        return {"label": "F", "kind": "felony"}
    if (getattr(charge, "municipal_case", "") or "").strip():
        return {"label": "M", "kind": "misdemeanor"}
    return None

def _tier_counts(inmate: Inmate, offenses: dict | None = None) -> dict:
    """Count this inmate's charges by tier, using the most authoritative signal
    available for each charge:

      1. Explicit degree suffix in the HCSO description (e.g., '... F2').
      2. ORC code mapped through data/orc_offenses.json (statute default).
      3. Court venue: Common Pleas case# => felony, Municipal case# => misd.
         (Venue alone is unreliable — felony arraignments happen at municipal
         court before transfer, which is what was causing felonious assault
         and strangulation to be miscategorized as misdemeanors.)
    """
    if offenses is None:
        offenses = orc_mod.load_offenses()
    felony = misd = unknown = 0
    for c in inmate.charges:
        ct = _charge_tier(c, offenses)
        decided = ct["kind"] if ct else None
        # Skip rows that carry no charge AND no venue signal at all (truly blank).
        if decided is None:
            code = (c.orc_code or "").strip()
            if (not code or code.upper() == "NONE") and not (c.common_pleas_case or "").strip() and not (c.municipal_case or "").strip() and not (c.description or "").strip():
                continue
        if decided == "felony":
            felony += 1
        elif decided == "misdemeanor":
            misd += 1
        else:
            unknown += 1
    return {"felony": felony, "misdemeanor": misd, "unknown": unknown}

def _primary_tier(inmate: Inmate) -> dict | None:
    """Most-serious tier label for the inmate card, with charge count."""
    # Explicit-degree pass kept for the rare "...MM" / "...F2" suffix.
    order = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    best_idx, best = 99, None
    for c in inmate.charges:
        m = _DEGREE_RE.search((c.description or "").strip())
        if m:
            i = order.index(m.group(1))
            if i < best_idx:
                best_idx, best = i, m.group(1)
    counts = _tier_counts(inmate)

    def _result(kind: str, label: str, short: str, n: int) -> dict:
        sfx = f" ×{n}" if n > 1 else ""
        return {"label": label + sfx, "short": short + sfx, "kind": kind, "counts": counts}

    if best:
        kind = "felony" if best.startswith("F") else "misdemeanor"
        n = counts[kind] or 1
        # short corner badge: the degree itself ("F2") doubles as the label
        return _result(kind, best, best, n)
    if counts["felony"]:
        return _result("felony", "FELONY", "F", counts["felony"])
    if counts["misdemeanor"]:
        return _result("misdemeanor", "MISDEMEANOR", "M", counts["misdemeanor"])
    return None

def _primary_degree(inmate: Inmate, offenses: dict | None = None) -> str | None:
    """The most-severe specific degree (F1 ... MM) across an inmate's charges.

    Falls back through: explicit description suffix > ORC statute default >
    nothing. Used by the severity-ladder visual on the detail page so we can
    highlight the right cell even when the generic FELONY tier badge is shown."""
    if offenses is None:
        offenses = orc_mod.load_offenses()
    order = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"]
    best_idx, best = 99, None
    for c in inmate.charges:
        m = _DEGREE_RE.search((c.description or "").strip())
        deg = m.group(1) if m else orc_mod.degree_for((c.orc_code or "").strip(), offenses)
        if deg and deg in order:
            i = order.index(deg)
            if i < best_idx:
                best_idx, best = i, deg
    return best

def _tier_max(deg: str) -> str:
    return _TIER_MAX.get(deg or "", "")

def _parse_book_date(s: str) -> datetime | None:
    """Parse an HCSO booking / court date in M/D/YY or M/D/YYYY form.

    Rejects dates more than ~15 years before today (sentinel "1/1/70" /
    epoch-era values appear in the upstream feed occasionally)."""
    if not s:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(s.strip(), fmt)
            if d < datetime(datetime.now().year - 15, 1, 1):
                return None
            return d
        except ValueError:
            continue
    return None

def _display_date(s: str) -> str:
    """Render a date string for the user — '—' when the source value parses as
    a sentinel (e.g. 1/1/70). Falls back to the raw text otherwise."""
    if not s:
        return "—"
    if _parse_book_date(s) is None:
        return "—"
    return s.strip()

def _parse_bond_amount(s: str) -> int | None:
    """Parse a bond string like '$25,000' into an int. Returns None when blank."""
    if not s:
        return None
    m = re.search(r"\$?([\d,]+(?:\.\d{2})?)", s)
    if not m:
        return None
    try:
        return int(float(m.group(1).replace(",", "")))
    except ValueError:
        return None

def _parse_md_yy(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None

def _short_month_label(month_label: str) -> str:
    """'May 2026' -> 'May '26'. Used in the sticky chip nav."""
    parts = month_label.split()
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
        return f"{parts[0][:3]} '{parts[1][-2:]}"
    return month_label

def _approx_age(dob: str) -> int | None:
    """Approximate age from a M/D/YY date of birth. For 2-digit years, prefer
    20xx when that year is in the past; otherwise fall back to 19xx. Roster
    inmates skew young, and the prior 'prefer 19xx if 14+ years ago' rule
    misclassified DOBs like 1/16/07 as 1907 (age 119) instead of 2007 (age 19)."""
    if not dob:
        return None
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$", dob)
    if not m:
        return None
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        current_year = datetime.now().year
        yr = 2000 + yr if (2000 + yr) <= current_year else 1900 + yr
    try:
        b = datetime(yr, mo, da)
    except ValueError:
        return None
    now = datetime.now()
    age = now.year - b.year - ((now.month, now.day) < (b.month, b.day))
    return age if 0 < age < 120 else None

def _booking_seq(booking_number: str) -> str:
    """'26002740' -> "Hamilton County booking #2,740 of 2026"."""
    bn = (booking_number or "").strip()
    m = re.match(r"(\d{2})(\d{4,})$", bn)
    if not m:
        return ""
    yy, seq = int(m.group(1)), int(m.group(2))
    year = 2000 + yy
    return f"booking #{seq:,} of {year}"

def _avatar_initials(full_name: str) -> str:
    parts = (full_name or "?").strip().split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()

def _expand_race(code: str) -> str:
    c = (code or "").strip().upper()
    return _RACE_LABEL.get(c, code or "—")

def _expand_sex(code: str) -> str:
    c = (code or "").strip().upper()
    return _SEX_LABEL.get(c, code or "—")

def _pct_ordinal(p: float) -> str:
    """Render a 0-1 percentile as a labeled ordinal like '79th', '21st', '2nd'.
    Handles the 11-13 exception and the 1/2/3 ones-place rule."""
    n = round((p or 0) * 100)
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def _rfc822(iso_ts: str | None) -> str:
    """Convert an ISO-8601 UTC timestamp to the RFC 822 form RSS 2.0 requires
    for <pubDate>/<lastBuildDate>. Returns "" on empty / unparseable input."""
    if not iso_ts:
        return ""
    s = iso_ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, AttributeError):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return email.utils.format_datetime(dt)

def _load_explainers() -> dict[str, dict]:
    """Plain-English explainers for top ORC offenses, indexed by base ORC code."""
    path = Path("data/explainers.json")
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw.get("explainers", {})
    except (json.JSONDecodeError, OSError):
        return {}
