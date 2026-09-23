# Evidence freshness report

Produced by D4 on each activation. One file per assessment: `freshness-[YYYY-MM-DD].md`. D4 reports commands and outputs. It never reports "verified" for a check it did not run.

```
EVIDENCE FRESHNESS REPORT - [UTC date of assessment]

Repository state at assessment:
  main tip: [SHA]
  Assessed release commit: [SHA]

Aged or invalidated items: [list or NONE]

For each item:
  Evidence: [run ID or file path]
  Captured: [UTC timestamp]
  Age at assessment: [days and hours]
  Test applied: [exact command, or field compared]
  Observed: [command output summary]
  Still valid if: [condition]
  Invalid if: [condition]
  Renewal action: [specific trigger or re-run, or NONE-REQUIRED with rationale]
  Decision required from: [named authority or AUTOMATED]
  Outcome: [VALID-NO-ACTION / RENEWAL-REQUIRED]
```

## Baseline for this package (assessed 2026-09-23T03:25Z)

| Item | Capture | Test | Result at baseline |
| :-- | :-- | :-- | :-- |
| CI run `35809118882` (`headSha=d9ba0678`) | 2026-09-23T02:07:48Z | `git log --since="2026-09-23T02:07:48Z" main -- . ':(exclude)data' ':(exclude)docs'` | VALID-NO-ACTION (age under one hour; empty output) |
| Pages deploy run `35809118858` | 2026-09-23T02:07:48Z | `main` tip still `d9ba0678` plus generated-only changes | VALID-NO-ACTION |
| Phase 2 lab numbers (`closure/lab-performance.json`) | 2026-09-22 | build under review unchanged | VALID-NO-ACTION as context; never field evidence |
| Manifests `tested-source-sha256.json` (1,592 paths), `artifact-sha256.json` (2,447), `inputs-before.json` (1,536), `evidence-sha256.json` (43) | 2026-09-22T21:47:46.899Z | content-addressed; no age limit | VALID-NO-ACTION, with the caveat that these do not identify a commit |
| Scheduled sweep run `35800597032` | 2026-09-23T00:07:01Z | conclusion FAILURE, pre-fix | Not usable as tip evidence; see D3 |

## Rules

1. Elapsed time is a trigger for review, not a verdict. CI evidence for a pinned commit does not decay while the commit is unchanged. The 30-day rule flags divergence, staffing change, or CI environment change; it does not invalidate evidence by itself.
2. Behavioral change is defined as the repository already defines it: `ci.yml` `paths-ignore` excludes `data/**` and `docs/**`. Generated-only commits do not invalidate a green run. This is why elapsed-time-alone was rejected: sweeps push hourly, and a rule that invalidates CI every hour is a rule that gets ignored.
3. A `RENEWAL-REQUIRED` item is ineligible for Phase 3 gate closure until renewal completes and a C-processor re-ingests.
4. D4 never re-runs CI itself and never renews an item. It names the trigger: `gh workflow run ci.yml`, or wait for the next push, or re-run `live-parity.yml`.
5. Where a command fails or a run's log is unreachable, record that as the observation. Do not substitute a plausible value.
