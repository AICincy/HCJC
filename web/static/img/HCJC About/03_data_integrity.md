# data - Data Integrity Audit

## Audit metadata
- Skill: jcstream-python-data-integrity
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 8 (scraper/store.py 150, scraper/models.py 80, scraper/sweep.py 355, data/current.json 80340, data/changelog.json 3501, data/history.json 1, tests/test_store.py 75, tests/test_models.py 19)
- Time: 2026-05-14T01:42:27Z

## Observations (3-10 bullets, line-cited)

- `scraper/store.py:28-38` `_atomic_write_text` uses `tmp + os.replace`, so a killed process cannot publish a half-written `current.json` or `changelog.json`. Confirmed no leftover `.tmp` is asserted in `tests/test_store.py:71`.
- `scraper/store.py:58-65` `save_current` computes `inmate_count = len(materialized)` at write time, so the count cannot drift on save, but `Snapshot` (`scraper/models.py:71-76`) does not enforce that invariant on load. The live `data/current.json` checks out: `inmate_count == len(inmates) == 1210`.
- `scraper/store.py:41-55` `load_current` swallows `JSONDecodeError, ValidationError, KeyError, TypeError, AttributeError` and returns `{}`. With `prev_count == 0`, the sweep guard at `scraper/sweep.py:64-65` accepts any seen_count as believable, which is the schema-migration risk called out in the skill.
- `scraper/store.py:79-84` `save_changelog` trims `events[-CHANGELOG_LIMIT:]` only on write; there is no read-side trim and no read-side sort. Live `changelog.json` is exactly 500 events and is currently in ascending timestamp order, but only because saves happen serially and the OS clock has been monotonic.
- `scraper/store.py:142-150` `_materially_changed` compares `charges` with Pydantic `!=`, which is element-wise and order-sensitive. Sampling 50 inmates in the live snapshot shows multi-charge lists are insertion order, not sorted, so a backend reshuffle would emit spurious `updated` events.
- `scraper/models.py:24-41` every `Inmate` field except `inmate_number` is optional and defaults to `""` or `[]`. No validator rejects an empty-string `inmate_number`, so a parser bug that yields `inmate_number=""` would create a single bucket that swallows multiple records as later-wins.
- `scraper/sweep.py:152-155` checkpoint `save_current` runs every 50 details inside the `with ThreadPoolExecutor`. It rewrites the snapshot but does not append to the changelog (changelog write is in the `finally`, lines 162-175). A killed-mid-checkpoint cycle leaves a partial snapshot with no event history for that cycle; that is correct, but `store.py` has no comment marking the dependency.
- `scraper/sweep.py:163-175` final write order is: `save_current`, then `diff(previous, current)`, then `save_changelog`, then `_prune_photos`. Photo prune happens after `save_current`, so the snapshot can transiently reference a photo that prune is about to delete. Today this is benign because the next sweep rewrites both, but the dependency is not pinned by code or comment.
- `data/history.json` is a single flat array of `{date, count, booked_24h, released_24h}` written by `web/build.py:456-511`, not by the scraper layer. It is bounded at 400 days at write time and is the only artifact that retains anything beyond the current roster. The schema is undocumented in `scraper/models.py` and unvalidated.
- `scraper/store.py:99-102` `diff` emits a warning when the previous/current dicts have entries keyed under a different `inmate_number` than the record's own field, but it does not deduplicate, it does not normalize, and it does not skip the record.

## Analysis (3-8 paragraphs, anchored)

The persistence layer is small and focused. The atomic-write pattern at `scraper/store.py:28-38` is correct, and the deliberate decision in `_materially_changed` (`scraper/store.py:142-150`) to ignore `last_seen_utc` and `first_seen_utc` is the right contract: those two fields churn every sweep and would otherwise produce a wall of `updated` events. The four watched fields (`booking_number`, `projected_release_date`, `holder_status`, `charges`) are the publicly-meaningful ones. This is documented in code and should be preserved.

