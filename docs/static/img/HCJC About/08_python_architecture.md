# arch - Python Architecture Audit

## Audit metadata
- Skill: jcstream-python-architecture
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 21 (scraper/__init__.py 3, scraper/cfs.py 89, scraper/cfs_pdi.py 78, scraper/cincy_open.py 56, scraper/client.py 110, scraper/courtclerk.py 43, scraper/incidents.py 76, scraper/ingest_issue.py 134, scraper/match.py 84, scraper/models.py 80, scraper/orc.py 89, scraper/parsers.py 208, scraper/photos.py 37, scraper/pra.py 118, scraper/pra_capias.py 127, scraper/pra_jms_vendor.py 132, scraper/shootings.py 76, scraper/store.py 150, scraper/sweep.py 355, web/__init__.py 1, web/build.py 1282; plus pyproject.toml 26)
- Time: 2026-05-14T01:42:54Z

## Observations
- `web/build.py` (1282 lines) carries at least seven concerns at top level: Jinja env wiring, ORC offense classification (`_OFFENSE_CATEGORY`, `_CHAPTER_LABEL`, `_CLS_RANK`), per-inmate display helpers (`_primary_tier`, `_charge_tier`, `_bond_by_tier`, `_card_tip`), snapshot reshaping (`_group_by_month`, `_events_for_recent`, `_update_history`), feed generation (`_render_feeds`, `_render_index`), data emission (`_write_search_json`, `_write_dispatches`, `_write_checksums`), and stats aggregation (`_compute_stats`).
- Direction of dependency between packages is clean: `web/build.py` imports from `scraper/*`, but nothing in `scraper/*` imports from `web/*`. No boundary inversion.
- One test reaches a private symbol: `tests/test_sweep.py:6: from scraper.sweep import _sweep_looks_healthy`. The guard heuristic deserves to be a public name since it has its own tunable constants (`SWEEP_MAX_FAILED_FRACTION`, `SWEEP_MIN_ROSTER_FRACTION`, `SWEEP_BOOTSTRAP_FLOOR`).
- `scraper/sweep.py` (355 lines) mixes orchestration (`run`, `_sweep_list`, `_fetch_one`) with health heuristics (`_sweep_looks_healthy`, `_check_detail_watchdog`, `_prune_photos`) and their constants. The two concerns have different change cadences: orchestration changes when HCSO endpoints change; heuristics change when an incident proves a threshold wrong.
- `scraper/store.py` mixes persistence (`_atomic_write_text`, `load_current`, `save_current`, `load_changelog`, `save_changelog`) with pure diff logic (`diff`, `_materially_changed`). The diff functions have no I/O and could move to `models.py` or a `changes.py` for clearer reuse.
- The three PRA modules (`pra.py`, `pra_capias.py`, `pra_jms_vendor.py`) duplicate ~60-70 lines each: identical `_env`, identical `_send_smtp`, near-identical `_build_message`, identical dry-run pattern. Each differs only in subject, body template, default TO env-var name, and the per-call signature.
- File paths are hardcoded at module scope across the scraper: `Path("data/photos")`, `Path("data/current.json")`, `Path("data/changelog.json")` in `sweep.py`; `Path("data/cfs_recent.json")` in `cfs.py`; etc. Tests pass explicit paths in, so this is a smell rather than a bug, but `run()` in `sweep.py` does not accept paths as parameters.
- CLI hygiene is consistent: `web/build.py`, `scraper/sweep.py`, `scraper/cfs.py`, `scraper/cfs_pdi.py`, `scraper/shootings.py`, `scraper/incidents.py`, `scraper/ingest_issue.py`, `scraper/pra.py`, `scraper/pra_capias.py`, `scraper/pra_jms_vendor.py` each have `main()` + `if __name__ == "__main__": sys.exit(main())`. No drift to flag.
- Side effects at import time are absent. `make_client()` is a factory; `data/*.json` paths are constants, not opens. Logging is configured inside `main()`, not at module load.

## Analysis

The repository is structured into two top-level packages (`scraper`, `web`) plus tests, and the dependency direction is the right one. `web/build.py` depends on `scraper.models`, `scraper.orc`, `scraper.match`, `scraper.cfs`, `scraper.cfs_pdi`, `scraper.shootings`, `scraper.courtclerk`. None of the scraper modules pull anything from `web`. That single invariant is the most valuable architectural property the project has, and the audit found no violation.

