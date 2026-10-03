"""Maintainer-only ingest of one courtclerk.org case into
``data/courtclerk_cases.json``.

Trigger: ``.github/workflows/maintainer_case_ingest.yml`` (workflow_dispatch
only, gated to the repository owner). It replaces the retired public
issue-form path, where anyone could open an issue that auto-applied the
``case-data`` label and inject a record.

Input handling (public repository, publicly readable run logs):

* Values are read from the event payload file (``$GITHUB_EVENT_PATH``, key
  ``inputs``), never from a step ``env:`` block or an inline expression. The
  Actions runner prints every step's ``env:`` block into the step log before
  the step starts, so an env-passed value is published before any mask
  could apply.
* Every input value, and every line of a multi-line value, is masked with
  ``::add-mask::`` before anything else happens.
* Nothing derived from a value is logged. Rejections name the rule only.

Validation is the issue path's, unchanged: inputs are mapped onto the same
section keys ``scraper.ingest_issue.parse_issue_body`` produces and run
through ``build_case_record`` / ``validate_record`` / ``upsert`` /
``save_cases`` (courtclerk.org ``/data/case_summary.php`` source only, both
confirmations, field caps, ``normalize_case_number`` dedup,
``schema_version``).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import TextIO

from scraper.ingest_issue import (
    CONFIRM_HUMAN,
    CONFIRM_VERBATIM,
    CasesFileError,
    build_case_record,
    load_cases,
    save_cases,
    upsert,
    validate_record,
)

log = logging.getLogger(__name__)

# workflow_dispatch input id -> section key understood by build_case_record.
INPUT_SECTIONS = {
    "case_number": "case number",
    "defendant_name": "defendant name",
    "defendant_dob": "defendant date of birth",
    "filed_date": "filed date",
    "judge": "judge",
    "charges": "charges",
    "notes": "notes",
    "next_hearing": "next hearing",
    "disposition": "disposition",
    "source_url": "source url",
}

# Boolean inputs -> the confirmation line the issue form rendered when ticked.
CONFIRM_INPUTS = {
    "confirm_own_browser": CONFIRM_HUMAN,
    "confirm_verbatim": CONFIRM_VERBATIM,
}


def _as_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _escape_command_data(value: str) -> str:
    # Workflow-command data escaping (same as @actions/core issueCommand).
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def emit_masks(inputs: dict, out: TextIO | None = None) -> int:
    """Print ``::add-mask::`` for every input value and each of its lines.

    The runner matches masks line by line, so a multi-line value is masked
    per line as well as whole. Returns the number of mask commands written.
    """
    stream = out if out is not None else sys.stdout
    masks: set[str] = set()
    for value in inputs.values():
        text = _as_text(value)
        for candidate in (text, text.strip(), *text.splitlines()):
            for variant in (candidate, candidate.strip()):
                if variant.strip():
                    masks.add(variant)
    for mask in sorted(masks):
        stream.write(f"::add-mask::{_escape_command_data(mask)}\n")
    stream.flush()
    return len(masks)


def _truthy(value: object) -> bool:
    return _as_text(value).strip().lower() == "true"


def sections_from_inputs(inputs: dict) -> dict[str, str]:
    """Map dispatch inputs onto the section dict parse_issue_body returns."""
    sections = {key: _as_text(inputs.get(name)).strip() for name, key in INPUT_SECTIONS.items()}
    sections["confirmation"] = "\n".join(
        f"- [x] {label}" if _truthy(inputs.get(name)) else f"- [ ] {label}"
        for name, label in CONFIRM_INPUTS.items()
    )
    return sections


def read_event_inputs(event_path: str) -> dict:
    """Return the ``inputs`` object of a workflow_dispatch event payload."""
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    inputs = event.get("inputs") if isinstance(event, dict) else None
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("event payload has no workflow_dispatch inputs")
    return inputs


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        log.error("GITHUB_EVENT_PATH is not set")
        return 2
    try:
        inputs = read_event_inputs(event_path)
    except (OSError, ValueError) as exc:
        # json.JSONDecodeError is a ValueError; its message carries a
        # position, never input text.
        log.error("refusing to ingest: unreadable event payload (%s)", type(exc).__name__)
        return 2
    emit_masks(inputs)

    sections = sections_from_inputs(inputs)
    submitter = os.environ.get("GITHUB_ACTOR", "")
    record = build_case_record(sections, issue_number=0, issue_url="", submitter=submitter)
    problems = validate_record(record, sections)
    if problems:
        for p in problems:
            log.error("refusing to ingest: %s", p)
        return 3
    try:
        cases = upsert(load_cases(), record)
    except CasesFileError:
        log.error("refusing to ingest: data/courtclerk_cases.json is unreadable or malformed")
        return 4
    save_cases(cases)
    log.info("ingested 1 case record; file now holds %d", len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
