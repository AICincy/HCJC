# Sweep verification record

Maintained by D3. One file: `sweep-verification.md`. Non-blocking for LIVE-D by design.

```
SWEEP VERIFICATION RECORD

Anchored to: merge commit d9ba0678 (fixes: 25080285, b47cf77b)
Path under test: scheduled sweep publish, fresh-tip checkout, fast-forward rebase
Cadence: sweep.yml cron '0 * * * *' (Actions cron is best-effort; multi-hour gaps are expected)
Standing note owner: release readiness report, BUILD-E section

Closure event: next scheduled sweep execution after d9ba0678

Required evidence:
  Sweep CI run ID:
  Sweep CI run UTC timestamp:
  headSha is a descendant of d9ba0678: [Y/N]
  Event: [schedule]
  Conclusion: [SUCCESS / FAILURE]
  Evidence URL:

Behavior fields:
  1 Checkout resolved the tip at step time (log ref matches main tip, not the trigger SHA): [Y/N]
  2 HCSO inmate sweep step completed: [Y/N]
  3 Publisher outcome: [NO-CHANGES / SWEEP-COMMIT-PUSHED / ABORTED]
  4 No "::error::Rebase conflict while publishing generated changes; refusing merge fallback": [Y/N]
  5 Roster freeze alarm step executed (if: always()): [Y/N]
  6 Deploy staleness alarm step executed (if: always()): [Y/N]
  7 If a sweep commit was pushed, pages.yml deploy for that SHA succeeded: [Y/N or N/A]

Any N (excluding the N/A case): emit SWEEP-FAILED naming the step and its evidence.
Never emit SWEEP-VERIFIED with an unresolved field.

Statement to the release authority (copy verbatim into the activation record):
  The scheduled sweep publish path changed in this release and is not exercised by CI.
  Gate LIVE-D may proceed with this standing note in place. Deploying now means one
  automated publish path is unconfirmed until the next scheduled run. The known
  pre-fix failure mode is a self-healing publisher abort (run 35800597032), not data
  loss, and the next scheduled run confirms or refutes it.

On SWEEP-FAILED:
  Root cause class: [behavioral / infrastructure / transient]
  If behavioral: hand a defect record to D1 (defect-[SWEEP]-[ID].md) and notify D4
  that CI evidence for the tip is invalid.
```

## Rules

1. `workflow_dispatch` success does not close this record. It proves the scrape and build, not the cron-triggered publish-from-tip path.
2. `no changes` is a valid closure. The publisher's exit-0-with-no-commit branch is part of what the fix had to preserve.
3. D3 reads CI logs and run metadata. It does not re-run the sweep to manufacture a scheduled event.
4. The standing note is updated by the Phase 3 Orchestrator on SWEEP-VERIFIED, with run ID and UTC date. A LIVE-D that was already authorized and deployed is not reopened.
