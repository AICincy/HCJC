# Deployment overview

Executive summary and integration guide for the anon-feed enrichment fix.

| Artifact | Purpose | Audience |
|---|---|---|
| `deploy_fix.py` | Orchestrator: measures, decides, repairs, commits, verifies | Operator — run this |
| `README_DEPLOY.md` | Quick-start, real numbers, what to do with each exit code | Operator — read first |
| `DEPLOYMENT_FLOW.md` | Every gate and path, how to debug or override one | Engineer |
| `DEPLOYMENT_SPEC.md` | Normative contract: conditions, logging, incident, rollback | Architect / lead |
| `DEPLOYMENT_OVERVIEW.md` | This file | Lead / stakeholder |

Where these disagree, `DEPLOYMENT_SPEC.md` wins.

---

## The problem

`_save_changelog_and_anon()` in `scraper/sweep.py` builds the `tier` and
`category` tags on `data/anon_changelog.json` — the public, PII-expiring event
feed that carries the long-term aggregate signal. Two independent faults
produced one symptom: null tags.

**1. Released inmates were never tagged.** Enrichment was built by iterating the
*current* roster. A `released` event is by definition about someone no longer on
it, so every released row was written with `tier=None`. This was total, not
partial: all 970 released rows in the feed were null, and not one tagged row was
a release.

**2. Subsection charge codes never matched.** Booking rows carry codes like
`2925.11A` and `2903.02A1`; `data/orc_offenses.json` is keyed by base section
(`2925.11`). The raw-string lookup resolved **58.0%** of the live roster's
primary charges. `normalize_code()` — already used by every other consumer of
that table — resolves **98.8%**. 487 of 1,160 primary codes needed normalizing.

Both are real and both were confirmed against live data before any code was
changed.

---

## What is recoverable, and what is not

This is the part that most needs stating plainly, because the intuitive estimate
is wrong by a wide margin.

| Population | Rows | Null tags | Recoverable |
|---|---|---|---|
| Inside the 7-day window, PII intact | 1,889 | 960 | **501** |
| Past the window, PII stripped | 6,028 | 352 | 0 |
| **Total** | **7,917** | **1,312** | **501** |

**Recovery ceiling: ~52% of in-window nulls, 38% of all nulls.**

An earlier draft of this runbook asserted the null count "should drop by >90% if
successful." That was never achievable. The 811 rows that stay null have no
surviving charge source, and each obvious recovery idea fails for a specific
reason:

- **Expired rows (352).** `_anonymize_event()` strips `inmate_number` once a row
  passes `ANON_EXPIRY_DAYS`. There is nothing left to join on. Recovering them
  would mean re-identifying people whose retention window has closed — which the
  repair refuses to do as a matter of principle, not convenience.
- **In-window rows for people already released (459, of which 340 are `released`
  events).** `inmate_number` survives, so we know *who* the event was about, but
  nothing maps that number to a charge. `data/changelog.json` retains
  `inmate_number` on all 10,000 rows, but `ChangeEvent` carries only
  `event / inmate_number / name / timestamp_utc / note` — no charges.
  `data/current.json` is the live roster, and these people are by definition not
  on it. `docs/data/current.json` is byte-identical to it, not an independent
  snapshot.
- **Git history.** The repository has a single squashed commit, so every data
  file has exactly one revision. There is no earlier roster to mine. See the
  warning below — this one actively misleads.

> ### Git history produces a confident false positive here
>
> `git log --follow -p data/anon_changelog.json` returns **1,889 `inmate_number`
> hits**. That looks like a rich historical source and it is not. Every hit comes
> from the one commit that added the *current* file contents.
>
> A gate that greps history for inmate data and concludes "backfill is possible"
> selects the recovery path, then extracts today's roster while logging that it
> recovered a historical one. The failure is silent and the audit log looks
> clean. This is why Gate 1 probes the working tree instead — where the real
> sources live — and reports the split it actually measures.

**The ceiling drifts downward over time.** The retention window rolls, so rows
age past the cutoff continuously. Two measurements minutes apart found 503 and
then 501 repairable rows, because two rows expired in between. That is correct
behaviour: an expired row must not be repaired. A falling repairable count across
runs is not a regression.

