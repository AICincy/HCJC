"""URL builders for courtclerk.org case lookups.

JCStream does NOT scrape the clerk's site (their robots.txt explicitly
disallows ``/data/``). This module only constructs URLs that a human user can
click to view the public record at the source. The visitor passes any CAPTCHA
themselves; JCStream never touches the endpoint.

Case-number formats are documented at
https://www.courtclerk.org/data/case_key.html
"""

from __future__ import annotations

import re
import urllib.parse

BASE = "https://www.courtclerk.org"
NAME_SEARCH = f"{BASE}/data/crim_name_results.php"
CASE_SUMMARY = f"{BASE}/data/case_summary.php"

# City municipal: /YY/CRA|CRB|TRD|TRC/NNNNN
# County municipal: C/YY/CRA|CRB|TRD|TRC/NNNNN
# Optional charge letter at the end is not part of the clerk lookup key.
_MUNI_RE = re.compile(
    r"^(C)?/?(\d{2})/(D|CRA|CRB|TRD|TRC)/(\d+)(?:/[A-Z])?$",
    re.IGNORECASE,
)
_CP_RE = re.compile(r"^([ABC])\s*(\d{7})(?:-[A-Z])?$", re.IGNORECASE)


def name_search_url(last: str, first: str, dob: str = "") -> str:
    """Construct a name-search URL.

    Ohio public records are searchable by last+first name; criminal cases
    require a DOB (the clerk's site says so explicitly). Without DOB only
    civil cases are returned.
    """
    params = {"lname": last.strip().upper(), "fname": first.strip().upper()}
    if dob:
        params["dob"] = dob.strip()
    return f"{NAME_SEARCH}?{urllib.parse.urlencode(params)}"


def normalize_clerk_case_number(case_number: str) -> str:
    """Rewrite an HCSO case string into the clerk lookup form.

    City municipal cases must keep the leading slash. County municipal cases
    keep the C/ prefix. Charge codes (``/A``, ``/B``) are dropped. A lone
    ``D`` category on a driving ticket is treated as ``TRD``.
    """
    cleaned = (case_number or "").strip()
    if not cleaned:
        return ""
    muni = _MUNI_RE.match(cleaned)
    if muni:
        county, year, category, number = muni.groups()
        category = category.upper()
        if category == "D":
            category = "TRD"
        if county:
            return f"C/{year}/{category}/{number}"
        return f"/{year}/{category}/{number}"
    cp = _CP_RE.match(cleaned)
    if cp:
        return f"{cp.group(1).upper()} {cp.group(2)}"
    return cleaned


def case_summary_url(case_number: str) -> str:
    """Construct a case-summary URL in the clerk's documented format."""
    cleaned = normalize_clerk_case_number(case_number)
    if not cleaned:
        return ""
    return f"{CASE_SUMMARY}?casenumber={urllib.parse.quote(cleaned, safe='')}"
