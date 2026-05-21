# sweep - Sweep Reliability Audit

## Audit metadata
- Skill: jcstream-python-sweep-reliability
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 5 (scraper/sweep.py 355, scraper/photos.py 37, scraper/client.py 110, scraper/store.py 151, tests/test_sweep.py 56; plus .github/workflows/sweep.yml 106 for budget context)
- Time: 2026-05-14T01:41:59Z

## Observations

- `_sweep_looks_healthy` returns True unconditionally when `prev_count < SWEEP_BOOTSTRAP_FLOOR` (sweep.py:64-65). `load_current` returns `{}` on JSON corruption or schema mismatch (store.py:48-55), which collapses to a zero `prev_count` and silently re-enters bootstrap mode.
- Checkpoint writes happen every 50 detail fetches inside the worker loop (sweep.py:152-155). They are gated only on `not dry_run`, not on `roster_ok` or the current in-memory size relative to `prev_count`. The atomic write (store.py:28-38) keeps the file intact but the *count* it persists can be far below prior.
- The detail watchdog at sweep.py:182-204 only logs at WARNING. It never flips `roster_ok` to False. The list-row fallback at sweep.py:262-268 rescues names for IDs surfaced this cycle, but a `refresh_known=True` run carrying forward existing IDs gets no such fallback for IDs that drop off the list mid-sweep.
- KeyboardInterrupt handling at sweep.py:157-158 logs and falls through to the `finally` block. The `finally` then unconditionally calls `diff(previous, current)` and appends `released` events for every ID the sweep never reached, because `current` is half-built. With `CHANGELOG_LIMIT = 500` (store.py:25), one bad interrupt can monopolize the public feed.
- `_prune_photos` runs in the `finally` clause (sweep.py:174-175) gated only on `roster_ok` and `seen_ids` being non-empty. If `save_current` raises (disk full, permission), the `finally` still attempts the prune. There is no "save succeeded" flag.
- `_sweep_list` uses `pool.map` (sweep.py:226-234). `pool.map` is *not* tolerant of worker exceptions; it surfaces the first raise when iterated. The inner `fetch_one` defensively swallows everything (sweep.py:217-223), so today this is fine; the invariant is undocumented.
- `HcsoClient.timeout = 30.0` (client.py:36) plus a single retry with up to 1.0s backoff yields a worst case of ~61s per fetch. Crawl delay is 0 by default (client.py:24). There is no orchestrator-side wall-clock budget; only the GitHub Actions `timeout-minutes: 50` (sweep.yml:35) gates total runtime.
- `_read_surnames` (sweep.py:317-322) uses `line.strip()` which does not strip the U+FEFF BOM. A Windows-edited `data/surnames.txt` would produce a surname `﻿A` on line 1, which silently sends a request that returns nothing rather than failing loudly.
- `_prune_photos` docstring (sweep.py:295) references a typo `SWEOOTSTRAP_FLOOR`. Minor but confirms the bootstrap edge is on the author's mind.
- The healthy-roster guard fires before any detail fetch begins. After it passes, `to_fetch` can still be empty if `refresh_known` is False and the list returned an entirely-known set; the `finally` then re-saves `current` (which is the carry-forward of `previous`) and computes a no-op diff. This is correct but unobvious.

## Analysis

The orchestrator's deliberate posture is correct: trust the last-good snapshot more than any single noisy cycle, bias toward zero false positives on "released," and let GitHub Actions retry naturally every 30 minutes. The 0.10 / 0.50 / 50 thresholds match the failure shapes HCSO actually produces (Obs 1, sweep.py:43-45). The audit findings below are *not* a critique of those values; they are gaps around what the values cover.

The single biggest gap is the bootstrap-floor recovery path (Obs 1). `load_current` is engineered to swallow corruption and return `{}` (store.py:48-55), and `_sweep_looks_healthy` is engineered to bootstrap from `{}`. Each guard is reasonable in isolation; the composition lets a corrupted snapshot promote any non-trivial sweep to canonical truth, including a sweep where 90% of surnames errored but the 10% that succeeded happened to surface 60 IDs. The owner's documented promise that "the public count is stable" assumes `current.json` is recoverable.

