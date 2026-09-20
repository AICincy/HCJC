"""Match reader-submitted courtclerk case records to roster inmates.

Submissions (`data/courtclerk_cases.json`, via the case-data issue workflow)
carry a free-text ``defendant_name`` ("LAST, FIRST") and an optional
``defendant_dob``. The roster carries structured ``last_name`` /
``first_name`` / ``date_of_birth``. This module normalizes both sides and
joins them so the site build can render submissions on the right inmate
page.

Match rule: normalized last+first name must agree. When the submission
provides a date of birth, the roster DOB must agree too; records that
cannot be DOB-verified against a same-named roster entry are left
unmatched rather than risk misattribution. A name-only match (submission
without DOB, unique roster name) is returned with ``dob_verified=False``
so the template can say so.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date
from typing import Any, Protocol


class _InmateLike(Protocol):
    inmate_number: str
    last_name: str
    first_name: str
    date_of_birth: str


def normalize_case_number(case_number: str) -> str:
    """Canonical case key: uppercase alphanumeric only.

    ``B 24 1234``, ``B24-1234`` and ``b 24/1234`` all map to ``B241234``.
    """
    return re.sub(r"[^A-Z0-9]", "", (case_number or "").upper())


def normalize_name_part(part: str) -> str:
    """Uppercase letters only: ``O'Brien-Smith`` -> ``OBRIENSMITH``."""
    return re.sub(r"[^A-Z]", "", (part or "").upper())


def split_defendant_name(name: str) -> tuple[str, str]:
    """Split a ``LAST, FIRST [MIDDLE]`` submission name.

    Returns (last, first) normalized. Anything after the first token of the
    given-name side is treated as a middle name and dropped, matching how
    the roster stores middle names separately.
    """
    raw = (name or "").strip()
    if "," in raw:
        last_raw, rest = raw.split(",", 1)
    else:
        parts = raw.split()
        if len(parts) >= 2:
            last_raw, rest = parts[-1], " ".join(parts[:-1])
        elif parts:
            last_raw, rest = parts[0], ""
        else:
            return "", ""
    first_raw = rest.strip().split()[0] if rest.strip() else ""
    return normalize_name_part(last_raw), normalize_name_part(first_raw)


def normalize_dob(dob: str) -> str | None:
    """Normalize ``M/D/YY``, ``MM/DD/YYYY`` etc. to ISO ``YYYY-MM-DD``.

    Two-digit years pivot at the current century boundary, computed from
    the current year (e.g. in 2026, ``00``-``26`` map to 2000-2026,
    ``27``-``99`` to 1927-1999). Returns None when the value is empty
    or unparseable.
    """
    from datetime import date as _date

    raw = (dob or "").strip()
    if not raw or raw.upper() == "NA":
        return None
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*", raw)
    if not m:
        return None
    month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
    yy = int(year)
    if len(year) == 2:
        # Pivot at current 2-digit year: yy <= pivot -> 2000s, else 1900s
        pivot = _date.today().year % 100
        full_year = 2000 + yy if yy <= pivot else 1900 + yy
    else:
        full_year = yy
    try:
        return date(full_year, month, day).isoformat()
    except ValueError:
        return None


def _roster_case_keys(inmate: _InmateLike) -> set[str]:
    keys = set()
    for charge in getattr(inmate, "charges", None) or []:
        if isinstance(charge, dict):
            candidates = (
                charge.get("common_pleas_case"),
                charge.get("municipal_case"),
                charge.get("other_case"),
            )
        else:
            candidates = (
                getattr(charge, "common_pleas_case", None),
                getattr(charge, "municipal_case", None),
                getattr(charge, "other_case", None),
            )
        for c in candidates:
            if c:
                keys.add(normalize_case_number(str(c)))
    return keys


def match_cases_to_inmates(cases: Sequence[Any], inmates: Sequence[_InmateLike]) -> dict[str, list[dict]]:
    """Index submitted case records by matched ``inmate_number``.

    Each returned entry is the original record dict plus two annotation
    keys: ``dob_verified`` (bool) and ``case_on_booking`` (bool, whether the
    submitted case number appears among the inmate's roster charges).
    Unmatched records are omitted. Non-dict records are skipped, since
    reader-submitted payloads may contain malformed entries.
    """
    roster: dict[tuple[str, str], list[_InmateLike]] = {}
    for inmate in inmates:
        key = (normalize_name_part(inmate.last_name), normalize_name_part(inmate.first_name))
        if key[0] and key[1]:
            roster.setdefault(key, []).append(inmate)

    by_inmate: dict[str, list[dict]] = {}
    for record in cases:
        if not isinstance(record, dict):
            continue
        last, first = split_defendant_name(record.get("defendant_name") or "")
        if not last or not first:
            continue
        candidates = roster.get((last, first), [])
        if not candidates:
            continue
        sub_dob = normalize_dob(record.get("defendant_dob") or "")
        matched = None
        dob_verified = False
        if sub_dob:
            for inmate in candidates:
                if normalize_dob(inmate.date_of_birth) == sub_dob:
                    matched = inmate
                    dob_verified = True
                    break
        else:
            # No DOB on the submission: accept a name-only match against a
            # unique roster name, otherwise leave unmatched (ambiguous).
            if len(candidates) == 1:
                matched = candidates[0]
        if matched is None:
            continue
        entry = dict(record)
        entry["dob_verified"] = dob_verified
        entry["case_on_booking"] = bool(
            (record.get("case_number_key") or normalize_case_number(record.get("case_number") or ""))
            in _roster_case_keys(matched)
        )
        by_inmate.setdefault(matched.inmate_number, []).append(entry)
    return by_inmate