The dominant smell is concentration, not coupling. `web/build.py` is doing too many things, and the things it is doing are separable along clean lines. The file holds three classes of helper: (a) ORC classification tables and the pure functions that consume them (`_OFFENSE_CATEGORY`, `_offense_for_code`, `_primary_chapter`, `_primary_charge`, `_charge_tier`, `_tier_counts`, `_primary_tier`, `_bond_by_tier`, `_card_tip`, `_crimes_of_month`, `_charges_by_chapter`, `_orc_frequency`); (b) snapshot reshaping (`_group_by_month`, `_sort_in_group`, `_events_for_recent`, `_update_history`, `_parse_md_yy`, `_short_month_label`); and (c) output emitters (`_render_index`, `_render_inmates`, `_render_feeds`, `_render_data_page`, `_render_stats_page`, `_write_search_json`, `_write_dispatches`, `_write_manifest`, `_write_cname`, `_write_well_known`, `_write_checksums`, `_copy_static`, `_copy_photos`). Splitting (a) into `web/classify.py`, (b) into `web/shape.py`, and (c) staying behind `web/build.py` would drop `build.py` by roughly 600 lines without changing any rendered byte. The split is observable from the tests because Jinja-globals registration in `build()` would import from the new modules, so a broken import would surface immediately.

`scraper/sweep.py` is the second-largest concentration. The orchestrator carries three guards: list-sweep degradation (`_sweep_looks_healthy`), detail-fetch degradation (`_check_detail_watchdog`), and photo-prune safety (`_prune_photos` with `PHOTO_PRUNE_MAX_FRACTION`). Each has a constant nearby, and each is logically pure (takes counts in, returns bool or applies a guarded side effect). The orchestrator itself is `run()` plus `_sweep_list()` plus `_fetch_one()`. A `scraper/sweep_guards.py` module would let `tests/test_sweep.py` import a public surface instead of `_sweep_looks_healthy`, and a future change to thresholds would touch one file. The test suite already covers the guard, so the split has a test hook.

`scraper/store.py` is borderline. `diff()` and `_materially_changed()` are pure functions over `Inmate` mappings; the rest is filesystem I/O. They are co-located today because the historical interface is "compare and persist". With the schema stable and the diff logic now testable in isolation (it already is, indirectly), moving `diff` next to `models.Inmate` (where the "materially changed" definition belongs) tightens cohesion. This is a low-leverage refactor; only do it if pushing on `store.py` further.

The PRA family is a genuine duplication. Each of `pra.py`, `pra_capias.py`, `pra_jms_vendor.py` repeats: an `_env` helper, an `_send_smtp` helper that branches on port 465, a `_build_message` that fills `From`/`To`/`Subject`/body, and a `send_*_request` that checks for dry-run conditions. The differences are entirely the subject string, the body template, the default `TO` env-var name (`JCSTREAM_PRA_TO_*_EMAIL`), and the date-window signature (capias/photos take `since, until`; jms_vendor takes nothing). A `scraper/pra/base.py` exposing `send_request(*, subject, body, to_env_var, label)` and three thin modules that build the body and call the base would cut ~200 lines and centralize the SMTP-secret handling. Since SMTP is the security-sensitive line and there are three near-identical copies of it today, that consolidation also reduces drift risk.

The Cincinnati Open Data fan-out (`cfs.py`, `cfs_pdi.py`, `shootings.py`, `incidents.py`) already factored `cincy_open.py` as a shared SODA client; `cfs_pdi.py`, `shootings.py`, `incidents.py` use it, but `cfs.py` still inlines its own httpx call. That looks like an artifact of `cfs.py` being the first feed written; folding `cfs.py` onto `cincy_open.query` would make the four feeds homogeneous, which makes adding a fifth feed (or testing one offline) a 30-line addition.

Path injection: tests already pass explicit `Path` arguments through to `save_current`, `load_current`, `save_changelog`, `load_changelog`. The remaining hardcoded paths are in `sweep.run()` and in the module-level defaults of the feed pullers. Adding an optional `paths` dataclass to `sweep.run()` (not a config file) is the cheapest way to make the orchestrator unit-testable without writing into the repo's `data/` directory. CLAUDE.md is explicit that no config-file ceremony is desired; a default-instance dataclass keeps the surface flat.

