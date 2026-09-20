# Audit — jcstream-test-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-test-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-test-author.md
- **Verdict**: Red
- **One-line summary**: Multiple stale numeric claims, two non-existent dependencies are recommended for use, one referenced test file does not exist, and ~half of the actual test suite is unmentioned.

## A. Drift
- **Test count wrong.** SKILL.md:3, :8, :57 say "148 tests". Actual count of `def test_*` functions across `tests/*.py` is **140** (verified `grep -rn "^def test_\|^async def test_" tests/ | wc -l`). CLAUDE.md says "currently 34 tests" — also stale; the truth is 140. Agent file `.claude/agents/jcstream-test-author.md:12,16` repeats the 148 number.
- **Test-file count off-by-one.** SKILL.md:8 / agent:12 say "15 files". `tests/` contains **14** test files plus `__init__.py` and `fixtures/` (`tests/test_*.py` ⇒ 14). 15 only matches if `__init__.py` is counted.
- **Lines total matches.** SKILL.md:8 says 1707 lines — `wc -l` confirms 1707 total. OK.
- **`test_sweep_guards.py` does not exist.** SKILL.md:24 lists it; SKILL.md:40 references `sweep_guards.py`. The guards function `sweep_looks_healthy` lives at `scraper/sweep_guards.py:46` but is exercised inside `tests/test_sweep.py:23-190`, not a dedicated file.
- **`respx` is not a dependency and is not used.** SKILL.md:35 says "mock with `respx` (already a transitive dep through httpx)". `grep -rn respx` returns zero matches in `requirements.txt`, `pyproject.toml:11-17`, and `tests/`. Recommending it as the network-mock convention is misleading; the actual convention is `monkeypatch` (e.g. `tests/test_client.py:38,53,67,83,99,113,126`, `tests/test_pra_send.py:17-110`).
- **`selectolax` template-parse pattern is aspirational.** SKILL.md:41 says "render with a fixture snapshot, parse the result with `selectolax`". `grep selectolax tests/` returns nothing. `selectolax` is a real dep (`pyproject.toml:13`) used only in `scraper/parsers.py:10` and copy at `web/build.py:1638`. No test renders a Jinja template through `selectolax`.
- **`Snapshot(inmates=[...])` constructor pattern.** SKILL.md:34 says "Inline `Snapshot(inmates=[...])` constructors are fine". `Snapshot` is constructed in `tests/test_models.py:54,63,73,81,87` only — the build-helper tests in `tests/test_build.py:14-26` use `Inmate` directly, not `Snapshot`. Pattern is partially accurate but miscredits where it appears.
- **Layout list omits `_card.html`-style breakdown.** SKILL.md:18-28 lists 8 file slots (with "…"); the unlisted real files include test_build.py (444 LOC, now the largest), test_sweep.py (255 LOC), test_shape.py (225 LOC), test_parsers.py (192 LOC), test_store.py (174 LOC), test_client.py (133 LOC), test_pra_send.py (117 LOC), test_open_data.py (113 LOC), test_models.py (112 LOC), test_ingest_issue.py (85 LOC), test_pra.py, test_orc.py, test_photos.py, test_courtclerk.py, test_cincy_open.py, test_match.py.

## B. Coverage gaps
- **`tests/fixtures/` HTML scaffold is unmentioned.** `tests/fixtures/README.md:1-30` defines a strict naming policy (DOE/ROE/VOE + JOHN/JANE), the no-real-records rule under ORC 149.43, and three offline HTML fixtures (`list_smith.html`, `detail_inmate.html`, `detail_no_photo.html`). This is the single most important convention for this skill and SKILL.md never mentions the directory.
- **HTML parser test pattern.** `tests/test_parsers.py:1-163` is the canonical example of feeding fixture HTML through `parse_detail_page`/`parse_list_page` (`tests/test_parsers.py:5`), exercising the orphan-row guard, the `?id=` → `/inmate-detail/N/` permalink shift, and base64 photo extraction — none of this surfaces in SKILL.md.
- **`SnapshotCorruptError` / store schema-version contract.** `tests/test_store.py:7,145,152,164` enforces the schema_version round-trip. SKILL.md:25 mentions test_store.py vaguely as "photo cache / data writes" but misses the corruption-guard contract.
- **PRA SMTP send path.** `tests/test_pra_send.py` (117 LOC) covers the live-send branch (STARTTLS at 587, implicit TLS at 465, missing-credentials skip, SMTP failure). SKILL.md:26 only acknowledges "PRA email loop (dry-run path)".
- **HCSO httpx client retry/backoff harness.** `tests/test_client.py:38-129` is the template for retry-on-5xx, Retry-After honoring, and env-var override testing — a pattern future scraper tests should mirror. Not mentioned.
- **GitHub-issue ingest tests.** `tests/test_ingest_issue.py:1-85` (parses issue body, builds case record, upserts) is invisible in SKILL.md but represents an active code path.
- **Cincinnati Open Data shape tests.** `tests/test_open_data.py` (113 LOC) and `tests/test_cincy_open.py` cover the four open-data feeds called out in CLAUDE.md.

## C. Trigger-phrase quality
- Current description (paraphrased): "Use when writing or updating pytest tests under tests/. Covers snapshot/fixture conventions, network mocking with respx or monkeypatch, build.py helper tests, scraper integration tests, and creating tests/conftest.py. 148 tests must stay green. Trigger phrases: 'write a test for', 'fix the failing test', 'add coverage'."
- Issues: triggers will fire on the obvious phrasings. Missing common JCStream-specific phrasings: "regression test", "pytest", "test the parser", "fixture for", "the suite is failing", "tests/", "monkeypatch". The `respx` mention may misroute the model toward suggesting an absent library.
- Proposed rewording: "Use when writing or updating pytest tests under `tests/` in JCStream — `test_build.py`, `test_sweep.py`, `test_parsers.py`, `test_store.py`, `test_pra_send.py`, etc. Covers offline HTML fixtures in `tests/fixtures/` (DOE/ROE placeholder names, ORC 149.43 no-real-records rule), `monkeypatch`-based network/SMTP mocking, the schema-version guard in `test_store.py`, and the absent `tests/conftest.py`. 140 tests must stay green. Trigger phrases: 'write a test for', 'add a regression test', 'fix the failing test', 'add coverage', 'test the parser', 'fixture for', 'the suite is failing', 'pytest'."

## D. Applicability
- Domain is fully alive — `tests/` is the most active leaf in the agent topology (every code-path chain ends here per `.claude/skills/README.md:31,39`); the skill should not be retired, only corrected.

## Recommended fixes (priority order)
1. Replace every "148 tests" mention with "140 tests" (SKILL.md:3,8,57; agent:12,16) and update CLAUDE.md's "currently 34 tests" line in tandem.
2. Drop the `respx` recommendation; document the actual `monkeypatch` convention with citations to `tests/test_client.py` and `tests/test_pra_send.py`.
3. Add a "Fixtures" subsection that points at `tests/fixtures/README.md` and the DOE/ROE placeholder rule before any new HTML test is authored.
4. Remove `test_sweep_guards.py` from the layout (or note guards live in `tests/test_sweep.py:23-190`).
5. Expand the layout list to include the eight unmentioned files, especially `test_parsers.py`, `test_open_data.py`, `test_pra_send.py`, `test_client.py`.
6. Either ship a real `selectolax`-based template-render example or remove SKILL.md:41 — currently it tells the agent to use a pattern no test in the repo demonstrates.
7. Broaden the trigger-phrase list per section C.
