# Deployment specification

The normative contract for `deploy_fix.py`: conditions, data handling, logging
schema, incident tracking, rollback, and the verification phase. Written for
review by whoever owns this pipeline next.

`README_DEPLOY.md` is the operator quick-start. `DEPLOYMENT_FLOW.md` is the
step-by-step path reference. This file is the specification; where the three
disagree, this one wins and the other two are wrong.

---

## 1. Scope

### In scope

- `scraper/sweep.py` — extraction of `_anon_enrichment()` and the two fault fixes
- `tests/test_sweep.py` — six regression tests
- `data/anon_changelog.json` — bounded in-place repair of recoverable rows
- `.gitignore` — ignoring this script's run artifacts
- The runbook set itself (`deploy_fix.py` and four documents)

### Out of scope

- `data/changelog.json` — never written. It is the PII-bearing source of record.
- `data/waf_block_log.json` — append-only SHA-256-chained evidence. Per
  `AGENTS.md` it must never be hand-edited, truncated, or reformatted. This
  script does not read or write it.
- Any expired row of the anon feed. See §4.
- Pushing. The script creates local commits only.

### Architectural boundaries respected

`AGENTS.md` requires that anonymization and retention rules be preserved, that
no public historical archive of released individuals be created, and that
fail-closed handling of corrupt changelogs not be relaxed. §4 and §5 are written
against those constraints specifically.

---

## 2. Preconditions

| # | Condition | Failure mode |
|---|---|---|
| P1 | Run from the repository root; `git` available | Gate reads fail loudly |
| P2 | An interpreter that can `import pytest` | V3 fails → rollback |
| P3 | Worktree clean outside `EXPECTED_COMMIT_FILES` | Gate 2 halts, exit 1 |
| P4 | `data/anon_changelog.json` readable | Gate 1 reports zero rows, Path B |
| P5 | `scraper.orc` importable | measurement aborts, no write |

P2 deserves emphasis because it is the one that bites. `pytest` is a
`[project.optional-dependencies] dev` extra, absent from a runtime-only install.
A deployment that cannot run its own tests cannot verify anything, and under
auto-rollback an unverifiable deployment reverts itself. The script probes six
candidate interpreters and fails with setup instructions rather than silently
skipping V3.

---

## 3. Gate conditions

### Gate 1 — recovery decision

Pure function of the measured `Damage`:

```
total_rows == 0            → accept_losses  (nothing to repair)
in_window_null == 0        → accept_losses  (nothing left to repair)
repairable == 0            → accept_losses  (no surviving charge source)
otherwise                  → repair
```

Returns `(choice, reason)`; the reason string always names the counts it was
derived from, so the log entry is self-justifying.

**Inputs probed:** `data/anon_changelog.json`, `data/current.json`,
`data/orc_offenses.json`.

**Input explicitly not probed:** git history. This is a correction to an earlier
draft, and the reason is recorded here because the wrong version is plausible
and will be re-proposed by anyone who has not measured it.

> `git log --follow -p data/anon_changelog.json` returns 1,889 `inmate_number`
> hits on this repository. That is not historical roster data. The repository
> has one squashed commit (`638c889`), so those hits are the diff of the single
> commit that added the *current* file contents, and `data/current.json` has
> exactly one revision. A gate keyed on "does history contain inmate data"
> returns true, selects the backfill path, and then extracts today's roster
> while logging that it recovered a historical one. The failure is silent and
> the log looks clean.
>
> Gate 1 therefore probes the working tree, where the actual sources live, and
> reports the recoverable/unrecoverable split it finds rather than inferring
> availability from the presence of a string.

### Gate 2 — worktree

Halts (exit 1) if any modified, staged, or untracked path falls outside
`EXPECTED_COMMIT_FILES`.

The gate is a **rollback-safety precondition**, not hygiene. Rollback performs
`git reset --hard`, which destroys uncommitted work. Gate 2 is what makes that
acceptable. Disabling Gate 2 without disabling rollback converts a safety
mechanism into a data-loss mechanism; `--no-rollback` is the supported way to
run against a dirty tree.

Exclusions: the runbook files, `.gitignore`, and the two gitignored run
artifacts. `.mcp.json` is excluded for compatibility with the original runbook —
it does not exist here and is not gitignored, so its exclusion is inert.

---

