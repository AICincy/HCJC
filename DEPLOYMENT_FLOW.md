# Remediation deployment flow

## Gate 1 — recovery decision

deploy_fix.py runs:

    git log --all --since "<recovery window>" --format=%H -- data/current.json

Two or more snapshots select the backfill path. Fewer snapshots select accept-losses.

### Backfill path

scripts/backfill_anon_changelog.py:

- loads recent anon_changelog.json rows with identifiers still inside the seven-day window;
- reads historical data/current.json snapshots from Git;
- selects a nearby historical inmate record, preferring the pre-event snapshot for releases and the post-event snapshot for bookings;
- re-runs the same ORC normalization/tagging helper used by the sweep;
- writes only recovered tier and category fields.

### Accept-losses path

The deployment writes .incident_summary.json with the recent null-tag count and records that recovery was not possible from repository history.

## Gate 2 — untracked-file safety

The deployment reads:

    git status --porcelain

Only tracked modifications are allowed. .mcp.json is ignored explicitly. Any other ?? entry aborts the run with exit code 1.

## Commit

The commit includes only:

- scraper/sweep.py
- tests/test_sweep.py
- scripts/backfill_anon_changelog.py
- deploy_fix.py
- data/anon_changelog.json when the backfill changes it
- README_DEPLOY.md
- DEPLOYMENT_FLOW.md
- DEPLOYMENT_SPEC.md
- DEPLOYMENT_OVERVIEW.md
- .incident_summary.json when the accept-losses path creates it

The script never uses git add -A.

## Verification

### V1 — null-tag bound

The seven-day null-tag count recorded before backfill must not increase.

### V2 — sweep dry-run

Unless --skip-dry-run is supplied:

    python -m scraper.sweep --dry-run --max-surnames 1

The verification also checks that this operation does not increase recent null tags.

### V3 — regression suite

    python -m pytest -q

## Rollback

When any verification fails, the script runs:

    git revert --no-edit <deployment-commit>

and exits with 2.

No remote push is attempted by the deployment script.
