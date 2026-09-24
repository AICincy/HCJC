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
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (repo / "deploy_fix.py").write_text("before\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "deploy_fix.py")
    _git(repo, "commit", "-qm", "baseline")
    return repo


def _patch_operator(monkeypatch, repo: Path) -> None:
    monkeypatch.setattr(deploy_fix, "REPO_ROOT", repo)
    monkeypatch.setattr(deploy_fix, "DEPLOY_LOG", repo / ".deployment.log")
    monkeypatch.setattr(deploy_fix, "INCIDENT_FILE", repo / ".incident_summary.json")
    monkeypatch.setattr(deploy_fix, "ANON_PATH", repo / "data" / "anon_changelog.json")
    monkeypatch.setattr(deploy_fix, "FIX_TARGETS", ("deploy_fix.py",))
    monkeypatch.setattr(deploy_fix, "RUNBOOK_FILES", ())
    monkeypatch.setattr(deploy_fix, "EXPECTED_COMMIT_FILES", {"deploy_fix.py"})
    monkeypatch.setattr(deploy_fix, "KNOWN_ARTIFACTS", {".deployment.log"})


def _modify_allowlisted_file(repo: Path) -> None:
    (repo / "deploy_fix.py").write_text("after\n", encoding="utf-8")


def _commit_names(repo: Path, commit: str = "HEAD") -> list[str]:
    return [
        line
        for line in _git(repo, "show", "--format=", "--name-only", commit).stdout.splitlines()
        if line
    ]


def _audit_log() -> deploy_fix.AuditLog:
    return deploy_fix.AuditLog(deploy_fix.DEPLOY_LOG)


def test_gate_2_rejects_prestaged_unrelated_file(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    unrelated = repo / "unrelated.txt"
    unrelated.write_text("must not ship\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")

    clean, offenders = deploy_fix.gate_2_worktree(_audit_log())

    assert clean is False
    assert offenders == ["unrelated.txt"]
    event = deploy_fix.DEPLOY_LOG.read_text(encoding="utf-8").splitlines()[-1]
    assert json.loads(event)["stage"] == "gate_2_worktree"


def test_commit_fix_is_idempotent_after_noop_rerun(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    _modify_allowlisted_file(repo)

    first = deploy_fix.commit_fix(_audit_log(), "test commit")
    second = deploy_fix.commit_fix(_audit_log(), "test commit")

    assert first == second
    assert _git(repo, "status", "--porcelain").stdout == ""
    assert _commit_names(repo) == ["deploy_fix.py"]


def test_rollback_restores_data_and_head(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    data_dir = repo / "data"
    data_dir.mkdir()
    data = data_dir / "anon_changelog.json"
    data.write_text("before-data\n", encoding="utf-8")
    _git(repo, "add", "data/anon_changelog.json")
    _git(repo, "commit", "-qm", "add data")

    before_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    backup = deploy_fix.backup(data)
    data.write_text("after-data\n", encoding="utf-8")
    _modify_allowlisted_file(repo)
    new_head = deploy_fix.commit_fix(_audit_log(), "test mutation")
    assert new_head != before_head

    deploy_fix.rollback(_audit_log(), before_head, backup, allow=True)

    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before_head
    assert data.read_text(encoding="utf-8") == "before-data\n"


def test_rollback_records_failure(tmp_path: Path, monkeypatch):
    repo = _init_repo(tmp_path)
    _patch_operator(monkeypatch, repo)
    data = repo / "deploy_fix.py"
    backup = deploy_fix.backup(data)

    def fail_git(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["git", *args])

    monkeypatch.setattr(deploy_fix, "_git", fail_git)

    deploy_fix.rollback(_audit_log(), "deadbeef", backup, allow=True)

    event = json.loads(deploy_fix.DEPLOY_LOG.read_text(encoding="utf-8").splitlines()[-1])
    assert event["stage"] == "rollback"
    assert event["status"] == "failed"
