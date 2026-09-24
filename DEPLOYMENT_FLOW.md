# Deployment flow

Step-by-step reference for each gate and path in `deploy_fix.py`. This is the
debugging document: use it when you need to understand a decision, override one,
or work out why a run stopped where it did.

For orientation read `README_DEPLOY.md` first. For the full contract —
conditions, logging schema, incident tracking, rollback — see
`DEPLOYMENT_SPEC.md`.

```
START
  │
  ├─ resolve interpreter (needs pytest importable)
  │
  ▼
[GATE 1] measure damage, decide recovery path            read-only
  │
  ├─ nothing recoverable ──► PATH B: accept losses
  │                            └─ no write to the data file
  └─ something recoverable ─► PATH A: repair
                               └─ backfill tier/category in place
  │
  ▼            (--plan stops here and exits 0)
[GATE 2] worktree clean outside fix targets?             read-only
  │
  ├─ no ──► HALT, exit 1        (rollback would destroy pending work)
  └─ yes
  │
  ▼
[BACKUP] copy data/anon_changelog.json outside the repo
  │
  ▼
[DRY PASS] classify every row, change nothing
  │
  ├─ dry count != measured count ──► raise, roll back, exit 2
  └─ agree
  │
  ▼
[COMMIT] stage exactly FIX_TARGETS + RUNBOOK_FILES
  │        (skip if nothing staged — this is what makes re-runs safe)
  ▼
[VERIFY] V1 V2 V3 V4 (V5 only if a commit was created)
  │
  ├─ all pass ──► write .incident_summary.json ──► exit 0
  └─ any fail ──► ROLLBACK ──► exit 2
```

Every step appends to `.deployment.log` before it returns, so a crash still
leaves a trail up to the last completed step.

---

## Interpreter resolution

Happens first, before anything is measured, because a missing `pytest` used to
look like a broken fix.

`pytest` is a `[project.optional-dependencies] dev` extra. On a fresh checkout
with runtime dependencies only, `python -m pytest` fails with `No module named
pytest`. Under auto-rollback that failure reverts a correct fix, so the script
probes instead of assuming:

`$JCSTREAM_PYTEST_PYTHON` → `.venv/bin/python` → `.venv/Scripts/python.exe` →
`sys.executable` → `python3` → `python`

Each candidate must actually import `pytest` to be accepted. If none does, V3
fails with an actionable message rather than a bare non-zero exit.

## Gate 1 — recovery decision

**Probes:** `data/anon_changelog.json`, `data/current.json`,
`data/orc_offenses.json`. All in the working tree.

**Does not probe git history**, and that is a deliberate correction. See
"What Gate 1 does not do" below.

Every row is passed through `classify_row()`, which returns one bucket:

| Bucket | Condition | Action |
|---|---|---|
| `tagged` | already has a tier | leave alone |
| `repairable` | in window, on roster, resolves to a real tag | fill |
| `unresolvable_off_roster` | in window, but inmate gone or charge unknown | permanent loss |
| `expired_null` | anonymized (no `inmate_number`) and null | permanent loss |
| `pii_without_timestamp` | has `inmate_number`, no `timestamp_utc` | leave alone, report |
| `other` | not a dict | leave alone |

**Decision:**

- `repair` if `repairable > 0`
- `accept_losses` if the feed is empty/unreadable, if there are no in-window
  nulls, or if every in-window null is unresolvable

Both outcomes exit 0 on success. Path B is not a failure state.

### Why the buckets are not obvious

`pii_without_timestamp` exists because two predicates that look equivalent are
not. An earlier version of this script classified rows in `measure_damage()`
with one predicate and in `repair_anon_changelog()` with another, and they
disagreed by 12 rows on live data. Both now call `classify_row()`, and the
script raises before writing anything if the measured count and the dry-pass
count differ. That assertion is the reason the dry pass exists.

The bucket counts are exhaustive and sum to the file's row count, so a
disagreement is arithmetically visible rather than something you have to go
looking for.

### What Gate 1 does not do

It does not treat git history as a recovery source.

`git log --follow -p data/anon_changelog.json` on this repository returns 1,889
`inmate_number` hits. A gate that greps for those and concludes "historical
roster data is present, backfill is possible" is reading the single commit that
added the *current* file contents. The repository has one squashed commit, so
`data/current.json` has exactly one revision and there is no earlier roster to
extract. The gate would then silently "restore" today's roster as though it were
history — a false positive that looks like success in the log.

The real PII source is `data/changelog.json` in the working tree, which retains
`inmate_number` on all 10,000 rows. But `ChangeEvent` carries no charges, so it
can identify *who* an event was about without being able to say *what they were
charged with*. That is why the recovery ceiling is set by the live roster and not
by the changelog.

## Gate 2 — worktree check

**Probes:** `git diff --name-only`, `git diff --cached --name-only`,
`git ls-files --others --exclude-standard`.

