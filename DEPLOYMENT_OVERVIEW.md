# Deployment overview

The remediation is implemented as a small operator-controlled flow around the existing sweep:

    probe Git history
          |
          +-- historical roster snapshots available --> backfill recent anon tags
          |
          +-- unavailable ----------------------------> record incident / accept loss
          |
    check unexpected untracked files
          |
    commit explicit remediation files
          |
    V1 null-tag bound
    V2 sweep dry-run
    V3 pytest
          |
          +-- all pass --> exit 0
          |
          +-- any fail -> git revert -> exit 2

## Code changes

scraper/sweep.py now centralizes anonymized-feed enrichment in _anon_enrichment(previous, current, offenses). The helper covers both rosters, normalizes subsection ORC codes, and converts unknown degrees to None.

scripts/backfill_anon_changelog.py recovers recent missing tags from historical data/current.json snapshots stored in Git.

tests/test_sweep.py adds regressions for release-only inmates, subsection-code normalization, current-record precedence, unknown handling, and malformed ORC input.

deploy_fix.py provides the operator flow, JSON audit log, incident path, commit allow-list, verification gates, and rollback.

## Important repository facts

- The sweep CLI is python -m scraper.sweep.
- The production sweep defaults to data/surnames.txt.
- The anonymized retention window is seven days.
- The sweep's list/detail guards preserve the last-good roster during degraded source access.
- The deployment script does not push to GitHub.

## Operator commands

    python deploy_fix.py -v
    git show --stat HEAD
    git push origin main

For details, see README_DEPLOY.md, DEPLOYMENT_FLOW.md, and DEPLOYMENT_SPEC.md.