The checkpoint behavior (Obs 2) is intentional partial-progress preservation, and removing it would regress the local-dev story. The issue is that the checkpoint bypasses the same fraction guard that protects the final write. A reasonable refinement is to require the checkpoint payload to be at least `SWEEP_MIN_ROSTER_FRACTION * prev_count` of size before being persisted, which preserves the "interrupt-and-not-blank" property for healthy in-progress sweeps and falls back to the previous snapshot for degenerate ones.

The detail watchdog (Obs 3) is the right shape but lacks teeth. A scenario where HCSO ships a detail-page redesign mid-cycle produces a sweep that the list-side guard accepts and the detail-side guard merely whispers about. List-row fallback covers most of this for first-time fetches but cannot help a `refresh_known` pass whose ID disappeared from the list between the list call and the detail call. Promoting the watchdog to a write-blocker at a stricter threshold (say, >=100 attempts and <60% named) preserves the WARN-only behavior for small fluctuations while catching a true regime change.

KeyboardInterrupt + changelog (Obs 4) is the worst-case data event in the audit. The `finally` block writes a half-built `current` and computes the diff against `previous`, so every unreached ID becomes a `released` event. With `CHANGELOG_LIMIT = 500`, a single interrupted sweep can evict 500 real events from the rolling feed and replace them with synthetic "released" entries. The fix is to gate the changelog append on a `_clean_finish` flag set just before the `finally`; the snapshot still gets written so the next cycle's diff is correctly anchored, but the changelog stays honest.

Photo prune ordering (Obs 5) is small but real. The current code reaches `_prune_photos` even when `save_current` raised. The prune itself has a `PHOTO_PRUNE_MAX_FRACTION = 0.5` guard, but on a healthy roster of 1200 inmates an attacker scenario or a disk-edge-case scenario could still delete up to ~600 valid photos before the guard trips. Gating prune on `save_current_succeeded` is cheap.

Concurrency and budget (Obs 7) is the least urgent. The owner has explicitly tuned concurrency=32 with rationale in client.py:25-28. The reality is HCSO behaves as expected at that level. The thing missing is an orchestrator-level wall-clock cap that converts "we ran out of time" into "we wrote what we had at minute 22" rather than "GitHub killed us at minute 50 mid-checkpoint." This is a low-likelihood failure mode given that the previous-known carry-forward path already accounts for most of the cycle's content.

The surname BOM issue (Obs 8) is a one-line fix and would only ever matter if the owner edits `data/surnames.txt` on Windows. The cost of the defensive `lstrip("﻿")` is zero and the failure mode (silently empty letter) is invisible to all existing guards because zero rows from one surname is below the 10% failure threshold and is indistinguishable from a real empty letter.

## Technical notes

```python
# Obs 1: bootstrap from corrupted snapshot
# store.py:48-55 returns {} on ANY deserialization error
# sweep.py:64-65 treats prev_count < 50 as bootstrap
# Net effect: a corrupt current.json + a degraded sweep = canonicalized degraded data
```

```python
# Obs 2: checkpoint guard gap
if not dry_run and done % 50 == 0:
    save_current(CURRENT_PATH, current.values())
# Proposed:
if (not dry_run
    and done % 50 == 0
    and (len(previous) < SWEEP_BOOTSTRAP_FLOOR
         or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous))):
    save_current(CURRENT_PATH, current.values())
```

```python
# Obs 3: watchdog promotion sketch
DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE = 100
DETAIL_WATCHDOG_BLOCK_NAME_FLOOR = 0.60
def _check_detail_watchdog(...) -> bool:  # returns roster_ok delta
    if attempts >= DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE \
       and (named / attempts) < DETAIL_WATCHDOG_BLOCK_NAME_FLOOR:
        return False
    return True
```

```python
# Obs 4: changelog corruption under KeyboardInterrupt
clean_finish = False
try:
    ...
    clean_finish = True
except KeyboardInterrupt:
    log.warning("interrupted; persisting %d partial inmates", len(current))
finally:
    if not dry_run and roster_ok:
        save_current(CURRENT_PATH, current.values())
        if clean_finish:
            events = diff(previous, current)
            ...
```

```python
# Obs 5: photo prune ordering
save_ok = False
...
finally:
    if not dry_run and roster_ok:
        try:
            save_current(CURRENT_PATH, current.values())
            save_ok = True
        except OSError as e:
            log.error("save_current failed: %s", e)
        ...
        if save_ok and seen_ids:
            _prune_photos(seen_ids)
```

