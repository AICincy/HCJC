# Remediation deployment runbook

## Purpose

deploy_fix.py applies and verifies the anonymized-changelog remediation. It does not push to GitHub.

The flow is:

1. Probe Git history for at least two data/current.json snapshots inside the recovery window.
2. Backfill recent missing tier/category tags from those snapshots when recovery data exists.
3. Refuse to continue when unexpected untracked files are present.
4. Commit only the remediation and recovery artifacts.
5. Run the verification gates.
6. Create a rollback commit and return exit code 2 if verification fails.

## Prerequisites

Run from the repository root with the same Python environment used by the project:

    python --version
    python -m pytest --version

Python >=3.13 is required by pyproject.toml.

## Run

    python deploy_fix.py -v
    python deploy_fix.py --days 7 -v

Skip the live sweep dry-run gate when HCSO access is unavailable:

    python deploy_fix.py --skip-dry-run -v

## Exit codes

- 0 — deployment and verification succeeded.
- 1 — a pre-deployment safety gate failed, normally because an unexpected untracked file is present.
- 2 — a post-commit verification failed and a rollback commit was attempted.

## Audit files

deploy_fix.py writes .deployment.log as newline-delimited JSON. It writes .incident_summary.json when Git history does not contain enough snapshots for the recovery path.

    cat .deployment.log | jq .
    cat .deployment.log | jq 'select(.type == "verification")'

## Manual recovery

The data-only recovery utility can be run independently:

    python scripts/backfill_anon_changelog.py --days 7 --dry-run -v
    python scripts/backfill_anon_changelog.py --days 7 -v

The utility only fills missing tier and category values on recent full rows. It does not add identifiers or reconstruct records older than the retention window.

## Review and push

After a successful run:

    git show --stat HEAD
    git status --short
    git push origin main

The deployment script never runs git push.