---

## The flow

```
START
  ↓
resolve interpreter (pytest is a dev extra — probe, don't assume)
  ↓
[GATE 1] measure damage from the working tree          read-only
  ├─ something recoverable → PATH A: repair
  └─ nothing recoverable   → PATH B: accept losses     (also exit 0)
  ↓
[GATE 2] worktree clean outside fix targets?           read-only
  ├─ no  → HALT, exit 1     (rollback would destroy pending work)
  └─ yes
  ↓
backup data file → DRY PASS → assert measured count == dry count
  ↓
[COMMIT] stage exactly the expected paths (skip if nothing staged)
  ↓
[VERIFY] V1 V2 V3 V4 (+V5 if a commit was created)
  ├─ all pass → write incident summary → exit 0
  └─ any fail → ROLLBACK → exit 2
```

Every step logs before it returns.

---

## The fix

**`scraper/sweep.py`** — enrichment extracted to
`_anon_enrichment(previous, current, offenses_path)`:

- merges the **previous and current** rosters, current winning as the fresher
  record, so released inmates get tagged
- routes charge codes through `normalize_code()`, so subsection codes resolve
- reports a missing degree as `None` rather than `orc`'s `"?"` placeholder, so
  downstream aggregates do not count a sentinel as a severity bucket
- degrades to empty tags on a malformed offenses file instead of raising inside
  the sweep's `finally` block

**`tests/test_sweep.py`** — six regression tests. All six were verified to
**fail against a faithful reconstruction of the pre-fix logic** and pass against
the fix. A regression test that passes against the buggy code documents
behaviour rather than guarding it.

- `test_anon_enrichment_covers_released_inmates`
- `test_anon_enrichment_normalizes_subsection_codes`
- `test_anon_enrichment_prefers_current_and_tolerates_unknowns`
- `test_anon_enrichment_reports_placeholder_degree_as_none`
- `test_anon_enrichment_tolerates_malformed_offenses_file`
- `test_released_inmate_row_lands_tagged_in_anon_changelog` (end-to-end through
  the real write path)

---

## What was corrected relative to the original plan

Recorded so the same mistakes are not re-made. Each was found by measuring
against the live repository rather than by review.

| # | Original | Problem | Corrected |
|---|---|---|---|
| 1 | Gate 1 probes git history for inmate data | Single squashed commit; 1,889 grep hits are the *current* file, not history. Confident false positive. | Probe the working tree; report the measured recoverable split |
| 2 | "Null count should drop by >90%" | Ceiling is ~52% of in-window nulls. Also a threshold cannot detect over-reach. | V1 asserts `nulls_after == nulls_before - repaired`, exactly |
| 3 | V2 = sweep dry-run shows no new nulls | Vacuous twice: `_save_changelog_and_anon` is behind `if not dry_run`, so a dry run cannot write nulls; and it needs a live roster, unavailable offline. A check that cannot fail logs `passed: true` and lends unearned confidence. | V2 asserts row count, PII surface, and anomalous-row population are unchanged |
| 4 | V3 = `python -m pytest` | `pytest` is a `[dev]` extra, absent on a fresh checkout → `No module named pytest` → auto-rollback reverts a **correct** fix | Probe six candidate interpreters; fail with setup instructions |
| 5 | Incident summary written only on Path B | The expected case is a *partial* recovery, which would have recorded no permanent loss at all | Written on both paths |
| 6 | Gate 2 excludes `.mcp.json` | File does not exist and is not gitignored; the exclusion is inert. Worse, the script's own `.deployment.log` would trip the gate. | Exclude the script's own artifacts; keep `.mcp.json` for compatibility, documented as inert |
| 7 | "Run twice → fails at staging" | Undefined behaviour | Stages nothing when nothing differs; no empty commit; V5 skipped |
| 8 | `git push origin main` | This work is on a feature branch | Script never pushes; the operator pushes the branch and opens a PR |

