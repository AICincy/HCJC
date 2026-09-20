"""URL builders for hamiltoncourtclerk.org case lookups.

JCStream does NOT scrape the clerk's site (their robots.txt explicitly
disallows ``/data/``). This module only constructs URLs that a human user can
click to view the public record at the source. The visitor passes any CAPTCHA
themselves; JCStream never touches the endpoint.

The URLs are stable enough for deep-linking — the page format has been the same
for years and is the documented public-records access path.
"""

from __future__ import annotations

import urllib.parse

BASE = "https://www.courtclerk.org"
NAME_SEARCH = f"{BASE}/data/crim_name_results.php"
CASE_SUMMARY = f"{BASE}/data/case_summary.php"


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


def case_summary_url(case_number: str) -> str:
    """Construct a case-summary URL.

    Hamilton County case numbers include slashes (e.g. ``B 23/12345``,
    ``25/CRA/00123``). The clerk's site URL-encodes them.
    """
    cleaned = case_number.strip()
    if not cleaned:
        return ""
    return f"{CASE_SUMMARY}?casenumber={urllib.parse.quote(cleaned, safe='')}"