## 4. Data handling contract

This is the section to read if you are reviewing for privacy risk.

### What the repair may do

Fill `tier` and `category` on a row that satisfies **all** of:

1. `tier` is currently falsy (never overwrite an existing tag)
2. `timestamp_utc` is present and `>= now - ANON_EXPIRY_DAYS`
3. `inmate_number` is present
4. that `inmate_number` resolves in `data/current.json` to an inmate whose
   primary charge normalizes to an entry in `data/orc_offenses.json` with a
   usable `title` or `degree`

Condition 3 is what makes the repair privacy-neutral: the row already holds PII,
because it is still inside the retention window by design. The repair adds two
aggregate fields to a record that already names the person. It does not extend
retention and does not re-identify anyone.

### What the repair must never do

- Add or remove a row
- Overwrite a non-null `tier` or `category`
- Write to a row past the expiry cutoff
- Write to a row lacking `timestamp_utc`, even if it has an `inmate_number` —
  without a timestamp the script cannot prove the row is inside the window, so
  filling it could extend retention. Such rows are counted and reported instead.
- Write to a row lacking `inmate_number` — it has been anonymized and there is
  nothing to join on
- Modify `data/changelog.json` or any other data file
- Alter `data/waf_block_log.json` under any circumstances

### Known anomaly in the live file

Some rows carry `inmate_number` with no `timestamp_utc`. They are neither inside
the retention window (no timestamp to test) nor fully anonymized (PII present).
The repair leaves them alone and reports the count. V2 asserts the population is
unchanged, which is the correct invariant: asserting it is *zero* would fail on
pre-existing rows this deployment did not create and does not own.

### Write mechanics

Atomic: `tmp` file plus `os.replace`, matching
`scraper.store._atomic_write_text`. A kill mid-write cannot leave a
half-written feed, which matters because this file is published.

### Classification is single-sourced

`measure_damage()` and `repair_anon_changelog()` both call `classify_row()`. An
earlier draft had two predicates that looked equivalent and disagreed by 12 rows
on live data. The script now takes a dry pass before writing and **raises if the
dry count differs from the measured count**, so any future divergence fails
loudly before mutation instead of silently miscounting afterwards.

Buckets are exhaustive and sum to the row count, which makes a disagreement
arithmetically visible.

---

## 5. Recovery ceiling

The honest number, and why it is not higher.

| Population | Rows | Null | Recoverable |
|---|---|---|---|
| In window, PII intact | 1,889 | 960 | 501 |
| Past window, PII stripped | 6,028 | 352 | 0 |
| **Total** | **7,917** | **1,312** | **501** |

501 of 960 in-window nulls is **~52%**. Of all 1,312 nulls it is **38%**.

An earlier draft of this runbook claimed the null count "should drop by >90% if
successful". That was not achievable and never was. The 811 rows that remain null
have no surviving charge source:

- **352 expired rows** — `inmate_number` stripped by `_anonymize_event()`.
  Nothing to join on. Recovery would require re-identifying people whose
  retention window has closed.
- **459 in-window rows for people already off the roster** (340 of them
  `released` events) — `inmate_number` survives, but no source maps it to a
  charge:
  - `data/changelog.json` keeps `inmate_number` on all 10,000 rows, but
    `ChangeEvent` is `event / inmate_number / name / timestamp_utc / note`. No
    charges.
  - `data/current.json` is the live roster; by definition these people are not
    on it.
  - Git history has one revision of everything. No prior roster exists.
  - `docs/data/current.json` is byte-identical to `data/current.json`. Not an
    independent snapshot.

**The ceiling drifts down over time.** The retention window is rolling, so rows
age past the cutoff continuously. Two runs minutes apart measured 503 and then
501 repairable rows because two rows crossed the boundary in between. This is
correct behaviour, not nondeterminism: a row that has expired must not be
repaired. Do not treat a falling repairable count across runs as a regression.

### Fault magnitudes, measured

Recorded so the fix can be re-validated against something other than assertion:

- Raw ORC code lookup resolves **58.0%** of the live roster's primary charges;
  `normalize_code()` resolves **98.8%**. 487 of 1,160 primary codes require
  normalization (`2925.11A`, `2903.02A1`, `4511.19A1A`, …).
- All 970 `released` rows in the feed were null before the fix, and not one
  tagged row was a release. The released-inmate fault was total, not partial.

