"""Static regression checks for the workflow and live-parity audit.

These checks intentionally do not require PyYAML or GitHub credentials. They
scan active (non-comment) workflow directives so a future rename, floating
Action ref, or accidental trigger overlap is caught in the same test suite as
the application code.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


EXPECTED_WORKFLOWS = {
    "archive-evidence.yml",
    "ci.yml",
    "clerk_pra_packets.yml",
    "codeql.yml",
    "ingest_case_data.yml",
    "lint.yml",
    "live-parity.yml",
    "pages.yml",
    "rebuild.yml",
    "refresh_caselaw.yml",
    "staleness-watchdog.yml",
    "sweep.yml",
}


def _active_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]


def _active_text(path: Path) -> str:
    return "\n".join(_active_lines(path))


def test_workflow_inventory_is_explicit_and_lint_is_renamed():
    actual = {p.name for p in WORKFLOW_DIR.glob("*.yml")}
    assert actual == EXPECTED_WORKFLOWS
    assert "lint.yml" in actual
    assert "pylint.yml" not in actual
    assert "deno.yml" not in actual
    assert "purge_codeql_caches.yml" not in actual


def test_every_active_action_reference_is_a_full_sha():
    bad_names = ("@v4", "@latest", "@main")
    refs: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        for line in _active_lines(path):
            if "uses:" not in line:
                continue
            ref = line.split("uses:", 1)[1].strip().split()[0]
            refs.append(ref)
            assert not any(ref.endswith(bad) for bad in bad_names), f"floating action in {path.name}: {ref}"
            assert re.search(r"@[0-9a-f]{40}$", ref), f"unpinned action in {path.name}: {ref}"
    assert refs


def test_repeated_core_actions_use_one_sha_each():
    for action in ("actions/checkout", "actions/setup-python"):
        refs = set()
        for path in WORKFLOW_DIR.glob("*.yml"):
            for line in _active_lines(path):
                if f"uses: {action}@" in line:
                    refs.add(line.split(f"uses: {action}@", 1)[1].split()[0])
        assert len(refs) == 1, f"{action} has inconsistent pins: {refs}"


def test_lint_is_pull_request_only_without_side_branch_push():
    text = _active_text(WORKFLOW_DIR / "lint.yml")
    assert "branches-ignore:" not in text
    assert not re.search(r"^\s*push:", text, re.MULTILINE)
    assert re.search(r"\n\s*pull_request:\s*$", text, re.MULTILINE)
    assert "python-version: '3.14'" in text
    assert "pip install -r requirements.txt" in text
    assert "pip install ruff==0.16.7" in text
    assert "concurrency:" in text
    assert "timeout-minutes:" in text
    assert '-e ".[dev]"' not in text


def test_ci_is_main_push_only_and_does_not_duplicate_lint():
    text = _active_text(WORKFLOW_DIR / "ci.yml")
    assert re.search(r"push:\s*\n\s*branches: \[main\]", text)
    assert not re.search(r"^\s*pull_request:", text, re.MULTILINE)
    assert "ruff check ." in text
    assert "python -m pytest" in text


def test_live_parity_is_html_freshness_only():
    text = _active_text(WORKFLOW_DIR / "live-parity.yml")
    assert "name: Check published HTML freshness" in text
    assert "needs: contract" not in text
    assert "verify_live_url_parity.py" not in text
    assert "verify_public_data.py" not in text
    assert "--site https://www.aretheyinjail.com" in text
    assert "--data data/current.json" in text
    assert "--max-lag-hours 26" in text
    assert "--fail-on-live-newer" in text
    assert "--timeout 10" in text
    assert "--page index.html" in text
    assert "continue-on-error" not in text
    assert "deploy-pages" not in text


def test_live_parity_is_monday_schedule_and_manual_only():
    text = _active_text(WORKFLOW_DIR / "live-parity.yml")
    assert "cron: '40 4 * * 1'" in text
    assert "workflow_dispatch: {}" in text
    assert "permissions:\n  contents: read" in text


def test_pages_follows_sweep_without_generated_push_noise():
    text = _active_text(WORKFLOW_DIR / "pages.yml")
    assert "workflow_run:" in text
    assert "workflows: [sweep, rebuild-site]" in text
    assert "paths-ignore:" in text
    assert '"data/**"' in text
    assert '"docs/**"' in text
    assert "verify_public_data.py" in text
    assert "verify_live_url_parity.py" in text


def test_sweep_runs_twice_hourly_and_publishes_docs_with_deterministic_build():
    text = _active_text(WORKFLOW_DIR / "sweep.yml")
    assert "cron: '7,37 * * * *'" in text
    assert "python -m web.build" in text
    assert re.search(r"commit_generated_changes\.sh\s+main\s+\"[^\"]+\"\s+data/\s+docs/", text)
    assert "concurrency:" in text
    assert "timeout-minutes: 50" in text