Re-exports at package level are absent (`scraper/__init__.py` is one line, `web/__init__.py` is one line). That is appropriate for this size of project. Do not add re-exports.

## Technical notes

```
# web/build.py concern map (line ranges, observed)
ORC classification tables + helpers    : 188-345, 376-460, 519-537, 600-636, 666-725
Render-side display helpers            : 463-505, 508-516, 558-583, 586-597, 639-663, 728-744
Snapshot reshaping                     : 747-832, 963-1001
Env / URL resolution                   : 834-872
Output emission (HTML / JSON / feeds)  : 875-922, 932-960, 1004-1080, 1082-1255, 1258-1265
Entrypoint                             : 1268-1282
```

```
# scraper/sweep.py concern map
Sweep guards + constants    : 40-70, 182-204, 287-314
Orchestration (CLI + run)   : 73-180, 207-285, 317-355
```

```
# Duplicated PRA SMTP envelope (verbatim across all three modules)
def _send_smtp(msg: EmailMessage) -> None:
    host = _env("JCSTREAM_PRA_SMTP_HOST")
    port = int(_env("JCSTREAM_PRA_SMTP_PORT") or "587")
    user = _env("JCSTREAM_PRA_SMTP_USER")
    password = _env("JCSTREAM_PRA_SMTP_PASS")
    if not host:
        raise RuntimeError("JCSTREAM_PRA_SMTP_HOST is not set")
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            ...
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            ...
```

```
# Boundary check (only direction observed)
scraper.*  ->  scraper.*               OK (cfs_pdi/shootings/incidents use cincy_open)
web.build  ->  scraper.cfs|cfs_pdi|courtclerk|orc|shootings|match|models   OK
scraper.*  ->  web.*                   NONE
```

```
# Private-symbol import from test (only one)
tests/test_sweep.py:6:   from scraper.sweep import _sweep_looks_healthy
```

```
# CLI pattern is uniform across runnable modules
def main(argv: list[str] | None = None) -> int: ...
if __name__ == "__main__":
    sys.exit(main())
```

```
# Hardcoded data paths in module scope (representative)
scraper/sweep.py:36   PHOTOS_DIR    = Path("data/photos")
scraper/sweep.py:37   CURRENT_PATH  = Path("data/current.json")
scraper/sweep.py:38   CHANGELOG_PATH= Path("data/changelog.json")
scraper/cfs.py:25     CFS_PATH      = Path("data/cfs_recent.json")
scraper/cfs_pdi.py:25 LOCAL_PATH    = Path("data/cfs_pdi_recent.json")
scraper/shootings.py:20 LOCAL_PATH  = Path("data/shootings_recent.json")
scraper/incidents.py:22 LOCAL_PATH  = Path("data/incidents_recent.json")
```

## Findings

### arch-F1. `web/build.py` is a god module along three separable axes
- Severity: medium. Confidence: high.
- File(s): web/build.py (1282 lines).
- Smell: ORC classification tables + functions, snapshot reshaping, and output emitters live in the same file. The classification tables alone are ~130 lines of literal data.
- Why it matters: every edit to a Jinja global or a renderer touches the same file as every classification-table change. Diff review surface is wider than necessary, and a future "add a feed" change crosses three concerns.
- Fix: extract `web/classify.py` (ORC tables + `_offense_for_code`, `_primary_charge_obj`, `_primary_chapter`, `_primary_charge`, `_charge_tier`, `_tier_counts`, `_primary_tier`, `_bond_by_tier`, `_card_tip`, `_charges_by_chapter`, `_crimes_of_month`, `_orc_frequency`) and `web/shape.py` (`_group_by_month`, `_sort_in_group`, `_parse_md_yy`, `_short_month_label`, `_events_for_recent`, `_events_in_window`, `_update_history`). Keep `build.py` as the orchestrator + Jinja env wiring + emitters.