---

## 6. Logging schema

`.deployment.log` is a JSON array, rewritten atomically after every event so
`jq '.[]'` works mid-run. Gitignored.

Every event carries `timestamp` (UTC, `%Y-%m-%dT%H:%M:%SZ`) and `type`:

```jsonc
// type: decision — a gate chose a path
{"timestamp": "…", "type": "decision", "gate": "gate_1",
 "choice": "repair", "reason": "501 of 960 in-window null rows are resolvable…",
 "total_rows": 7917, "null_rows": 1312, "repairable_now": 501, …}

// type: action — something was executed
{"timestamp": "…", "type": "action", "stage": "repair_anon_changelog",
 "status": "ok", "repaired": 501, "before_nulls": 1312, "after_nulls": 811,
 "before_pii_rows": 1889, "after_pii_rows": 1889, …}

// type: verification — a check ran
{"timestamp": "…", "type": "verification", "check": "v2_privacy_invariant",
 "passed": true, "detail": "row count and PII surface unchanged…",
 "row_count_unchanged": true, "pii_row_count_unchanged": true, …}

// type: outcome — terminal
{"timestamp": "…", "type": "outcome", "status": "success", "exit_code": 0,
 "commit": "…", "repaired": 501, "permanently_null": 811}
```

`status` on actions is one of `ok | planned | skipped | refused | fail | failed`.
`gate_1` decision events embed the full `Damage.as_dict()`, so a log entry is
sufficient to reconstruct the measurement without re-running it.

Logging failures are caught and reported to stderr. A deployment must not fail
because its audit log could not be written — but the failure is surfaced, never
swallowed silently.

Useful queries:

```bash
jq '.[] | select(.type=="decision")' .deployment.log
jq '.[] | select(.type=="verification")' .deployment.log
jq '.[] | select(.type=="verification" and .passed==false)' .deployment.log
jq '.[-1]' .deployment.log          # terminal outcome
```

---

## 7. Incident tracking

`.incident_summary.json` is written on **both** paths, at the end of a
successful verification. Gitignored.

An earlier draft wrote it only on Path B. That was wrong for the case that
actually occurs: a *partial* recovery leaves 811 rows permanently null and, under
the old rule, would have recorded no incident at all. Permanent loss is
reportable regardless of whether some rows were saved.

```jsonc
{
  "date": "2026-09-24T…Z",
  "bug_id": "tier_category_null_corruption",
  "root_causes": [
    "enrichment built from the current roster only; released inmates are never on it",
    "raw ORC subsection codes looked up against a base-section-keyed offense table"
  ],
  "fix_commit": "…",
  "damage": { /* full Damage.as_dict() */ },
  "recovery": {
    "attempted": true,
    "rows_repaired": 501,
    "rows_permanently_lost": 811,
    "recovery_ceiling_fraction": 0.5219,
    "why_not_more": "expired rows have inmate_number stripped…; the repository has one squashed commit…"
  },
  "next_steps": [ … ]
}
```

`why_not_more` is included deliberately. The first question anyone asks about a
partial recovery is why it is partial, and the answer is not obvious — it
requires knowing that `ChangeEvent` carries no charges and that git history is a
single commit. Writing it down at incident time is cheaper than reconstructing
it later.

Feed this into whatever tracking system the project uses. The counts are a
snapshot at run time and will not match a later measurement, because the
retention window rolls.

---

## 8. Verification phase

| ID | Check | Passes when | Can it fail? |
|---|---|---|---|
| V1 | `v1_null_audit` | `nulls_after == nulls_before - repaired` | Yes |
| V2 | `v2_privacy_invariant` | row count, PII row count, and anomalous-row population all unchanged | Yes |
| V3 | `v3_regression_tests` | the six enrichment tests pass offline | Yes |
| V4 | `v4_full_suite` | the whole suite passes | Yes |
| V5 | `v5_commit_contents` | commit diff ⊆ `EXPECTED_COMMIT_FILES`, and is non-empty | Yes; runs only if a commit was created |

**V1 uses exact equality, not a threshold.** A drop larger than `repaired` means
the repair touched rows it should not have — which is a privacy event, not a
bonus. The earlier draft's "should drop by >90%" was both unachievable (§5) and
the wrong shape of assertion: a threshold cannot detect over-reach.

