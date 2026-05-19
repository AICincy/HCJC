# Audit Pass 2 — jcstream-sweep-debugger

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 fixes landed accurately with correct file:line cites, and the broadened triggers now cover the previously blind detail-watchdog symptoms.

## Pass-1 recommendation status
1. Fix the broken `pytest` invocation pointing at non-existent `tests/test_sweep_guards.py`: Done — SKILL.md:94 now reads `python -m pytest -q tests/test_sweep.py`; that file exists at `tests/test_sweep.py` and covers `sweep_looks_healthy`/`check_detail_watchdog`/`prune_photos` (`tests/test_sweep.py:10-117`).
2. Add a Step-3b table for the detail-watchdog WARN/BLOCK pairs: Done — new §3b at SKILL.md:41-53 documents `DETAIL_WATCHDOG_MIN_SAMPLE`, `_NAME_FLOOR`, `_PHOTO_FLOOR`, `_BLOCK_MIN_SAMPLE`, `_BLOCK_NAME_FLOOR` with correct cites to `scraper/sweep_guards.py:30-37` (verified in source at `sweep_guards.py:30-37`) and the invocation site at `scraper/sweep.py:197-200` (verified).
3. Add wall-clock cap / checkpoint-guard / corrupt-snapshot / save-failure / photo-prune rows: Done — table at SKILL.md:56-62 lists all five paths with cites at `scraper/sweep.py:61`, `:152-157`, `:183-196`, `:80-90`, `:212-216`, and `scraper/sweep_guards.py:104-129`; each verified against current source (e.g., `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` at `scraper/sweep.py:61`).
4. Note `data/history.json` is owned by `web/build.py`, not the sweep: Done — SKILL.md:71 says "Owned by `web/build.py:1321` (`_update_history`), not by the sweep"; verified function definition at `web/build.py:1321`.
5. Broaden trigger phrases (stale photos, partial sweep, sweep bailed, nameless records, detail watchdog): Done — SKILL.md:3 now includes all five new phrases plus the original four.

## New issues found in pass 2
- None substantive. SKILL.md:8 still references the back-compat alias path correctly (real function at `scraper/sweep_guards.py:46`, alias at `scraper/sweep.py:65` — both verified). The atomic-write contract is now mentioned at SKILL.md:64 with correct cite to `scraper/store.py:44-54` (verified — `_atomic_write_text` defined at `store.py:44`).

## Pass-2 lens checks
- **Drift**: Clean. Every cite I spot-checked resolves (`sweep_guards.py:23-25,30-37,46,64-101,104-129`; `sweep.py:61,80-90,152-157,183-196,197-200,212-216`; `store.py:44-54`; `build.py:1321`; `tests/test_sweep.py`).
- **Coverage**: Clean. The six failure paths pass-1 flagged (detail watchdog, wall-clock cap, checkpoint guard, corrupt-snapshot, save-failure, photo prune skip) and the atomic-write contract are all now documented (SKILL.md:41-64).
- **Triggers**: Clean. The description at SKILL.md:3 fires on the obvious phrasings ("sweep didn't update", "stuck count") plus the previously missed detail-watchdog symptoms ("stale photos", "nameless records", "detail watchdog") and partial-sweep symptoms ("partial sweep", "sweep bailed", "sweep timed out"). The CLAUDE.md preamble (CLAUDE.md:46-49) describes the same fallback the skill anchors on, so routing is consistent.
- **Applicability**: Domain is alive — `scraper/sweep.py`, `scraper/sweep_guards.py`, `data/{current,changelog,history}.json`, and `.github/workflows/sweep.yml` are all current; the paired agent at `.claude/agents/jcstream-sweep-debugger.md:9` correctly directs to invoke this skill on every task.