**Halts (exit 1)** if anything outside `EXPECTED_COMMIT_FILES` is modified,
staged, or untracked.

This gate exists to make rollback safe, not to be tidy. Rollback uses
`git reset --hard`, which destroys uncommitted work. That is only acceptable
because Gate 2 has already proven there is none. If you disable Gate 2 you
disable that guarantee — use `--no-rollback` instead.

`.mcp.json` is in the exclusion list for compatibility with the original
runbook. It does not exist in this repository and is not gitignored; excluding
it is harmless rather than load-bearing. `.deployment.log` and
`.incident_summary.json` are gitignored and excluded.

## Dry pass

Runs the full classification and counts what it *would* change, writing nothing.
If that count differs from Gate 1's measurement the script raises immediately,
before any mutation. Cheap, and it converts a silent data-corruption class into
a loud failure.

## Backup

`data/anon_changelog.json` is copied to a temp file outside the repository
(`tempfile.mkstemp`) so a rollback can restore it even if git state is
confusing. Removed in a `finally`.

## Path A — repair

Fills `tier` and `category` in place on `repairable` rows only, then writes with
the same tmp-file + `os.replace` contract as `scraper.store._atomic_write_text`.

Constraints enforced by construction:

- never adds or removes a row
- never overwrites an existing tag (`classify_row` returns `tagged` for those)
- never writes to a row past the expiry cutoff
- never writes to a row lacking `timestamp_utc`, because without a timestamp the
  script cannot prove the row is still inside the retention window

## Path B — accept losses

No write to the data file. The dry pass still runs, so the reported numbers come
from a real classification rather than from Gate 1 alone, and V1/V2 verify the
file is byte-for-byte unchanged in effect.

`.incident_summary.json` is written on **both** paths. An earlier draft only
wrote it on Path B, which meant a partially-successful repair — the actual
expected case here — recorded no permanent loss at all. The permanent portion is
real regardless of which path ran.

## Commit

Stages exactly `FIX_TARGETS + RUNBOOK_FILES` by explicit path, never
`git add -A`, so an unexpected artifact cannot ride along. If anything outside
`EXPECTED_COMMIT_FILES` ends up staged it is unstaged and the commit is refused.

If nothing is staged, no commit is created and HEAD is returned unchanged. That
is what makes re-running safe: a second run after a successful deployment finds
the tree clean and reports "fix already committed" instead of making an empty
commit.

V5 runs only when a commit was actually created; otherwise
`git diff before_head HEAD` is empty by definition and would fail spuriously.

## Verify

| | Asserts | Notes |
|---|---|---|
| **V1** | `nulls_after == nulls_before - repaired` | Exact equality. A larger drop means the repair touched rows it should not have. |
| **V2** | Row count, PII row count, and the `inmate_number`-without-`timestamp_utc` population are all unchanged | Replaces the vacuous dry-run sweep. See below. |
| **V3** | Six enrichment regression tests pass | `-k "anon_enrichment or released_inmate_row"` on `tests/test_sweep.py` |
| **V4** | Full suite green | The fix touches a shared code path; V3 alone is not enough |
| **V5** | Commit contains only expected files | Only when a commit was created |

### The check that was removed

An earlier draft had V2 run a sweep in dry-run mode and assert no new nulls
appeared. It could not fail, for two independent reasons:

1. `_save_changelog_and_anon()` is called from `sweep.run()`'s `finally` block
   behind `if not dry_run and roster_ok:`. A dry run never writes the feed, so it
   can never produce a null. The assertion was true by construction.
2. It needs a live HCSO roster. Offline it fails on network access, which under
   auto-rollback reverts a correct fix.

A check that cannot fail is worse than no check, because it appears in the log as
`passed: true` and lends confidence it has not earned. V2 asserts something that
can actually be violated instead.

What the dry run was reaching for — proof that the *next live sweep* tags
released events — is only provable by a live sweep. That is post-deploy
monitoring, and this script says so rather than logging a green tick for it.

## Rollback

Triggered by any failed verification, or by an unhandled exception anywhere in
the mutating section.

1. Restore `data/anon_changelog.json` from the backup copy.
2. If HEAD moved, `git reset --hard <before_head>`.

Safe because Gate 2 proved there was no uncommitted work to lose. `--no-rollback`
leaves everything in place for inspection; if you use it, clean up manually.

A failed rollback is logged as `status: failed` and printed loudly with the
backup path. It does not raise, so the exit code still reflects the original
failure.

## Overriding a decision

Prefer `--plan` to inspect what would happen. To force a path, edit
`gate_1_recovery_decision()` — it is a pure function of the `Damage` dataclass
and returns `(choice, reason)`, so it can be changed without touching anything
else. Do not bypass Gate 2; use `--no-rollback` if the tree state is the problem.

Any override is recorded in `.deployment.log` as a `decision` event. If you
change the return value by hand, note the reason in the commit message, because
the log will show the code's decision and not yours.
