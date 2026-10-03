"""Maintainer-only case ingest (scraper/ingest_dispatch.py and
.github/workflows/maintainer_case_ingest.yml).

The public issue-form path let any GitHub user inject a record. These tests
pin the replacement: workflow_dispatch only, gated to AICincy, inputs read
from the event file and masked before use, output a PR (never a push to
main), and validation identical to scraper/ingest_issue.py.
"""

from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path

import pytest

from scraper import ingest_dispatch
from scraper.ingest_dispatch import (
    emit_masks,
    main,
    read_event_inputs,
    sections_from_inputs,
)
from scraper.ingest_issue import (
    SCHEMA_VERSION,
    build_case_record,
    parse_issue_body,
    validate_record,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "maintainer_case_ingest.yml"

SOURCE = "https://www.courtclerk.org/data/case_summary.php?casenumber=B%2024%201234"

INPUTS = {
    "case_number": "B 24 1234",
    "defendant_name": "SMITH, JOHN",
    "defendant_dob": "01/15/1985",
    "filed_date": "",
    "judge": "Hon. Jane Doe",
    "charges": "2903.11 Felonious assault\n2925.11 Possession of drugs",
    "notes": "",
    "next_hearing": "06/02/2026",
    "disposition": "Bound over to grand jury",
    "source_url": SOURCE,
    "confirm_own_browser": "true",
    "confirm_verbatim": "true",
}

# The same submission as the retired issue form rendered it.
ISSUE_BODY = f"""\
### Case number

B 24 1234

### Defendant name (Last, First)

SMITH, JOHN

### Defendant date of birth (MM/DD/YYYY)

01/15/1985

### Filed date (MM/DD/YYYY)

_No response_

### Judge

Hon. Jane Doe

### Charges (one per line \u2014 ORC code, then description)

2903.11 Felonious assault
2925.11 Possession of drugs

### Notes (verbatim docket entries only)

_No response_

### Next hearing (MM/DD/YYYY)

06/02/2026

### Disposition

Bound over to grand jury

### Source URL (the courtclerk.org case_summary.php link)

{SOURCE}

### Confirmation

- [x] I confirm this data was retrieved from courtclerk.org by my own browser, not by any automated tool.
- [x] I confirm this data contains only verbatim docket information, no personal commentary or speculation.
"""

VOLATILE = {"ingested_utc", "issue_number", "issue_url", "submitter"}


def _write_event(tmp_path: Path, inputs: dict | None) -> Path:
    event = {"ref": "refs/heads/main", "workflow": ".github/workflows/maintainer_case_ingest.yml"}
    if inputs is not None:
        event["inputs"] = inputs
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event), encoding="utf-8")
    return path


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTOR", "AICincy")

    def _run(inputs: dict | None) -> int:
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(_write_event(tmp_path, inputs)))
        return main()

    return _run


def _cases(tmp_path: Path) -> list[dict]:
    raw = json.loads((tmp_path / "data" / "courtclerk_cases.json").read_text(encoding="utf-8"))
    assert set(raw) == {"cases"}
    return raw["cases"]


# --- Validation parity with the issue path ---------------------------------


def test_dispatch_record_matches_issue_form_record():
    via_dispatch = build_case_record(sections_from_inputs(INPUTS), 0, "", "AICincy")
    via_issue = build_case_record(parse_issue_body(ISSUE_BODY), 0, "", "AICincy")
    strip = lambda r: {k: v for k, v in r.items() if k not in VOLATILE}  # noqa: E731
    assert strip(via_dispatch) == strip(via_issue)
    assert via_dispatch["schema_version"] == SCHEMA_VERSION
    assert via_dispatch["case_number_key"] == "B241234"
    assert validate_record(via_dispatch, sections_from_inputs(INPUTS)) == []


