---
name: jcstream-sweep-debugger
description: Use when investigating why a JCStream sweep didn't produce fresh data — the roster count is flat, the changelog is empty, the site rendered stale photos, or the GitHub Actions sweep workflow showed exit-0 but no commit. Covers the silent degraded-roster fallback in scraper/sweep.py, the health thresholds in sweep_guards.py, and how to read changelog.json / history.json / current.json together. Trigger phrases: "sweep didn't update", "stuck count", "no changes in changelog", "scraper looks idle", "stale photos", "partial sweep", "sweep bailed", "sweep timed out", "nameless records", "detail watchdog".
---

# JCStream sweep debugger

You diagnose sweep failures. The most common failure mode is **silent**: `sweep_looks_healthy` (in `scraper/sweep_guards.py`; the underscored name in `scraper/sweep.py` is a back-compat alias) returned False, `sweep.py` kept the last-good `data/current.json`, and the workflow exited 0 with no commit. The site looks fine but is stale.

## The triage flow

### 1. Did the sweep workflow run at all?
Check GitHub Actions for the most recent sweep run:
```sh
# Workflow defined at .github/workflows/sweep.yml
# Look for "data+site: sweep YYYY-MM-DDTHH:MMZ" commits on the dev branch
git log --oneline -20 | grep "data+site: sweep"
```
Gaps in the timeline (>30 min) mean the cron didn't fire — that's a GH Actions / repo-permissions problem, not a scraper problem.

### 2. Did the scraper bail on the health check?
The workflow log will show the sweep's `sweep_looks_healthy` decision. Without log access, infer from data:

- Compare today's `data/current.json` `inmate_count` to yesterday's: if it's identical for >2 cycles, the gate likely tripped.
- Tail `data/changelog.json`: if the most recent `timestamp_utc` is >1 hour old, no new events.

### 3a. Which list-side threshold tripped?
From `scraper/sweep_guards.py`:

| Threshold | Meaning |
|---|---|
| `SWEEP_MAX_FAILED_FRACTION = 0.10` | >10% of surname fetches errored → bail |
| `SWEEP_MIN_ROSTER_FRACTION = 0.5` | new roster <50% of last cycle → bail |
| `SWEEP_BOOTSTRAP_FLOOR = 50` | first-ever sweep needs ≥50 inmates → bail |

To distinguish:
- **High error rate** → HCSO rate-limited the scraper. Look at the workflow log for HTTP 429 / generic-block-page hits. The fix is usually time (wait an hour) — not a code change.
- **Roster collapse** → HCSO published a degraded list (frequent during a system migration). Check `https://www.hcso.org/justice-center-services/inmate-search/` manually.
- **Bootstrap floor** → a brand-new deploy with `data/current.json` missing. Run a manual sweep with `workflow_dispatch`.

### 3b. Did the detail-page watchdog trip?
Even when the list sweep stays green, `check_detail_watchdog` (`scraper/sweep_guards.py`, called at `scraper/sweep.py`) can refuse the cycle if the per-inmate detail pages stop yielding names or photos. This is the path that fires on *"stale photos but fresh roster count"* / *"nameless inmates"*.

From `scraper/sweep_guards.py`:

| Threshold | Tier | Meaning |
|---|---|---|
| `DETAIL_WATCHDOG_MIN_SAMPLE = 10` | gate | below this many detail attempts the watchdog is silent (small samples are noisy) |
| `DETAIL_WATCHDOG_NAME_FLOOR = 0.70` | WARN | <70% of detail attempts parsed a name → log warning, still write |
| `DETAIL_WATCHDOG_PHOTO_FLOOR = 0.50` | WARN | <50% of detail attempts yielded a photo → log warning, still write |
| `DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE = 100` + `DETAIL_WATCHDOG_BLOCK_NAME_FLOOR = 0.60` | BLOCK | both must hold (≥100 attempts AND <60% named) → `roster_ok=False`, keep last-good |