### arch-F2. `scraper/sweep.py` orchestration is fused with health heuristics
- Severity: medium. Confidence: high.
- File(s): scraper/sweep.py (lines 40-70, 182-204, 287-314).
- Smell: `_sweep_looks_healthy`, `_check_detail_watchdog`, `_prune_photos`, and their four constant blocks share the file with the orchestrator. Tests already reach `_sweep_looks_healthy` by its underscore name.
- Why it matters: threshold edits and orchestration edits have different cadences. A guard tweak should not require reading a 355-line file, and the guards each have their own meaningful test surface.
- Fix: create `scraper/sweep_guards.py` exposing `sweep_looks_healthy`, `check_detail_watchdog`, `prune_photos` plus their constants. `sweep.py` imports the public names. `tests/test_sweep.py` updates one import line.

### arch-F3. PRA modules duplicate the SMTP envelope three times
- Severity: medium. Confidence: high.
- File(s): scraper/pra.py, scraper/pra_capias.py, scraper/pra_jms_vendor.py (each carries `_env`, `_send_smtp`, `_build_message`, dry-run branch).
- Smell: ~70% of each file is the same SMTP boilerplate. Differences are subject string, body, TO env-var, and the request-window signature.
- Why it matters: SMTP secrets handling is the security-load-bearing path. Three copies means three places to keep in sync if (for example) port handling changes or a new transport is added. There is no SRP win to the duplication.
- Fix: introduce `scraper/pra_base.py` (single module, not a package) with `send_pra_request(*, subject: str, body: str, to_env_var: str, label: str) -> int` and move the SMTP+dry-run logic there. Each of the three callers becomes 30-40 lines of body template + a single function call. tests/test_pra.py and tests/test_pra_send.py exercise the consolidated path.

### arch-F4. `scraper/store.py` mixes persistence and pure diff logic
- Severity: low. Confidence: high.
- File(s): scraper/store.py (`diff`, `_materially_changed` lines 87-150 vs the rest).
- Smell: `diff` and `_materially_changed` are pure functions over `Inmate` mappings, sharing a module with atomic I/O.
- Why it matters: the diff definition of "materially changed" is part of the data model, not part of persistence. Keeping them together blurs the responsibility boundary. The data-integrity audit will want to point at the diff in isolation.
- Fix: optional. If pushing further on `store.py`, move `diff` and `_materially_changed` to `scraper/changes.py` (or as a `@staticmethod` on `Snapshot`). Re-export from `scraper.store` for backward compatibility for one cycle, then remove. Skip if you do not have an unrelated reason to touch store.py.

### arch-F5. `scraper/cfs.py` inlines its own httpx call instead of using `cincy_open.query`
- Severity: low. Confidence: high.
- File(s): scraper/cfs.py:28-50 vs scraper/cincy_open.py:34-56.
- Smell: three of the four Socrata feeds (`cfs_pdi`, `shootings`, `incidents`) route through `cincy_open.query`; `cfs.py` did not get migrated.
- Why it matters: adding a header, switching to httpx async, or adding a retry policy is two-place-edit work for no reason. Pure cleanup; no behavior change.
- Fix: rewrite `cfs.pull_recent` to call `cincy_open.query(DATASET_ID, where=..., order=..., limit=...)`. Drop the local httpx import. The test fixture in `tests/test_open_data.py` already covers `cincy_open.query`.

### arch-F6. Test imports a private guard symbol
- Severity: low. Confidence: high.
- File(s): tests/test_sweep.py:6.
- Smell: `from scraper.sweep import _sweep_looks_healthy`. The underscore signals private but the test treats it as public.
- Why it matters: the guard is a stable, intentionally-testable surface. Calling it private invites a future refactor to rename or move it and silently break the test, or worse, to remove the test because "it's testing a private helper".
- Fix: resolved by arch-F2 (export as `sweep_looks_healthy` from `scraper/sweep_guards.py`). If not doing the split, rename to `sweep_looks_healthy` in place.

### arch-F7. Hardcoded data-paths in `sweep.run()` block local re-runs
- Severity: low. Confidence: medium.
- File(s): scraper/sweep.py (module constants `CURRENT_PATH`, `CHANGELOG_PATH`, `PHOTOS_DIR`).
- Smell: `run()` takes surnames and flags but never takes paths; it always writes `data/current.json`. The persistence functions in `store.py` are properly parameterized, but the orchestrator is not.
- Why it matters: running the sweep with `--dry-run` already skips writes, so this is not a correctness gap. It is a testability and local-development friction point. Not urgent.
- Fix: optional. Add a small `SweepPaths` dataclass with default-factory fields (`current`, `changelog`, `photos`), pass it through `run()`, and let `main()` build the default instance. Tests for `_check_detail_watchdog` and `_prune_photos` (if added) can then run without touching `data/`. Skip if not adding sweep tests.

