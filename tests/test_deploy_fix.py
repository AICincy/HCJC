import json
import subprocess
from pathlib import Path

import deploy_fix


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=check,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "deploy_fix.py").write_text("before\n", encoding="utf-8")
    _git(repo, "add", "deploy_fix.py")
    _git(repo, "commit", "-qm", "baseline")
    return repo


def _patch_operator(monkeypatch, repo: Path) -> None:
    monkeypatch.setattr(deploy_fix, "ROOT", repo)
    monkeypatch.setattr(deploy_fix, "LOG_PATH", repo / ".deployment.log")
    monkeypatch.setattr(deploy_fix, "INCIDENT_PATH", repo / ".incident_summary.json")
    monkeypatch.setattr(deploy_fix, "BACKFILL", repo / "scripts" / "backfill_anon_changelog.py")
    monkeypatch.setattr(deploy_fix, "ANON_PATH", repo / "data" / "anon_changelog.json")
    monkeypatch.setattr(deploy_fix, "FILES_TO_COMMIT", ("deploy_fix.py",))


def _modify_allowlisted_file(repo: Path) -> None:
    (repo / "deploy_fix.py").write_text("after\n", encoding="utf-8")


def _commit_names(repo: Path, commit: str = "HEAD") -> list[str]:
    return [line for line in _git(repo, "show", "--format=", "--name-only", commit).stdout.splitlines() if line]


def test_gate_2_rejects_prestaged_unrelated_file(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    unrelated = repo / "unrelated.txt"
    unrelated.write_text("must not ship\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")

    assert deploy_fix.gate_2_untracked_files() is False
    assert json.loads(deploy_fix.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])["unexpected_staged"] == [
        "unrelated.txt"
    ]


def test_main_commits_after_noop_backfill(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    _modify_allowlisted_file(repo)

    monkeypatch.setattr(deploy_fix, "gate_1_backfill_decision", lambda days: ("backfill", "test"))
    monkeypatch.setattr(
        deploy_fix,
        "run_backfill",
        lambda days: {"before_nulls": 0, "after_nulls": 0, "updated": 0},
    )
    monkeypatch.setattr(deploy_fix, "verify_dry_run", lambda: True)
    monkeypatch.setattr(deploy_fix, "verify_tests", lambda: True)

    assert deploy_fix.main([]) == 0
    assert _git(repo, "status", "--porcelain").stdout == ""
    assert _commit_names(repo) == ["deploy_fix.py"]
    assert "success" in deploy_fix.LOG_PATH.read_text(encoding="utf-8")


def test_main_reverts_on_verification_failure(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    _modify_allowlisted_file(repo)

    monkeypatch.setattr(deploy_fix, "gate_1_backfill_decision", lambda days: ("accept_losses", "test"))
    monkeypatch.setattr(deploy_fix, "write_incident", lambda days: None)
    monkeypatch.setattr(
        deploy_fix,
        "verify_dry_run",
        lambda: False,
    )
    monkeypatch.setattr(deploy_fix, "verify_tests", lambda: True)

    assert deploy_fix.main([]) == 2
    assert (repo / "deploy_fix.py").read_text(encoding="utf-8") == "before\n"
    assert _git(repo, "log", "-1", "--format=%s").stdout.strip().startswith("Revert")
    assert json.loads(deploy_fix.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])["rollback_status"] == "ok"


def test_main_reports_rollback_failure(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    _modify_allowlisted_file(repo)

    monkeypatch.setattr(deploy_fix, "gate_1_backfill_decision", lambda days: ("accept_losses", "test"))
    monkeypatch.setattr(deploy_fix, "write_incident", lambda days: None)
    monkeypatch.setattr(deploy_fix, "verify_dry_run", lambda: False)
    monkeypatch.setattr(deploy_fix, "verify_tests", lambda: True)
    monkeypatch.setattr(deploy_fix, "rollback", lambda commit_sha: False)

    assert deploy_fix.main([]) == 2
    assert (repo / "deploy_fix.py").read_text(encoding="utf-8") == "after\n"
    result = json.loads(deploy_fix.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])
    assert result["rollback_status"] == "fail"