A WARN-tier trip leaves the roster fresh but the warnings in the workflow log are the early signal that HCSO's detail-page HTML is shifting (parser regression imminent). A BLOCK-tier trip looks identical to a list-side bail from the outside — exit 0, no commit.

### 3c. Other silent-bail / partial-write paths in `scraper/sweep.py`
| Path | Where | Symptom |
|---|---|---|
| Wall-clock cap | `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` at `scraper/sweep.py`, enforced at `scraper/sweep.py` | sweep finishes after ~22 min with a *partial* roster persisted; diff/changelog are skipped (`clean_finish=False`), so the count moves but no events appear |
| Checkpoint guard | `scraper/sweep.py` | mid-sweep `save_current` checkpoints are skipped when in-memory roster is <50% of previous; a stuck count can come from this even though the final-write path looks fine — log line: "checkpoint skipped at N/M details" |
| Corrupt-snapshot bail | `scraper/sweep.py` (`SnapshotCorruptError`) | returns 0 immediately; the broken `data/current.json` is left in place for inspection — log line: "refusing sweep: data/current.json is unreadable" |
| `save_current` failure | `scraper/sweep.py` (`OSError`) | disk-full / atomic-rename failure: snapshot unchanged, changelog and prune both skipped — log line: "save_current failed (...); skipping changelog and prune" |
| Photo prune skip | `scraper/sweep_guards.py` (`PHOTO_PRUNE_MAX_FRACTION = 0.5`) | when >50% of stored photos would be deleted in one cycle, prune is skipped wholesale — symptom is "photos for released inmates aren't disappearing" — log line: "photo prune would remove N/M photos (>50%) - skipping prune" |

Atomic write contract: `data/current.json` is written via tmp + `os.replace` in `scraper/store.py` (`_atomic_write_text`), so a half-written snapshot is never published — a stale `current.json` is always intact, never truncated.

### 4. Cross-check the data files
| File | What it tells you |
|---|---|
| `data/current.json` | Latest *accepted* roster snapshot. `generated_utc` is when the snapshot was written (not when the sweep ran — those diverge during a bailed sweep). |
| `data/changelog.json` | Append-only log of booked/released/updated events. Length grows on every accepted sweep. |
| `data/history.json` | Daily roster-size + churn counts. Stubby today (≈200 bytes). **Owned by `web/build.py` (`_update_history`), not by the sweep** — a stale history.json points at the build/Pages workflow, not the scraper. |
| Workflow logs (Actions) | Per-surname HTTP status, error count, gate decision. |

If `current.json.generated_utc` is recent but `changelog.json` is unchanged → the sweep was accepted but no events flipped (genuinely quiet day) **or** the sweep tripped the wall-clock cap and the diff was skipped (check the log for "wall-clock cap reached").

If `current.json.generated_utc` is stale and `changelog.json` is stale → the gate has been tripping. Read the recent workflow logs.

## When to file a code fix
- Threshold is too tight for the actual error envelope (HCSO consistently returns 8% errors and the floor is 10%) → tune `SWEEP_MAX_FAILED_FRACTION` in `sweep_guards.py` *with* telemetry to back it up.
- A new HCSO HTML quirk is causing parsing failures → fix the parser, don't relax the gate.
- The bootstrap floor is biting a legitimate restart → drop a known-good `data/current.json` into place rather than weakening the check.

## When NOT to file a code fix
- HCSO is rate-limiting → wait it out, this is normal.
- HCSO is publishing a degraded list → the silent fallback is *protecting* the site; let it.

## Anti-patterns
- Lowering `SWEEP_MIN_ROSTER_FRACTION` to make a bad sweep go through.
- Editing `data/current.json` by hand.
- Re-running the workflow without diagnosing — you'll get the same answer.

## Verify a fix
```sh
python -m pytest -q tests/test_sweep.py
# Then trigger a manual sweep via the GH Actions UI (workflow_dispatch).
```
