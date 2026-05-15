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
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

CASES_PATH = Path("data/courtclerk_cases.json")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
PLACEHOLDER = "_no response_"


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


def build_case_record(
    sections: dict[str, str],
    issue_number: int,
    issue_url: str,
    submitter: str,
) -> dict:
    return {
        "case_number": _field(sections, "Case number"),
        "defendant_name": _field(sections, "Defendant name (Last, First)", "Defendant name"),
        "defendant_dob": _field(sections, "Defendant date of birth (MM/DD/YYYY)", "Defendant date of birth"),
        "filed_date": _field(sections, "Filed date (MM/DD/YYYY)", "Filed date"),
        "judge": _field(sections, "Judge"),
        "charges_raw": _field(sections, "Charges (one per line — ORC code, then description)", "Charges"),
        "notes": _field(sections, "Notes (verbatim docket entries only)", "Notes"),
        "source_url": _field(sections, "Source URL (the courtclerk.org case_summary.php link)", "Source URL"),
        "ingested_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "issue_number": issue_number,
        "issue_url": issue_url,
        "submitter": submitter,
    }


def load_cases() -> list[dict]:
    if not CASES_PATH.exists():
        return []
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def save_cases(cases: list[dict]) -> None:
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_text(json.dumps(cases, indent=2), encoding="utf-8")


def upsert(cases: list[dict], record: dict) -> list[dict]:
    """Replace any existing case with the same ``case_number``, else append."""
    key = (record.get("case_number") or "").strip().upper()
    out = [c for c in cases if (c.get("case_number") or "").strip().upper() != key]
    out.append(record)
    return out


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
    if not record["case_number"]:
        log.error("issue body did not contain a Case number; refusing to ingest")
        return 3
    if not record["source_url"]:
        log.error("issue body did not contain a Source URL; refusing to ingest")
        return 3
    cases = upsert(load_cases(), record)
    save_cases(cases)
    log.info("ingested case %s from issue #%s", record["case_number"], issue_number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