## Recommendations

- arch-R1 (for arch-F1): split `web/build.py` into `web/build.py` + `web/classify.py` + `web/shape.py`. Move the ORC tables and tier helpers to `classify.py`; move month/event/history reshapers to `shape.py`. `build.py` keeps orchestration, Jinja env globals registration, and emitters.
- arch-R2 (for arch-F2): create `scraper/sweep_guards.py` and move `sweep_looks_healthy`, `check_detail_watchdog`, `prune_photos`, plus the five `SWEEP_*` / `DETAIL_WATCHDOG_*` / `PHOTO_PRUNE_*` constants. `sweep.py` imports them.
- arch-R3 (for arch-F3): create `scraper/pra_base.py` exposing `send_pra_request(subject, body, to_env_var, label)`. Reduce `pra.py`, `pra_capias.py`, `pra_jms_vendor.py` to body templates plus a single call each.
- arch-R4 (for arch-F4): defer unless touching `store.py` for another reason. When you do, move `diff` and `_materially_changed` to `scraper/changes.py` and re-export from `scraper.store` for one cycle.
- arch-R5 (for arch-F5): route `cfs.pull_recent` through `cincy_open.query`.
- arch-R6 (for arch-F6): renamed/exported as part of arch-R2; otherwise rename in place to `sweep_looks_healthy`.
- arch-R7 (for arch-F7): defer. Add a `SweepPaths` dataclass only when adding tests for the orchestrator that need a tmp dir.

## Remediation plan

1. arch-R5 first. One file, ~25 lines changed in `scraper/cfs.py`. Re-run `python -m pytest -q`; `tests/test_open_data.py` already covers the path. No new tests needed.
2. arch-R2. Create `scraper/sweep_guards.py`, move three functions and five constants, leave `from .sweep_guards import sweep_looks_healthy, check_detail_watchdog, prune_photos` at the top of `sweep.py`. Update `tests/test_sweep.py:6` to `from scraper.sweep_guards import sweep_looks_healthy`. Pytest stays at 102 passed.
3. arch-R3. Create `scraper/pra_base.py` with `send_pra_request`. Refactor `pra.py`, `pra_capias.py`, `pra_jms_vendor.py` to import it. `tests/test_pra.py` and `tests/test_pra_send.py` continue to assert on the same public functions (`send_daily_request`, `send_request`). If any test reaches a private helper, expose the equivalent on `pra_base`.
4. arch-R1. Split `web/build.py`. Move ORC classification block + helpers into `web/classify.py`; move snapshot-shape helpers into `web/shape.py`. `build.py` imports both at the top and registers Jinja globals as before. Run `python -m web.build` to confirm byte-identical output (compare `docs/` hashes before and after on the same `data/current.json`). Run pytest.
5. arch-R6 falls out of step 2. arch-R4 and arch-R7 are deferred.

Each step is independently green-able. Do not combine steps 1-4 into one commit.

## Cross-references

- Sweep guard thresholds, photo-prune safety, and recovery paths -> jcstream-python-sweep-reliability.
- Atomic-write semantics, changelog limits, diff invariants -> jcstream-python-data-integrity.
- Parser drift, label-based table parsing, name heading -> jcstream-python-parser-robustness.
- TLS verify=False, retry/backoff, SMTP secret handling -> jcstream-python-security-networking.
- Coverage gaps in the suggested splits -> jcstream-python-test-gap-analysis.
- Template escaping, ld+json, inline JS in build outputs -> jcstream-html-template-security.

## Confidence and limitations

Confidence is high on the file-level concerns (F1, F2, F3, F5, F6): they are mechanical, observable in `git diff`, and each has a test hook. Confidence is medium on F4 and F7 because both are judgement calls about future change cost rather than current friction. The audit did not run the build or the sweep; it relied on static reading and the reported pytest baseline (102 passed). No outbound network access was needed and none was attempted. The audit deliberately did not flag `web/build.py` length on its own; each F1 finding names the responsibilities to extract. The audit also did not flag `verify=False`, parser fragility, schema/changelog semantics, or test coverage gaps, per scope.

End of report.
