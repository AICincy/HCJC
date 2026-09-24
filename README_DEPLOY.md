# Deploying the anon-feed enrichment fix

Quick-start for whoever is running this. Read this file; the other three are
reference. For the full reasoning see `DEPLOYMENT_SPEC.md`.

## What is being deployed

A fix to `_save_changelog_and_anon()` in `scraper/sweep.py`, which builds the
`tier` and `category` tags on `data/anon_changelog.json` — the public,
PII-expiring event feed. Two independent faults produced one symptom: null
aggregate signal.

1. **Released inmates were never tagged.** Enrichment was built from the
   *current* roster only. A `released` event is by definition about someone no
   longer on the roster, so every released row was written with `tier=None`.
2. **Subsection codes never matched.** Booking rows carry codes like
   `2925.11A`; `data/orc_offenses.json` is keyed by base section (`2925.11`).
   The raw lookup resolved 58.0% of the roster. `normalize_code()` — which
   every other consumer of that table already used — resolves 98.8%.

## Run it

```bash
python deploy_fix.py --plan     # measure and decide; changes nothing
python deploy_fix.py            # repair, commit, verify
```

`--plan` is safe and idempotent. Run it first if you have never seen this
repository. Then run without flags.

The script needs an interpreter with `pytest` importable. `pytest` is a
`[project.optional-dependencies] dev` extra, so a runtime-only install does not
have it:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python deploy_fix.py
```

Discovery order is `$JCSTREAM_PYTEST_PYTHON`, `.venv/bin/python`,
`.venv/Scripts/python.exe`, the running interpreter, `python3`, `python`. If
none can import `pytest`, verification V3 fails and the run rolls back — so fix
the environment before running rather than overriding the check.

## What it decides, and what it can actually recover

Gate 1 measures the damage and picks a path. **Both paths exit 0.** Path B is
not an error; it is the correct outcome when nothing recoverable is left.

Measured on the live data at the time of writing:

| | rows | null tier/category | recoverable |
|---|---|---|---|
| Inside the 7-day window, PII intact | 1,889 | 960 | **501** |
| Past the window, PII stripped | 6,028 | 352 | 0 |
| **Total** | **7,917** | **1,312** | **501 (38% of all nulls)** |

**The recovery ceiling is ~52% of in-window nulls, not the ">90%" claimed in an
earlier draft of this runbook.** If you are comparing against that number, the
earlier number was wrong, not this run.

The 811 rows that stay null cannot be recovered, and it is worth being precise
about why, because the obvious recovery ideas all fail:

- **Expired rows (352)** have had `inmate_number` stripped by
  `_anonymize_event()`. There is nothing left to join on. Recovering them would
  mean re-identifying people whose retention window has closed, which the repair
  refuses to do on principle.
- **In-window rows for people already released (459, of which 340 are
  `released` events)** still carry `inmate_number`, but no surviving source maps
  that number to a charge. `data/changelog.json` keeps `inmate_number`, but
  `ChangeEvent` carries only `event / inmate_number / name / timestamp_utc /
  note` — no charges.
- **Git history does not help.** This repository has a single squashed commit,
  so `data/current.json` has exactly one revision: there is no historical roster
  to mine. See the warning below.

> **Do not probe git history for recovery material here.**
> `git log --follow -p data/anon_changelog.json` returns 1,889 `inmate_number`
> hits on this repository, which looks like a rich historical source. Every one
> of those hits comes from the single commit adding the *current* file contents.
> A gate that greps history for inmate data and concludes "backfill is possible"
> gets a confident false positive, then "extracts a historical roster" that is
> just today's roster. Gate 1 probes the working tree instead and reports the
> split it actually finds.

The repair is deliberately narrow. It fills `tier`/`category` **only** on rows
that are inside the retention window and already carry PII. It never adds a row,
never removes one, never overwrites an existing tag, and never writes to an
expired row. Verified after the fact: 501 rows changed, all of them only in
`tier`/`category`, PII row count identical at 1,889.

## Reading the result

Exit `0` — success. Repair applied and verified, or nothing was left to do.

```bash
git show HEAD --stat      # review the commit
jq '.[] | select(.type=="verification")' .deployment.log
cat .incident_summary.json
```

Exit `1` — halted before touching anything. Gate 2 found uncommitted changes
outside the fix targets. This matters because rollback uses `git reset --hard`,
which is only safe if the tree was clean to start with. Commit or stash the
unrelated work and re-run.

Exit `2` — a verification failed and the change was rolled back. Find out which:

```bash
jq '.[] | select(.type=="verification" and .passed==false)' .deployment.log
```

## Verification checks

| | What it asserts |
|---|---|
| **V1** | Null count fell by *exactly* the number of rows repaired — no more, no less. |
| **V2** | Row count unchanged, PII row count unchanged, and the population of rows carrying `inmate_number` without a `timestamp_utc` unchanged. The repair must not re-identify anyone. |
| **V3** | The six enrichment regression tests pass, offline, on a real interpreter. |
| **V4** | The full suite stays green (825 tests at time of writing). The fix touches a shared code path. |
| **V5** | The commit contains only the expected files. Runs only when a commit was created. |

**There is no dry-run sweep check, on purpose.** An earlier draft verified the
fix by running a sweep in dry-run mode and asserting no new nulls. That check
was vacuous twice over: `_save_changelog_and_anon()` sits behind
`if not dry_run and roster_ok:` in `sweep.run()`, so a dry run cannot write the
feed at all and can never produce a null; and it requires a live HCSO roster,
which is unavailable offline. It has been replaced by V2, which constrains
something real.

The thing a dry run was *trying* to prove — that the next live sweep tags
released events correctly — can only be proven by a live sweep. That is a
post-deploy monitoring step, not a gate, and this script does not claim
otherwise.

## After deploying

1. Review the commit: `git show HEAD`
2. Push the branch and open a PR. This script never pushes.
3. On the **first live sweep**, confirm released events now carry tags:

   ```bash
   jq '[.[] | select(.event=="released" and .timestamp_utc)] |
       {n: length, tagged: [.[] | select(.tier)] | length}' data/anon_changelog.json
   ```

   Before the fix that ratio was 0 of 970. It should now be non-zero and climb.

4. Expect the in-window null count to fall further on its own as live sweeps
   apply the fix to new events. It will **not** fall below the 811 permanent
   nulls; those are unrecoverable and are recorded in `.incident_summary.json`.

## Re-running

Safe. A second run finds nothing to repair, stages nothing, and reports the
fix as already committed — it does not create an empty commit. It is not
destructive, but it is not interesting either: the repair is at its ceiling.

If you re-run and see `repaired: 501` again, something restored the old data.
Check `git log -- data/anon_changelog.json`.

## Flags

```
--plan         measure and decide; change nothing
--no-commit    repair the data but leave it uncommitted for review
--no-rollback  on failure, leave changes in place instead of reverting
--no-log       do not write .deployment.log
--quiet        only gate and verification results
```

`.deployment.log` and `.incident_summary.json` are gitignored — they are run
artifacts carrying a snapshot of damage counts, not source.