The largest invariant gap is on the read path. `load_current` (`scraper/store.py:41-55`) treats any `ValidationError` as "treat as empty," which is the intended behavior for a corrupt file. The risk only appears when combined with `_sweep_looks_healthy` (`scraper/sweep.py:57-70`): once `previous` is empty, the bootstrap floor (`SWEEP_BOOTSTRAP_FLOOR = 50`) means a single new sweep, however small, is unconditionally accepted. If a model migration ever adds a required field, the first sweep after deploy could silently replace a healthy roster with a small or empty one and the changelog would record a flood of `booked` events with no `released` counterpart. Adding a `schema_version` field to `Snapshot` with a forward-compat read path closes this without a one-time data migration: a `model_validator(mode="before")` can default the field to `1` for existing files.

The `inmate_count` / `len(inmates)` invariant is currently enforced only on the write side (`scraper/store.py:62-63`). The live file checks out, but a hand-edited `current.json` or a future bug could publish a mismatched count. A `@model_validator(mode="after")` on `Snapshot` would enforce this on both load and save with zero migration cost. The same validator can enforce uniqueness of `inmate_number` across `inmates`, which today depends entirely on the fact that all callers build `current` as a dict keyed by `inmate_number`.

The `charges` ordering issue is real. `Pydantic`'s `BaseModel.__eq__` is field-wise and `list[Charge]` compares element-wise. The HCSO detail parser produces charges in document order. If HCSO ever reorders them, every affected inmate will fire an `updated` event on the next sweep, even though the user-visible content is the same. The fix is either to sort charges at parse time (so the stored order is deterministic) or to canonicalize before comparison inside `_materially_changed`. The latter is a one-liner and preserves whatever display order the parser captured.

Changelog growth is correctly bounded. The skill flagged a hypothetical "previous bug wrote 10000 events" case; the negative-slice trim at `scraper/store.py:80` makes this self-healing on the next save. The more interesting case is non-monotonic time: the changelog is appended in insertion order, not sorted, and the live file happens to be sorted by timestamp only because saves are serial and the cron clock is well-behaved. A defensive sort-by-`timestamp_utc` with insertion-order as the stable tiebreaker would cost nothing and harden the contract that downstream feeds rely on (`web/build.py:568-611` slices `events[-50:]` for the RSS feeds at `:577` and trusts the ordering).

The carry-forward path at `scraper/sweep.py:117-120` does `model_copy(update={"last_seen_utc": utcnow_iso()})`, which already produces a new instance, so there is no in-place mutation risk. The skill's `model_copy(deep=True)` recommendation is unnecessary here because `model_copy` already produces a shallow copy that is independent at the top level and the `charges` list is not mutated downstream; `web/build.py` reads only.

The photo-vs-record concern is currently latent. `_prune_photos` runs after `save_current` in `sweep.py:162-175`, and the snapshot only references photos that existed when the detail fetch ran or that were already on disk. The audit found zero broken references (1074 referenced, 1074 on disk, zero orphans). The risk is that nothing in code pins this ordering: someone reordering the `finally` block could ship a snapshot that references freshly-deleted JPGs. A short comment in `store.py` or `sweep.py` would prevent that regression.

`data/history.json` is the only artifact with cross-day retention, and it has no model. The shape is stable (4-key dicts), but the read path at `web/build.py:478-479` only catches `JSONDecodeError, OSError`; a structurally-valid but wrong-shape file (e.g. someone hand-edited a record into a string) would crash the `_compute_stats` path. A small Pydantic model for the daily record would cost almost nothing and would make the shape audit-discoverable.

## Technical notes (3-10 fenced blocks)

Snapshot post-validator that enforces count and uniqueness without a migration:

```python
# scraper/models.py
from pydantic import model_validator

class Snapshot(BaseModel):
    schema_version: int = 1
    generated_utc: str
    inmate_count: int
    inmates: list[Inmate]

    @model_validator(mode="after")
    def _check_invariants(self) -> "Snapshot":
        if self.inmate_count != len(self.inmates):
            raise ValueError(
                f"inmate_count={self.inmate_count} != len(inmates)={len(self.inmates)}"
            )
        ids = [i.inmate_number for i in self.inmates]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate inmate_number in snapshot")
        return self
```

Forward-compat read for `schema_version`:

```python
# scraper/store.py, in load_current
try:
    raw = json.loads(path.read_text(encoding="utf-8"))
    version = raw.get("schema_version", 1)
    if version > 1:
        log.error("current.json schema_version=%d is newer than expected; keeping file in place and returning empty", version)
        return {}
    return {i["inmate_number"]: Inmate(**i) for i in raw.get("inmates", [])}
except (json.JSONDecodeError, ValidationError, KeyError, TypeError, AttributeError) as e:
    log.error("could not deserialize %s (%s): treating as empty", path, e)
    return {}
```

Inmate-number validator (rejects empty strings):

```python
# scraper/models.py
from pydantic import field_validator

class Inmate(BaseModel):
    inmate_number: str
    # ...

    @field_validator("inmate_number")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("inmate_number must be non-empty")
        return v
```

Charges-order tolerance in `_materially_changed`:

```python
# scraper/store.py
def _materially_changed(a: Inmate, b: Inmate) -> bool:
    if any(getattr(a, k) != getattr(b, k) for k in ("booking_number", "projected_release_date", "holder_status")):
        return True
    # Order-insensitive compare for charges so a HCSO reshuffle of the same
    # content doesn't fire a spurious updated event.
    return sorted(a.charges, key=lambda c: c.model_dump_json()) != \
           sorted(b.charges, key=lambda c: c.model_dump_json())
```

Stable changelog sort at save time:

```python
# scraper/store.py
def save_changelog(path: Path, events: list[ChangeEvent]) -> None:
    indexed = list(enumerate(events))
    indexed.sort(key=lambda iv: (iv[1].timestamp_utc, iv[0]))
    ordered = [e for _, e in indexed]
    trimmed = ordered[-CHANGELOG_LIMIT:]
    _atomic_write_text(path, json.dumps([e.model_dump() for e in trimmed], indent=2))
```

Generated-UTC format validator:

```python
# scraper/models.py
import re
_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class Snapshot(BaseModel):
    # ...
    @field_validator("generated_utc")
    @classmethod
    def _iso_z(cls, v: str) -> str:
        if v and not _ISO_Z.match(v):
            raise ValueError(f"generated_utc must be ISO-8601 ending in Z, got {v!r}")
        return v
```

Pinned write order in `sweep.py` finally block (comment-only, no behavior change):

```python
# scraper/sweep.py
finally:
    # Order matters: snapshot -> diff -> changelog -> prune. _prune_photos runs
    # last so the published snapshot never references a freshly-deleted JPG.
    if not dry_run and roster_ok:
        save_current(CURRENT_PATH, current.values())
        # ...
```

History.json record model:

```python
# scraper/models.py
class HistoryRecord(BaseModel):
    date: str          # YYYY-MM-DD
    count: int
    booked_24h: int
    released_24h: int
```

## Findings (data-F1 ... cap 8 unless cron-stopping; severity + confidence each)

### data-F1. Snapshot has no schema_version and load swallows ValidationError silently - severity high - confidence high
- File: scraper/store.py:41-55, scraper/models.py:71-76
- Invariant at risk: schema versioning, last-good preservation across migrations
- Failure mode: a future required-field migration empties `previous`; the sweep then accepts any small result because `prev_count < SWEEP_BOOTSTRAP_FLOOR`, silently replacing the live roster.
- Fix: add `schema_version: int = 1` to `Snapshot`, default it in a `model_validator(mode="before")` for existing files, and have `load_current` refuse versions above the known max while keeping the file in place. No data migration needed.
- Test to add: tests/test_store.py::test_load_current_rejects_unknown_schema_version

### data-F2. inmate_count and uniqueness only enforced on write - severity med - confidence high
- File: scraper/models.py:71-76
- Invariant at risk: `inmate_count == len(inmates)`, `inmate_number` unique in snapshot
- Failure mode: a hand-edited or partially-merged `current.json` publishes a mismatch; `web/build.py:49` parses it and downstream stats display incorrect totals.
- Fix: `@model_validator(mode="after")` on `Snapshot` that asserts both invariants. Pydantic v2 runs validators on both load and save.
- Test to add: tests/test_models.py::test_snapshot_rejects_mismatched_count_and_duplicate_ids

