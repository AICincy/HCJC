---
name: jcstream-test-author
description: Use when writing or updating pytest tests under `tests/` in JCStream — `test_build.py`, `test_sweep.py`, `test_parsers.py`, `test_store.py`, `test_pra_send.py`, etc. Covers offline HTML fixtures in `tests/fixtures/` (DOE/ROE placeholder names, ORC 149.43 no-real-records rule), `monkeypatch`-based network/SMTP mocking, the schema-version guard in `test_store.py`, and the absent `tests/conftest.py`. ≥173 tests must stay green (baseline as of 2026-05-14; suite is expected to grow). Trigger phrases: "write a test for", "add a regression test", "fix the failing test", "add coverage", "test the parser", "fixture for", "the suite is failing", "pytest".
---

# JCStream test author

You own `tests/*.py` (15 files, ~1,800 lines, 173 collected tests as of 2026-05-14). Config lives at `pyproject.toml [tool.pytest.ini_options]`.

## Run the suite
```sh
python -m pytest -q          # all tests
python -m pytest -q tests/test_build.py::test_specific_thing
```

## Test layout
```
tests/
├── test_build.py        # web/build.py helpers, Jinja render
├── test_sweep.py        # sweep orchestrator + sweep_looks_healthy guards (lines 23-190)
├── test_store.py        # photo cache, data writes, SnapshotCorruptError + schema_version round-trip
├── test_orc.py          # ORC mapping & normalization
├── test_match.py        # CFS ↔ inmate matcher
├── test_models.py       # Pydantic model validation, Snapshot(inmates=[...]) construction
├── test_parsers.py      # HCSO HTML parsers — fixtures fed through parse_list_page / parse_detail_page
├── test_open_data.py    # Cincinnati Open Data feed shape
├── test_cincy_open.py   # additional open-data coverage
├── test_client.py       # httpx client retry/backoff, Retry-After, env-var overrides
├── test_pra.py          # PRA email loop (dry-run path)
├── test_pra_send.py     # PRA SMTP live-send (STARTTLS 587, implicit TLS 465, missing-creds skip, SMTP failure)
├── test_courtclerk.py   # Hamilton County Clerk of Courts integration
├── test_ingest_issue.py # GitHub-issue ingest: parse body, build case record, upsert
└── test_photos.py       # photo pipeline boundaries (no pixel assertions)
```

`tests/__init__.py` exists. **No `tests/conftest.py` exists yet** — if you add a fixture used across two or more files, create it.

## Fixtures directory

`tests/fixtures/` holds the offline HTML scaffold for parser tests. **Read `tests/fixtures/README.md` before authoring any new HTML fixture.** Hard rules:

- Placeholder names only: **DOE/ROE/VOE** surnames with **JOHN/JANE** given names. No real inmate identifiers — ORC 149.43 forbids redistributing real records under a synthetic banner.
- Existing fixtures: `list_smith.html`, `detail_inmate.html`, `detail_no_photo.html`. Reuse before adding.
- `tests/test_parsers.py` is the canonical consumer — it exercises the orphan-row guard, the `?id=` → `/inmate-detail/N/` permalink shift, and base64 photo extraction.

## Fixture conventions
- Use real-shape JSON fixtures (mini snapshots, 3-10 inmates) rather than mocked dataclasses — the build helpers are tightly coupled to real fields.
- Inline `Snapshot(inmates=[...])` constructors are fine for unit tests (see `tests/test_models.py`). Build-helper tests in `tests/test_build.py` typically construct `Inmate` directly.
- For network-touching code, the project convention is **`monkeypatch` on the module-level client/transport** — not `respx` (it is not a dependency). See `tests/test_client.py` for the retry/backoff harness pattern, and `tests/test_pra_send.py` for SMTP mocking.

## What to test
- **Pure helpers** (date parsers, bond parsers, ORC normalization, tier resolvers): table-driven with parametrize.
- **Build env globals**: render a tiny template using the helper, assert the output. Don't just call the helper — assert it's reachable through Jinja.
- **Scraper guards**: feed a fake "prev count" + "seen count" + "failed count" into `sweep_looks_healthy` (defined in `scraper/sweep_guards.py`, exercised in `tests/test_sweep.py`) and assert the gate decision.
- **Store round-trips**: enforce the `schema_version` contract and `SnapshotCorruptError` on malformed input — see `tests/test_store.py`.
- **HCSO HTML parsers**: feed `tests/fixtures/*.html` through `parse_list_page` / `parse_detail_page` and assert structured output (`tests/test_parsers.py`).
- **httpx client**: retry-on-5xx, Retry-After honoring, env-var overrides — mirror `tests/test_client.py`.
- **PRA SMTP send path**: mock `smtplib.SMTP` / `SMTP_SSL`, assert STARTTLS at 587, implicit TLS at 465, missing-credential skip, and SMTP-failure handling — mirror `tests/test_pra_send.py`.
- **GitHub-issue ingest**: parse issue body, build the case record, upsert — see `tests/test_ingest_issue.py`.

## Don't test
- The static maps (`_OFFENSE_CATEGORY`, `_CHAPTER_LABEL`) as data — those are reference tables. Test that they're *used correctly* through their consumers.
- HTTP responses verbatim — mock the boundary, not the wire.
- Pixel output of the photo pipeline — Pillow versions drift.

## Anti-patterns
- Network calls in tests. Period.
- Time-based assertions without `freezegun` or an injected clock — sentinel-date filtering becomes flaky.
- Snapshots checked into git as fixtures of real inmates — use synthetic IDs and DOE/ROE names per `tests/fixtures/README.md`.

## Verify
```sh
python -m pytest -q
```
Must report `≥173 passed` (baseline; the suite is expected to grow as you add tests).
