# Audit — jcstream-sweep-debugger

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-sweep-debugger/SKILL.md
- **Paired agent**: .claude/agents/jcstream-sweep-debugger.md
- **Verdict**: Yellow
- **One-line summary**: Core thresholds and triage flow are accurate, but the skill misses the entire detail-page watchdog + wall-clock cap + checkpoint guards and points at a non-existent test file.

## A. Drift
- SKILL.md:69 instructs `pytest -q tests/test_sweep_guards.py` but no such file exists; guard tests live in `tests/test_sweep.py:6-12` (imports `from scraper import sweep, sweep_guards`). Command will fail.
- SKILL.md:8 cites `_sweep_looks_healthy` as in-tree; the underscore name is now only a back-compat alias at `scraper/sweep.py:65` (`_sweep_looks_healthy = sweep_looks_healthy`). The real function is `sweep_looks_healthy` in `scraper/sweep_guards.py:46`. Minor — but `grep _sweep_looks_healthy` will mislead a reader.
- SKILL.md:28 cites `scraper/sweep_guards.py:23-25` for the three thresholds. Correct as of `sweep_guards.py:23-25`.
- SKILL.md:46 says `data/history.json` is "Stubby today (≈200 bytes)" — accurate (`wc -c` returns 209 bytes), but it omits that history.json is written by `web/build.py:456-511`, *not* by the sweep, so a stale history.json points at the build, not the scraper.

## B. Coverage gaps
- **Detail-page watchdog**: `sweep_guards.py:64-101` (`check_detail_watchdog`) is a second silent-fallback path with WARN floors (`DETAIL_WATCHDOG_NAME_FLOOR=0.70`, `PHOTO_FLOOR=0.50`) and BLOCK pair (`BLOCK_MIN_SAMPLE=100`, `BLOCK_NAME_FLOOR=0.60`). Triggered at `scraper/sweep.py:197-200` and sets `roster_ok=False`. The skill never mentions it — yet "stale photos but fresh roster count" is exactly when it fires.
- **Wall-clock cap**: `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` at `scraper/sweep.py:61`, enforced at `sweep.py:152-157`. A partial roster persisted via this path will look like a "small" sweep without tripping the 50% floor; missing from the triage flow.
- **Checkpoint guard**: `scraper/sweep.py:183-196` skips intermediate `save_current` checkpoints when in-memory roster is below 50% of previous. A stuck count can come from this even though the final-write path looks fine.
- **Corrupt-snapshot bail**: `scraper/sweep.py:80-90` returns 0 on `SnapshotCorruptError` keeping the broken file in place. A new failure mode worth a triage bullet.
- **Save failure path**: `scraper/sweep.py:212-216` (`save_current` `OSError` → skip changelog & prune) — disk-full / atomic-rename failure also produces "exit 0, no commit" with a different log line.
- **Photo prune skip**: `sweep_guards.py:104-129` (`PHOTO_PRUNE_MAX_FRACTION = 0.5`) silently skips prune when >50% of photos would be deleted. Useful when the symptom is "photos for released inmates aren't disappearing".
- **Atomic write contract**: `scraper/store.py:44-54` (`_atomic_write_text` via tmp + `os.replace`) — CLAUDE.md preamble cites this, the SKILL.md does not.

## C. Trigger-phrase quality
- Current description (paraphrased): "use when investigating why a sweep didn't produce fresh data — flat roster, empty changelog, stale photos, exit-0 sweep with no commit". Triggers: "sweep didn't update", "stuck count", "no changes in changelog", "scraper looks idle".
- Issues: phrasing is solid for the obvious symptoms but won't fire on detail-watchdog symptoms ("photos missing names", "nameless inmates", "photos not updating") or on the new wall-clock/checkpoint paths ("partial sweep", "sweep timed out", "sweep keeps bailing").
- Proposed rewording: add "stale photos", "partial sweep", "sweep bailed", "nameless records", "detail watchdog" to the trigger phrase list.

## D. Applicability
- Domain is alive — `scraper/sweep.py`, `scraper/sweep_guards.py`, `data/{current,changelog,history}.json`, and `.github/workflows/sweep.yml` are all current and on the 30-min cron; skill should be kept.

## Recommended fixes (priority order)
1. Fix the broken pytest invocation at SKILL.md:69 — point at `tests/test_sweep.py` (no `test_sweep_guards.py` exists).
2. Add a Step-3b table for the detail-watchdog (WARN + BLOCK pairs at `sweep_guards.py:30-37`) — it's the second silent-fallback and the skill is currently blind to it.
3. Add wall-clock cap, checkpoint-guard, save-failure, and corrupt-snapshot rows to the failure-mode table (all in `scraper/sweep.py`).
4. Note that `data/history.json` is owned by `web/build.py:456` (`_update_history`), not the sweep — prevents misrouted debugging.
5. Broaden trigger phrases to cover detail-page / partial-sweep symptoms.