### data-F3. `_materially_changed` is order-sensitive on charges - severity med - confidence high
- File: scraper/store.py:142-150
- Invariant at risk: diff correctness (no spurious `updated`)
- Failure mode: HCSO reorders charges for the same person; every affected inmate fires `updated`, flooding the changelog and the RSS feeds with non-events.
- Fix: compare charges by a canonical sort key (`Charge.model_dump_json()`), or sort `charges` deterministically at parse time. The first is one line in `store.py`; the second touches the parser.
- Test to add: tests/test_store.py::test_diff_ignores_charge_reorder_with_same_content

### data-F4. Empty-string inmate_number is permitted by the model - severity med - confidence high
- File: scraper/models.py:27
- Invariant at risk: id uniqueness, diff correctness
- Failure mode: a parser bug yields `inmate_number=""`; one bucket swallows multiple records; `diff` then sees a single phantom record under `""`.
- Fix: `@field_validator("inmate_number")` that strips and rejects empty. Combined with data-F2 this kills the failure class.
- Test to add: tests/test_models.py::test_inmate_rejects_empty_inmate_number

### data-F5. generated_utc accepted in any format on load - severity low - confidence high
- File: scraper/models.py:71-76, scraper/store.py:60-65
- Invariant at risk: write contract (`utcnow_iso` produces `...Z`)
- Failure mode: a hand-edited or mis-timed file with a non-Z timestamp loads cleanly, then sorts or compares break downstream.
- Fix: `@field_validator("generated_utc")` enforcing the `YYYY-MM-DDTHH:MM:SSZ` shape (allow empty for the bootstrap snapshot at `web/build.py:46`).
- Test to add: tests/test_models.py::test_snapshot_rejects_non_z_timestamp

### data-F6. Changelog is not sorted on save - severity low - confidence high
- File: scraper/store.py:79-84
- Invariant at risk: changelog ordering contract
- Failure mode: two saves with non-monotonic wall clock (NTP slew, container restart) leave an out-of-order changelog; the RSS feeds at `web/build.py:577` slice `events[-50:]` and trust ordering.
- Fix: sort by `(timestamp_utc, original_index)` before the trim. Pure addition, no migration.
- Test to add: tests/test_store.py::test_save_changelog_sorts_by_timestamp_stable

### data-F7. history.json has no validated model - severity low - confidence med
- File: web/build.py:456-511, data/history.json:1
- Invariant at risk: shape of the only retained-over-time artifact
- Failure mode: a structurally-valid but wrong-typed record (e.g. `count` as string) crashes `_compute_stats` or silently drives a bad sparkline.
- Fix: add a `HistoryRecord` Pydantic model in `scraper/models.py`, validate on load in `_update_history`. Cross-scope on the write side; document in the data model regardless.
- Test to add: tests/test_build.py::test_history_record_round_trips

### data-F8. Photo prune ordering pinned only by convention - severity low - confidence high
- File: scraper/sweep.py:162-175, scraper/store.py top of file
- Invariant at risk: snapshot never references a freshly-deleted JPG
- Failure mode: a future refactor swaps prune before `save_current`; the snapshot then references missing photos for a 30-minute window.
- Fix: add a short comment in the `finally` block stating the required order; consider a post-prune reconciliation that clears `photo_filename` for any inmate whose JPG no longer exists.
- Test to add: tests/test_sweep.py::test_finally_block_writes_snapshot_before_prune (assert call order via mocks)

## Recommendations (1:1 with findings)

- data-F1: add `schema_version` to `Snapshot`, default to 1 with a `model_validator(mode="before")`, reject unknown future versions in `load_current` by returning empty AND logging an error loud enough to fail the cron step.
- data-F2: add a `@model_validator(mode="after")` to `Snapshot` enforcing `inmate_count == len(inmates)` and unique `inmate_number`.
- data-F3: switch the `charges` comparison in `_materially_changed` to a canonical-sort key. Keep the stored order (display contract) untouched.
- data-F4: add a `@field_validator("inmate_number")` rejecting empty/blank ids on the model.
- data-F5: add a `@field_validator("generated_utc")` accepting empty (bootstrap) or the strict ISO-Z shape.
- data-F6: sort the changelog by `(timestamp_utc, insertion_index)` inside `save_changelog` before trimming.
- data-F7: introduce `HistoryRecord` in `scraper/models.py` and validate on read in `_update_history`. Mark `web/build.py` change as cross-scope.
- data-F8: pin the finally-block ordering with a comment; optionally add a post-prune reconcile that nulls `photo_filename` for any inmate whose JPG path no longer exists.