@pytest.mark.parametrize(
    "override, problem",
    [
        ({"source_url": "https://evil.example/data/case_summary.php"}, "Source URL must be"),
        ({"source_url": "http://www.courtclerk.org/data/case_summary.php?x=1"}, "Source URL must be"),
        ({"source_url": "https://www.courtclerk.org/data/other.php"}, "Source URL must be"),
        ({"source_url": ""}, "missing Source URL"),
        ({"case_number": "  "}, "missing Case number"),
        ({"confirm_own_browser": "false"}, "Confirmation"),
        ({"confirm_verbatim": False}, "Confirmation"),
    ],
)
def test_dispatch_validation_rejects(override, problem):
    inputs = {**INPUTS, **override}
    sections = sections_from_inputs(inputs)
    record = build_case_record(sections, 0, "", "AICincy")
    assert any(problem in p for p in validate_record(record, sections))


def test_dispatch_accepts_boolean_confirmations():
    inputs = {**INPUTS, "confirm_own_browser": True, "confirm_verbatim": True}
    sections = sections_from_inputs(inputs)
    assert validate_record(build_case_record(sections, 0, "", "x"), sections) == []


def test_dispatch_fields_are_length_capped():
    inputs = {**INPUTS, "defendant_name": "X" * 5000, "case_number": "B 24 " + "9" * 500}
    record = build_case_record(sections_from_inputs(inputs), 0, "", "AICincy")
    assert len(record["defendant_name"]) == 120
    assert len(record["case_number"]) == 40


# --- Masking ---------------------------------------------------------------


def test_emit_masks_covers_every_value_and_each_line():
    buf = io.StringIO()
    emit_masks(INPUTS, buf)
    masks = {line.removeprefix("::add-mask::") for line in buf.getvalue().splitlines()}
    assert all(line.startswith("::add-mask::") for line in buf.getvalue().splitlines())
    for value in INPUTS.values():
        if value.strip():
            assert value.replace("%", "%25").replace("\n", "%0A") in masks
    assert "2903.11 Felonious assault" in masks
    assert "2925.11 Possession of drugs" in masks


def test_emit_masks_escapes_command_data():
    buf = io.StringIO()
    emit_masks({"notes": "50%\r"}, buf)
    out = buf.getvalue()
    assert "::add-mask::50%25%0D\n" in out
    assert "::add-mask::50%25\n" in out


# --- End to end (main) -----------------------------------------------------


def test_main_masks_first_and_never_logs_values(run_env, tmp_path, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    assert run_env(INPUTS) == 0
    out = capsys.readouterr().out
    mask_lines = [ln for ln in out.splitlines() if ln.startswith("::add-mask::")]
    assert mask_lines and out.splitlines()[: len(mask_lines)] == mask_lines
    sensitive = [v for k, v in INPUTS.items() if not k.startswith("confirm_") and v]
    for value in sensitive:
        for line in value.splitlines():
            assert line not in caplog.text
    cases = _cases(tmp_path)
    assert len(cases) == 1
    rec = cases[0]
    assert rec["schema_version"] == SCHEMA_VERSION
    assert rec["case_number"] == "B 24 1234"
    assert rec["submitter"] == "AICincy"
    assert rec["issue_url"] == "" and rec["issue_number"] == 0


def test_main_dedups_on_normalized_case_number(run_env, tmp_path):
    assert run_env(INPUTS) == 0
    assert run_env({**INPUTS, "case_number": "b-24-1234", "judge": "Hon. Other"}) == 0
    cases = _cases(tmp_path)
    assert len(cases) == 1
    assert cases[0]["judge"] == "Hon. Other"
    assert run_env({**INPUTS, "case_number": "B 24 9999"}) == 0
    assert len(_cases(tmp_path)) == 2


def test_main_rejects_invalid_without_writing(run_env, tmp_path):
    assert run_env({**INPUTS, "source_url": "https://example.com/x"}) == 3
    assert not (tmp_path / "data" / "courtclerk_cases.json").exists()


def test_main_requires_event_inputs(run_env, monkeypatch, tmp_path):
    assert run_env(None) == 2
    monkeypatch.delenv("GITHUB_EVENT_PATH")
    assert main() == 2


def test_main_refuses_corrupt_cases_file(run_env, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "courtclerk_cases.json").write_text("{not json", encoding="utf-8")
    assert run_env(INPUTS) == 4
    assert (tmp_path / "data" / "courtclerk_cases.json").read_text(encoding="utf-8") == "{not json"


def test_read_event_inputs_rejects_non_dispatch_payload(tmp_path):
    path = _write_event(tmp_path, None)
    with pytest.raises(ValueError):
        read_event_inputs(str(path))


def test_input_ids_match_workflow_inputs():
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("    inputs:\n", 1)[1].split("\npermissions:", 1)[0]
    declared = set(re.findall(r"^      ([a-z_]+):\s*$", block, re.MULTILINE))
    expected = set(ingest_dispatch.INPUT_SECTIONS) | set(ingest_dispatch.CONFIRM_INPUTS)
    assert declared == expected


# --- Workflow and intake surface -------------------------------------------


def _active(path: Path) -> str:
    return "\n".join(ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))


