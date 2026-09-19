"""Parse a GitHub Issue body submitted via the case-data form and append it
to ``data/courtclerk_cases.json``.

Trigger: `.github/workflows/ingest_case_data.yml` on `issues: [opened, edited]`
with the ``case-data`` label. The workflow passes the issue body via stdin
or the ``ISSUE_BODY`` env var.

GitHub form bodies follow a predictable shape:

    ### Case number

    B 24 1234

    ### Defendant name (Last, First)

    SMITH, JOHN

    ### ...

We split on ``### `` headings and extract the first non-empty line that
isn't ``_No response_`` (GitHub's placeholder for blank optional fields).

Hardening (2026-09-19): the ingest refuses records whose ``source_url`` is
not a courtclerk.org ``/data/case_summary.php`` link, requires both human
confirmation checkboxes to be checked, normalizes case numbers before
dedup so formatting variants cannot create duplicates, and caps every
field length. Every record carries ``schema_version``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from scraper.case_match import normalize_case_number

log = logging.getLogger(__name__)

CASES_PATH = Path("data/courtclerk_cases.json")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
PLACEHOLDER = "_no response_"
SCHEMA_VERSION = 1

# courtclerk.org is never scraped (robots.txt disallows /data/); submissions
# must link the human-visited case summary page so provenance is checkable.
ALLOWED_SOURCE_HOST = "www.courtclerk.org"
ALLOWED_SOURCE_PATH_PREFIX = "/data/case_summary.php"

# (field, max characters)
FIELD_LIMITS = {
    "case_number": 40,
    "defendant_name": 120,
    "defendant_dob": 12,
    "filed_date": 12,
    "judge": 120,
    "charges_raw": 20000,
    "notes": 20000,
    "next_hearing": 40,
    "disposition": 200,
    "source_url": 500,
    "submitter": 80,
    "issue_url": 300,
}

CONFIRM_HUMAN = "i confirm this data was retrieved from courtclerk.org by my own browser"
CONFIRM_VERBATIM = "i confirm this data contains only verbatim docket information"


class CasesFileError(Exception):
    """Raised when data/courtclerk_cases.json exists but cannot be trusted."""


def parse_issue_body(body: str) -> dict[str, str]:
    """Return a dict of {section_title_lower: value} from a GitHub form body."""
    sections: dict[str, str] = {}
    parts = SECTION_RE.split(body)
    # Split yields: [preamble, heading1, content1, heading2, content2, ...]
    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip().lower()
        content = parts[i + 1].strip()
        # Strip GitHub form's "_No response_" placeholder.
        if content.lower().startswith(PLACEHOLDER):
            content = ""
        sections[heading] = content
    return sections


def _field(sections: dict[str, str], *keys: str) -> str:
    """Return the first non-empty value for any of the given heading variants."""
    for k in keys:
        v = sections.get(k.lower(), "").strip()
        if v:
            return v
    return ""


def _truncate(value: str, limit: int) -> str:
    return value[:limit]


def confirmations_checked(sections: dict[str, str]) -> bool:
    """Both required human-confirmation checkboxes must be ticked.

    GitHub renders checkboxes as ``- [x] label`` lines under the
    ``### Confirmation`` heading. An unticked box (``- [ ]``) or a missing
    section fails the check.
    """
    raw = sections.get("confirmation", "").lower()
    if not raw:
        return False
    checked = {line.strip() for line in raw.splitlines() if line.strip().startswith("- [x]")}
    return any(CONFIRM_HUMAN in line for line in checked) and any(CONFIRM_VERBATIM in line for line in checked)


def valid_source_url(url: str) -> bool:
    """Accept only https courtclerk.org /data/case_summary.php links."""
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == ALLOWED_SOURCE_HOST
        and parsed.path.startswith(ALLOWED_SOURCE_PATH_PREFIX)
    )


def build_case_record(
    sections: dict[str, str],
    issue_number: int,
    issue_url: str,
    submitter: str,
) -> dict:
    limits = FIELD_LIMITS
    return {
        "schema_version": SCHEMA_VERSION,
        "case_number": _truncate(_field(sections, "Case number"), limits["case_number"]),
        "case_number_key": normalize_case_number(_field(sections, "Case number")),
        "defendant_name": _truncate(
            _field(sections, "Defendant name (Last, First)", "Defendant name"),
            limits["defendant_name"],
        ),
        "defendant_dob": _truncate(
            _field(
                sections,
                "Defendant date of birth (MM/DD/YYYY)",
                "Defendant date of birth",
            ),
            limits["defendant_dob"],
        ),
        "filed_date": _truncate(
            _field(sections, "Filed date (MM/DD/YYYY)", "Filed date"),
            limits["filed_date"],
        ),
        "judge": _truncate(_field(sections, "Judge"), limits["judge"]),
        "charges_raw": _truncate(
            _field(
                sections,
                "Charges (one per line — ORC code, then description)",
                "Charges",
            ),
            limits["charges_raw"],
        ),
        "notes": _truncate(
            _field(sections, "Notes (verbatim docket entries only)", "Notes"),
            limits["notes"],
        ),
        "next_hearing": _truncate(
            _field(sections, "Next hearing (MM/DD/YYYY)", "Next hearing"),
            limits["next_hearing"],
        ),
        "disposition": _truncate(
            _field(sections, "Disposition", "Case disposition"),
            limits["disposition"],
        ),
        "source_url": _truncate(
            _field(
                sections,
                "Source URL (the courtclerk.org case_summary.php link)",
                "Source URL",
            ),
            limits["source_url"],
        ),
        "ingested_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "issue_number": issue_number,
        "issue_url": _truncate(issue_url, limits["issue_url"]),
        "submitter": _truncate(submitter, limits["submitter"]),
    }


def load_cases() -> list[dict]:
    if not CASES_PATH.exists():
        return []
    try:
        raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CasesFileError(f"{CASES_PATH} is unreadable ({exc})") from exc
    if not isinstance(raw, list):
        raise CasesFileError(f"{CASES_PATH} is not a JSON list")
    return raw


def save_cases(cases: list[dict]) -> None:
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(json.dumps(cases, indent=2), encoding="utf-8")


def upsert(cases: list[dict], record: dict) -> list[dict]:
    """Replace any existing case with the same normalized case number."""
    key = record.get("case_number_key") or normalize_case_number(record.get("case_number") or "")
    out = [c for c in cases if (c.get("case_number_key") or normalize_case_number(c.get("case_number") or "")) != key]
    out.append(record)
    return out


def validate_record(record: dict, sections: dict[str, str]) -> list[str]:
    """Return a list of human-readable rejection reasons (empty = accept)."""
    problems = []
    if not record["case_number"]:
        problems.append("missing Case number")
    if not record["source_url"]:
        problems.append("missing Source URL")
    elif not valid_source_url(record["source_url"]):
        problems.append("Source URL must be an https://www.courtclerk.org/data/case_summary.php link")
    if not confirmations_checked(sections):
        problems.append("both Confirmation checkboxes must be checked")
    return problems


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    body = os.environ.get("ISSUE_BODY") or sys.stdin.read()
    if not body.strip():
        log.error("no issue body provided (set ISSUE_BODY or pipe via stdin)")
        return 2
    issue_number = int(os.environ.get("ISSUE_NUMBER", "0") or 0)
    issue_url = os.environ.get("ISSUE_URL", "")
    submitter = os.environ.get("ISSUE_SUBMITTER", "")

    sections = parse_issue_body(body)
    record = build_case_record(sections, issue_number, issue_url, submitter)
    problems = validate_record(record, sections)
    if problems:
        for p in problems:
            log.error("refusing to ingest: %s", p)
        return 3
    try:
        cases = upsert(load_cases(), record)
    except CasesFileError as exc:
        log.error("refusing to ingest: %s", exc)
        return 4
    save_cases(cases)
    log.info("ingested case %s from issue #%s", record["case_number"], issue_number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