```python
# Obs 6: pool.map contract comment
# fetch_one MUST swallow all exceptions and return None on failure.
# pool.map surfaces the first worker raise when iterated, which would
# truncate the surname sweep below the SWEEP_MAX_FAILED_FRACTION
# threshold and look like a healthy partial sweep.
```

```python
# Obs 7: orchestrator wall-clock cap (suggested constant)
SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60  # leaves time for build + commit + deploy
# Checked inside the as_completed loop:
if time.monotonic() - started > SWEEP_WALLCLOCK_HARD_CAP_S:
    log.warning("hard cap reached at %d/%d details; finalizing", done, len(to_fetch))
    break
```

```python
# Obs 8: BOM-safe surname load
def _read_surnames(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    return [
        line.strip().upper()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
```

## Findings

### sweep-F1: Corrupted current.json silently re-enters bootstrap mode
- Severity: high. Confidence: high.
- Location: scraper/sweep.py:64-65, scraper/store.py:48-55.
- Trigger: a malformed or schema-drifted `data/current.json` (e.g., a Pydantic field rename, a half-recovered git revert, an editor-mangled save) causes `load_current` to return `{}`. The next sweep's `_sweep_looks_healthy` then treats *any* successful roster as truth, bypassing the 50% collapse guard.

### sweep-F2: KeyboardInterrupt synthesizes a wave of bogus "released" events
- Severity: high. Confidence: high.
- Location: scraper/sweep.py:157-173.
- Trigger: workflow cancellation or local Ctrl-C mid-sweep. The half-built `current` is diffed against the full `previous`, producing one `released` event per unreached ID. Up to 500 of those evict real events from the rolling changelog.

### sweep-F3: Checkpoint write can persist a sub-threshold roster
- Severity: medium. Confidence: high.
- Location: scraper/sweep.py:152-155.
- Trigger: a long `to_fetch` list combined with a mid-cycle crash right after a `done % 50 == 0` checkpoint. The on-disk count can land below `SWEEP_MIN_ROSTER_FRACTION * prev_count`, and the *next* cycle's guard then compares to that lowered baseline.

### sweep-F4: Detail watchdog warns but never blocks the write
- Severity: medium. Confidence: high.
- Location: scraper/sweep.py:182-204, called at sweep.py:156.
- Trigger: HCSO ships a detail-page redesign while the list page stays parseable. The list-side guard passes, the detail-side parser produces nameless or photoless records, the watchdog logs WARNING, and the degraded data is canonicalized.

### sweep-F5: Photo prune runs even when save_current failed
- Severity: medium. Confidence: medium.
- Location: scraper/sweep.py:174-175 (inside `finally`).
- Trigger: `save_current` raises (disk full, permission denied, filesystem hiccup). The `finally` then attempts to prune photos against `seen_ids` that was never persisted to disk. The `PHOTO_PRUNE_MAX_FRACTION` guard catches catastrophic deletes but not a 30-40% prune of valid records.

### sweep-F6: No orchestrator wall-clock budget
- Severity: low. Confidence: high.
- Location: scraper/sweep.py:129-156.
- Trigger: a slow-but-not-failing HCSO front-end causes the detail-fetch loop to consume the GitHub Actions 50-minute budget. The job is killed by the runner mid-checkpoint rather than producing a clean partial write.

### sweep-F7: BOM in data/surnames.txt produces a silently-empty letter
- Severity: low. Confidence: high.
- Location: scraper/sweep.py:317-322.
- Trigger: any Windows editor save that prepends U+FEFF. The first surname becomes `﻿A`, the HCSO list page returns zero rows, `_sweep_list` records that as zero rows (not a failure), and no guard fires.

### sweep-F8: Undocumented pool.map exception-isolation contract
- Severity: low. Confidence: high.
- Location: scraper/sweep.py:226-234.
- Trigger: a future refactor of `fetch_one` that re-raises (for example to bubble a typed HCSO error). `pool.map` would propagate the first raise, truncating the surname sweep below the failure threshold and looking like a healthy partial sweep.

## Recommendations

### sweep-R1 (for F1)
Distinguish "file missing" from "file unreadable" in `load_current`. On JSON or Pydantic error, raise (or return a sentinel like `None`) and have `sweep.run` refuse to bootstrap from `{}` unless the file is genuinely absent. Acceptable softer variant: persist a sidecar `data/.last_known_count` after every healthy write and feed *that* into `_sweep_looks_healthy` instead of `len(previous)`. Rollback note: the strict variant trades silent recovery for one manual fixup per corruption event; the soft variant is invisible and zero-risk.