def test_workflow_is_dispatch_only_and_gated_to_maintainer():
    text = _active(WORKFLOW)
    triggers = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert re.findall(r"^  ([a-z_]+):", triggers, re.MULTILINE) == ["workflow_dispatch"]
    assert '[ "$ACTOR" != "AICincy" ]' in text
    assert '[ "$ACTOR_ID" != "65099975" ]' in text
    assert '[ "$TRIGGERING_ACTOR" != "AICincy" ]' in text
    assert "needs: gate" in text
    assert "github.actor == 'AICincy' && github.triggering_actor == 'AICincy'" in text
    assert "\npermissions: {}\n" in text


def test_workflow_never_exposes_inputs():
    text = _active(WORKFLOW)
    assert "inputs." not in text.split("\npermissions:", 1)[1]
    assert "github.event.inputs" not in text
    assert "run-name" not in text
    assert "GITHUB_STEP_SUMMARY" not in text
    assert "upload-artifact" not in text
    ingest_step = text.split("- name: Mask inputs, validate", 1)[1].split("\n      - ", 1)[0]
    assert "env:" not in ingest_step
    assert "run: python -m scraper.ingest_dispatch" in ingest_step


def test_workflow_opens_pr_and_never_pushes_main():
    text = _active(WORKFLOW)
    assert "BOT_DEPLOY_KEY" not in text
    assert "commit_generated_changes" not in text
    assert "HEAD:main" not in text and "HEAD:refs/heads/main" not in text
    assert 'git push -q origin "HEAD:refs/heads/${branch}"' in text
    assert 'branch="case-data/run-' in text
    assert '"repos/${GITHUB_REPOSITORY}/pulls"' in text
    assert "git add -- data/courtclerk_cases.json" in text
    assert "gh workflow run ci.yml" in text and "gh workflow run lint.yml" in text
    for wf in ("ci.yml", "lint.yml"):
        assert re.search(r"^  workflow_dispatch:\s*$", _active(WORKFLOW.parent / wf), re.MULTILINE), wf


def test_public_issue_intake_is_gone():
    gh = REPO_ROOT / ".github"
    assert not (gh / "workflows" / "ingest_case_data.yml").exists()
    assert not (gh / "ISSUE_TEMPLATE" / "case-data.yml").exists()
    for path in sorted((gh / "workflows").glob("*.yml")):
        triggers = re.split(r"\n(?=\S)", _active(path).split("\non:\n", 1)[1], maxsplit=1)[0]
        assert not re.search(r"^  issues:", triggers, re.MULTILINE), path.name
    for path in sorted((gh / "ISSUE_TEMPLATE").glob("*.yml")):
        assert "case-data" not in path.read_text(encoding="utf-8"), path.name