## Remediation plan (<=5 ordered steps; Touches / Verification / Duration / Rollback)

1. Add Pydantic validators (data-F2, data-F4, data-F5).
   - Touches: scraper/models.py, tests/test_models.py
   - Verification: `python -m pytest tests/test_models.py -q` plus a full `python -m pytest -q` (must stay at 102 passed, plus 3 new tests).
   - Duration: ~20 minutes.
   - Rollback: remove the three validators; existing data round-trips because the validators are pure-additive.

2. Order-insensitive charges compare (data-F3).
   - Touches: scraper/store.py:142-150, tests/test_store.py
   - Verification: new test that two `Inmate` records with the same charges in different order produce no `updated` event; full pytest green.
   - Duration: ~10 minutes.
   - Rollback: revert the function body.

3. Stable changelog sort on save (data-F6).
   - Touches: scraper/store.py:79-84, tests/test_store.py
   - Verification: new test that feeds out-of-order events and asserts the saved file is sorted ascending; full pytest green; live changelog after first cron run still ascending (it already is).
   - Duration: ~10 minutes.
   - Rollback: revert the function body; live file is self-healing because it is already sorted.

4. Schema versioning (data-F1).
   - Touches: scraper/models.py (add field with default), scraper/store.py (forward-compat read), tests/test_store.py
   - Verification: load existing `data/current.json` (no `schema_version` field) and assert it loads as version 1; load a synthetic version-99 file and assert empty plus loud error log; full pytest green.
   - Duration: ~25 minutes.
   - Rollback: drop the field default to optional; existing files unaffected because the field defaults silently.

5. Pin sweep ordering and document checkpoint-vs-changelog gap (data-F8).
   - Touches: scraper/sweep.py (comments only), scraper/store.py module docstring (one sentence)
   - Verification: pytest green; reviewer reads the comment.
   - Duration: ~5 minutes.
   - Rollback: revert the comment.

## Cross-references (out-of-scope items, one-liners, pointing to sibling skills)

- `web/build.py:456-511` `_update_history` is the only writer of `data/history.json` and has no schema validation - cross-scope to jcstream-python-architecture (data model lives in scraper, write lives in web).
- `scraper/parsers.py` charge ordering and `inmate_number` extraction defenses - cross-scope to jcstream-python-parser-robustness; if charges are sorted at parse time, data-F3 closes from the other side.
- `scraper/sweep.py:152-155` checkpoint-write semantics and KeyboardInterrupt recovery - cross-scope to jcstream-python-sweep-reliability; this audit only flagged the missing comment.
- `scraper/sweep.py:290-314` `_prune_photos` 50% guard and ordering vs `save_current` - cross-scope to jcstream-python-sweep-reliability for the guard, this audit only flagged the ordering pin.
- `web/build.py:48-49` consumes `Snapshot(**raw)` directly; any new Snapshot validator runs there too, so data-F2 hardens the build path as a side effect - cross-scope ack only.

## Confidence and limitations

- High confidence: invariant checks against the live `data/current.json` (1210 inmates, count matches, ids unique, no empty ids, all photo refs present, no orphans) and the live `data/changelog.json` (500 events, ascending by timestamp, only `booked` and `released` present in the live window).
- High confidence: code-level findings on `_materially_changed` order-sensitivity, missing model-level invariants, and the schema-version gap. These are derived directly from the source.
- Medium confidence: severity of data-F1. The migration-path failure is hypothetical until the model changes; the impact would be high if it triggered, hence the rating.
- Limitation: I did not exercise the failure paths under load. I read tests and inferred behavior; the pytest suite is reported green at baseline.
- Limitation: `data/history.json` is touched only by `web/build.py`, which is technically out of primary scope. The shape and write logic are summarized; remediation belongs in an architecture sweep.

End of report.