### sweep-R2 (for F2)
Set a `_clean_finish = True` immediately before exiting the `try` block. In the `finally`, write the snapshot unconditionally (preserving the interrupt-recovery property) but only call `diff` and append to changelog when `_clean_finish` is True. Rollback note: a real interrupted sweep no longer emits churn for the changelog feed, which is the desired behavior.

### sweep-R3 (for F3)
Gate the in-loop checkpoint on the current in-memory size: only checkpoint when `len(previous) < SWEEP_BOOTSTRAP_FLOOR or len(current) >= SWEEP_MIN_ROSTER_FRACTION * len(previous)`. Rollback note: in a true catastrophic mid-sweep crash with `to_fetch` very large, the on-disk file stays at the previous good snapshot until the natural 30-minute retry. That is the desired property.

### sweep-R4 (for F4)
Add a stricter pair of constants (`DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE = 100`, `DETAIL_WATCHDOG_BLOCK_NAME_FLOOR = 0.60`) and have `_check_detail_watchdog` return a `roster_ok` delta. Sweep flips `roster_ok = False` when the strict floor is breached. Rollback note: the WARN-only thresholds (0.70 / 0.50) stay in place; this only blocks writes when both the sample is large and the name rate is unambiguously degraded.

### sweep-R5 (for F5)
Wrap `save_current` in a local try/except inside the `finally`, set a `save_ok` flag, and gate `_prune_photos(seen_ids)` on `save_ok`. Rollback note: in the rare disk-failure case, the photo directory is left intact and the next healthy cycle prunes naturally.

### sweep-R6 (for F6)
Add `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` and break out of the `as_completed` loop once exceeded. Falls into the existing `finally`, which writes the partial roster. Rollback note: on a slow HCSO day, the sweep finalizes with carry-forwards plus whatever details completed, instead of being killed mid-write by the runner.

### sweep-R7 (for F7)
Apply `text.lstrip("﻿")` once before splitlines in `_read_surnames`. Rollback note: zero behavioral change on non-BOM files.

### sweep-R8 (for F8)
Add a comment block above `pool.map(fetch_one, surnames)` documenting the "fetch_one must never raise; failures return None" contract. Rollback note: documentation only.

## Remediation plan

1. Apply sweep-R7 (BOM strip) and sweep-R8 (comment). Zero behavioral risk, lands first.
2. Apply sweep-R2 (`_clean_finish` gating of changelog append). High value, isolated to the `try/finally`; cover with a test that interrupts mid-loop and asserts no `released` events.
3. Apply sweep-R5 (gate prune on save_ok). Small, surfaces an OSError path that is currently invisible.
4. Apply sweep-R1 (load_current sentinel) plus sweep-R3 (checkpoint guard). These compose to close the bootstrap exploit; ship together with a test that corrupts `current.json` and asserts the sweep refuses to canonicalize a partial roster.
5. Apply sweep-R4 (watchdog block) and sweep-R6 (wall-clock cap) together once the higher-priority fixes are in. These bias toward "write existing-good behavior, not block sweeps" per the skill's guidance.

## Cross-references

- store.py changelog-corruption interaction (sweep-F2) overlaps with the data-integrity scope: the changelog append is the persistence-side amplifier. Cross-scope: data integrity.
- TLS verify=False / retry policy in client.py is in scope for security-networking. Not flagged here per skill guidance.
- Parser-side degradation that the detail watchdog is meant to catch (sweep-F4) is in scope for parser-robustness; the fix here is orchestrator-side (block the write) and remains owned by sweep.
- Architecture concern: sweep.run is doing list, fetch, write, diff, prune, and watchdog in one function. Refactor sequencing belongs to architecture scope.

## Confidence and limitations

- All findings are anchored to specific line ranges and constants. Confidence is high for F1-F4 and F6-F8; F5 confidence is medium because real OSError on `save_current` (atomic rename) is rare in the actions environment.
- No runtime reproduction was attempted; this is a static read of the orchestrator at commit 8355cc8.
- I did not read sibling reports per the constraints. Overlaps are flagged in Cross-references rather than resolved.
- The audit deliberately does not propose changing any of the documented thresholds (0.10, 0.50, 50, 32). All recommendations either add new constants with conservative defaults or gate existing behavior.

End of report.