**V3 and V4 both run.** V3 proves the fix; V4 proves the fix did not break the
shared code path it lives in. `_save_changelog_and_anon` is called from
`sweep.run()`'s `finally` block, so a regression there is expensive.

**V5 is conditional.** When no commit is created, `git diff before_head HEAD` is
empty by definition and the check would fail spuriously.

### The removed check

An earlier draft's V2 ran a sweep in dry-run mode and asserted no new nulls
appeared. It was vacuous on two independent grounds:

1. `_save_changelog_and_anon()` is called behind `if not dry_run and roster_ok:`
   in `sweep.run()`'s `finally` block. A dry run cannot write the feed, so it
   cannot produce a null. The assertion held by construction.
2. It requires a live HCSO roster. Offline it fails on network access — and under
   auto-rollback that failure reverts a correct fix.

A check that cannot fail is worse than no check: it logs `passed: true` and lends
confidence it has not earned. The current V2 asserts invariants that a buggy
repair would genuinely violate.

What the dry run was reaching for — proof that the *next live sweep* tags
released events — is only provable by a live sweep. That is post-deploy
monitoring (§10), and this script does not log a green tick for it.

### Regression tests must fail against the old code

The six tests in `tests/test_sweep.py` were verified in both directions: all six
fail against a faithful reconstruction of the pre-fix logic and all six pass
against the fix. A regression test that passes against the buggy code is
documenting behaviour, not guarding it.

---

## 9. Rollback procedure

### Automatic

Triggered by any failed verification, or by any unhandled exception in the
mutating section.

1. Restore `data/anon_changelog.json` from the pre-run backup copy.
2. If HEAD moved, `git reset --hard <before_head>`.

`git reset --hard` is destructive and is used here because Gate 2 established
there is no uncommitted work to lose. That ordering is load-bearing: Gate 2
before backup before mutation.

The script never pushes, so rollback never rewrites published history. If the
commit has already been pushed by an operator, roll back with
`git revert <sha>` instead and treat the data file separately — a revert of the
data file would undo the repair, which is probably not what you want. Restore the
data from the backup or re-run.

A failed rollback is logged `status: failed` and printed with the backup path. It
does not raise, so the exit code still reports the original failure.

### Manual

```bash
git revert <sha>                              # undo the code fix
git checkout <sha>^ -- data/anon_changelog.json   # undo the repair only
```

Re-run `python deploy_fix.py --plan` afterwards to re-measure. The repairable
count will be lower than before, because rows will have aged past the cutoff
(§5).

### `--no-rollback`

Leaves everything in place for inspection. Use it when the failure is in the
environment rather than the change — a missing `pytest`, for instance — and you
want to fix the environment and re-verify without re-doing the repair. You are
then responsible for cleanup.

---

## 10. Post-deployment monitoring

The only proof that released events are tagged *going forward* is a live sweep.

```bash
jq '[.[] | select(.event=="released" and .timestamp_utc)] |
    {n: length, tagged: [.[] | select(.tier)] | length}' data/anon_changelog.json
```

Before the fix: 0 tagged of 970. After: non-zero and climbing with each sweep.

Also confirm the in-window null count falls on live sweeps and then **plateaus
at the permanent residue**. It will not go to zero, and a monitor alerting on
"nulls > 0" would fire forever. Alert on the *trend* or on nulls among rows
written after the fix commit, not on the absolute count.

---

## 11. Exit codes

| Code | Meaning | State afterwards |
|---|---|---|
| 0 | Success, or `--plan` completed and the measurement was self-consistent | Change committed (or nothing to do) |
| 1 | Halted before any mutation | Tree untouched |
| 2 | Verification failed, or an unhandled exception | Rolled back |

`--plan` returns 1 if the dry pass and the measurement disagree, because that
means the classifiers have drifted and the script must not be run for real until
they are reconciled.

---

## 12. Idempotency

Re-running is safe and boring:

- Gate 1 finds no in-window nulls it can resolve → `accept_losses`
- The dry pass reports 0 repairable → nothing written
- `commit_fix` stages nothing → no commit, HEAD returned unchanged, V5 skipped
- V1–V4 still run and must still pass

No empty commit is created. The repair will not report a second round of
recovery; if it does, something restored the pre-fix data — check
`git log -- data/anon_changelog.json`.