Two bugs were also found in the corrected script during verification and fixed
before it was run for real: measurement and repair used two predicates that
looked equivalent and disagreed by 12 rows on live data (now single-sourced
through `classify_row()`, with a pre-write assertion that they agree), and V2
initially asserted the anomalous-row population was *zero*, which would have
failed on pre-existing rows this deployment does not own (now asserts
*unchanged*).

---

## Verification results

Run against the live repository on 2026-09-24:

```
[Repair]  repaired 501 rows (nulls 1312 -> 811)
          skipped 352 expired/anonymized, 459 in-window unresolvable

[Verify]  PASS  v1_null_audit
          PASS  v2_privacy_invariant
          PASS  v3_regression_tests
          PASS  v4_full_suite
```

Independently confirmed against the pre-repair file, not via the script's own
checks:

- row count identical: 7,917 → 7,917
- rows carrying PII identical: 1,889 → 1,889
- rows changed: exactly 501, every one differing **only** in `tier`/`category`
- no existing tag overwritten
- row key-shapes identical throughout

Repository gate, per `AGENTS.md`:

- `ruff check .` — clean
- `mypy scraper web` — clean, 46 source files
- `pytest -q` — 825 passed

---

## Key decisions

**Both paths included, auto-selected.** Gate 1 measures and decides. Path B
exits 0 — it is the correct outcome when nothing recoverable remains, not an
error.

**Auto-detect, not interactive.** No prompts. Faster, auditable, and safe to run
unattended — which matters because it runs against a published data file.

**JSON audit log.** `.deployment.log` holds every decision, action, and
verification with counts embedded, so an entry is sufficient to reconstruct the
measurement without re-running. Gitignored.

**Backfill in the same commit as the fix.** One revert undoes both. The repair is
bounded and independently verifiable, so if only the data change needs undoing,
`git checkout <sha>^ -- data/anon_changelog.json` does that without touching the
code fix.

**The script never pushes.** It creates local commits and stops. Review, then
push the branch and open the PR.

---

## Integration

### Incident tracking

`.incident_summary.json` carries `damage`, `recovery.rows_permanently_lost`,
`recovery.recovery_ceiling_fraction`, and a `why_not_more` string explaining the
ceiling. Feed it into whatever the project uses.

`why_not_more` is included deliberately: the first question about a partial
recovery is why it is partial, and the answer requires knowing that `ChangeEvent`
carries no charges and that git history is a single commit. Cheaper to record at
incident time than to reconstruct later.

Counts are a snapshot and will not match a later measurement — the window rolls.

### Notification

```
Anon-feed enrichment fix deployed (<sha>)
  - released inmates now tagged; ORC subsection codes now normalize
  - 501 of 1,312 null rows repaired (the ceiling — see below)
  - 811 rows permanently null: 459 released/off-roster in-window + 352 expired
  - regression tests fail against the old code and pass against the fix
  - full suite green (825)
```

State the ceiling and the permanent count. A consumer who is told "fixed" and
then finds 811 null rows will reasonably assume the fix failed.

### Monitoring

The only proof that released events are tagged *going forward* is a live sweep:

```bash
jq '[.[] | select(.event=="released" and .timestamp_utc)] |
    {n: length, tagged: [.[] | select(.tier)] | length}' data/anon_changelog.json
```

Before: 0 of 970. After: non-zero, climbing each sweep.

**Alert on the trend, not on `nulls > 0`.** The count plateaus at the permanent
residue and never reaches zero; an absolute threshold would fire forever.

---

## Success checklist

- [ ] `python deploy_fix.py --plan` run first; measurement and dry pass agree
- [ ] Exit code 0
- [ ] V1–V4 pass (V5 if a commit was created)
- [ ] `git show HEAD --stat` lists only expected files
- [ ] `.deployment.log` has a terminal `outcome` event
- [ ] `.incident_summary.json` records the permanent count
- [ ] Branch pushed, PR opened
- [ ] First **live** sweep tags released events
- [ ] Null count falls and plateaus at the permanent residue
- [ ] Data consumers told the permanent number, not just "fixed"

---

## Go live

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python deploy_fix.py --plan      # read the numbers first
.venv/bin/python deploy_fix.py             # repair, commit, verify
git show HEAD                              # review
git push origin <branch>                   # the script never does this
```

Then watch the first live sweep.
