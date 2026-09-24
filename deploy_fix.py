#!/usr/bin/env python3
"""Operator-side deployment orchestration for the anon-changelog remediation.

The script does not push to GitHub. It probes recovery data, performs the
7-day backfill when historical snapshots are available or the live roster can
still recover current records, commits only
the remediation files, runs verification gates, and creates a rollback commit
when a post-commit verification fails.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / ".deployment.log"
INCIDENT_PATH = ROOT / ".incident_summary.json"
BACKFILL = ROOT / "scripts" / "backfill_anon_changelog.py"
ANON_PATH = ROOT / "data" / "anon_changelog.json"

FILES_TO_COMMIT = (
    "scraper/sweep.py",
    "tests/test_sweep.py",
    "scripts/backfill_anon_changelog.py",
    "deploy_fix.py",
    "data/anon_changelog.json",
    ".incident_summary.json",
    "README_DEPLOY.md",
    "DEPLOYMENT_FLOW.md",
    "DEPLOYMENT_SPEC.md",
    "DEPLOYMENT_OVERVIEW.md",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(event_type: str, **fields: object) -> None:
    record = {"timestamp": _now(), "type": event_type, **fields}
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    logging.getLogger("deploy_fix").info("%s", json.dumps(record, sort_keys=True))


def _run(
    *args: str,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT if cwd is None else cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def _recent_null_count(days: int) -> int:
    if not ANON_PATH.exists():
        return 0
    try:
        rows = json.loads(ANON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = 0
    for row in rows if isinstance(rows, list) else []:
        if row.get("event_summary"):
            continue
        stamp = row.get("timestamp_utc")
        if not stamp:
            continue
        try:
            ts = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff and (row.get("tier") is None or row.get("category") is None):
            count += 1
    return count


def gate_1_backfill_decision(days: int) -> tuple[str, str]:
    since = (datetime.now(timezone.utc) - timedelta(days=days + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cp = _run(
        "git",
        "log",
        "--all",
        "--since",
        since,
        "--format=%H",
        "--",
        "data/current.json",
    )
    commits = [line for line in cp.stdout.splitlines() if line.strip()]
    current_available = (ROOT / "data" / "current.json").exists()
    recent_nulls = _recent_null_count(days)
    choice = "backfill" if recent_nulls > 0 and (len(commits) >= 2 or current_available) else "accept_losses"
    if choice == "backfill":
        if len(commits) >= 2:
            reason = f"found {len(commits)} historical current.json snapshots within the recovery window"
        else:
            reason = "Git history is sparse, but the live roster is available for current/booked-row recovery"
    else:
        reason = "no eligible recent null rows or no usable roster source is available"
    _log(
        "decision",
        gate="Gate 1",
        choice=choice,
        reason=reason,
        historical_snapshots=len(commits),
        live_roster_available=current_available,
        recent_nulls=recent_nulls,
    )
    return choice, reason


def gate_2_untracked_files() -> bool:
    cp = _run("git", "status", "--porcelain")
    unexpected_untracked: list[str] = []
    for line in cp.stdout.splitlines():
        if line.startswith("?? "):
            path = line[3:]
            if path != ".mcp.json":
                unexpected_untracked.append(path)

    staged = _run("git", "diff", "--cached", "--name-only").stdout.splitlines()
    unexpected_staged = [path for path in staged if path not in FILES_TO_COMMIT]
    ok = not unexpected_untracked and not unexpected_staged
    _log(
        "decision",
        gate="Gate 2",
        status="ok" if ok else "fail",
        unexpected_untracked=unexpected_untracked,
        unexpected_staged=unexpected_staged,
    )
    return ok


def run_backfill(days: int) -> dict[str, int]:
    before = _recent_null_count(days)
    cp = _run(
        sys.executable,
        "-m",
        "scripts.backfill_anon_changelog",
        "--days",
        str(days),
        "--verbose",
    )
    detail = {"stdout": cp.stdout[-2000:], "stderr": cp.stderr[-2000:]}
    _log("action", stage="backfill", status="ok", **detail)
    after = _recent_null_count(days)
    result = {"before_nulls": before, "after_nulls": after, "updated": max(0, before - after)}
    _log("verification", check="v1_changelog_integrity", passed=after <= before, detail=result)
    return result


def write_incident(days: int) -> None:
    damage = _recent_null_count(days)
    payload = {
        "date": _now(),
        "bug_id": "tier_category_null_corruption",
        "damage_count": damage,
        "recovery_attempted": False,
        "recovery_reason": "Git history did not contain enough roster snapshots for the recovery window.",
    }
    INCIDENT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _log("action", stage="incident_summary", status="ok", damage_count=damage)


def create_commit() -> str:
    existing = []
    for path in FILES_TO_COMMIT:
        if (ROOT / path).exists():
            existing.append(path)
    _run("git", "add", "--", *existing)
    staged = _run("git", "diff", "--cached", "--name-only").stdout.splitlines()
    unexpected = [path for path in staged if path not in FILES_TO_COMMIT]
    if unexpected:
        _log(
            "action",
            stage="commit_stage",
            status="fail",
            unexpected_staged=unexpected,
        )
        _run("git", "reset", "--", *staged, check=False)
        raise RuntimeError(f"staged paths outside allow-list: {unexpected}")
    _log("action", stage="commit_stage", status="ok", paths=staged)
    if not staged:
        raise RuntimeError("nothing to commit")
    msg = (
        "fix: restore anon changelog enrichment for released inmates and ORC subsections"
    )
    _run("git", "commit", "-m", msg)
    sha = _run("git", "rev-parse", "HEAD").stdout.strip()
    _log("action", stage="commit", status="ok", commit_sha=sha)
    return sha


def verify_tests() -> bool:
    cp = _run(sys.executable, "-m", "pytest", "-q", check=False)
    passed = cp.returncode == 0
    _log(
        "verification",
        check="v3_regression_tests",
        passed=passed,
        detail={"returncode": cp.returncode, "stdout": cp.stdout[-2000:], "stderr": cp.stderr[-2000:]},
    )
    return passed


def verify_dry_run() -> bool:
    before = _recent_null_count(7)
    with tempfile.TemporaryDirectory(prefix="jcstream-v2-") as tmp:
        worktree = Path(tmp) / "repo"
        add = _run(
            "git",
            "worktree",
            "add",
            "--detach",
            str(worktree),
            "HEAD",
            check=False,
        )
        if add.returncode != 0:
            _log(
                "verification",
                check="v2_sweep_dryrun",
                passed=False,
                detail={
                    "stage": "worktree_add",
                    "returncode": add.returncode,
                    "stdout": add.stdout[-2000:],
                    "stderr": add.stderr[-2000:],
                },
            )
            return False

        try:
            cp = _run(
                sys.executable,
                "-m",
                "scraper.sweep",
                "--dry-run",
                "--max-surnames",
                "1",
                check=False,
                cwd=worktree,
            )
        finally:
            remove = _run(
                "git",
                "worktree",
                "remove",
                "--force",
                str(worktree),
                check=False,
            )

    after = _recent_null_count(7)
    passed = cp.returncode == 0 and after == before and remove.returncode == 0
    _log(
        "verification",
        check="v2_sweep_dryrun",
        passed=passed,
        detail={
            "returncode": cp.returncode,
            "worktree_remove_returncode": remove.returncode,
            "nulls_before": before,
            "nulls_after": after,
            "stdout": cp.stdout[-2000:],
            "stderr": cp.stderr[-2000:],
        },
    )
    return passed


def rollback(commit_sha: str) -> bool:
    cp = _run("git", "revert", "--no-edit", commit_sha, check=False)
    ok = cp.returncode == 0
    _log(
        "action",
        stage="rollback",
        status="ok" if ok else "fail",
        commit_sha=commit_sha,
        stdout=cp.stdout[-2000:],
        stderr=cp.stderr[-2000:],
    )
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the anon-changelog remediation deployment flow.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--skip-dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    choice, _ = gate_1_backfill_decision(args.days)
    baseline = _recent_null_count(args.days)
    _log("decision", gate="baseline", recent_null_count=baseline)

    if not gate_2_untracked_files():
        logging.getLogger("deploy_fix").error("unexpected untracked files detected; refusing to deploy")
        return 1

    if choice == "backfill":
        run_backfill(args.days)
    else:
        write_incident(args.days)

    commit_sha = create_commit()

    v1 = _recent_null_count(args.days) <= baseline
    v2 = True if args.skip_dry_run else verify_dry_run()
    v3 = verify_tests()
    _log("verification", check="v1_post_commit_null_bound", passed=v1, detail={"baseline": baseline, "current": _recent_null_count(args.days)})

    if v1 and v2 and v3:
        _log("result", status="success", commit_sha=commit_sha)
        return 0

    rollback_ok = rollback(commit_sha)
    _log(
        "result",
        status="failure",
        commit_sha=commit_sha,
        rollback_status="ok" if rollback_ok else "fail",
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
