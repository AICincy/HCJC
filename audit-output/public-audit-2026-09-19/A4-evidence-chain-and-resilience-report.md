# A4 evidence-chain and resilience report

**Claim ID:** `A4-EVIDENCE-RESILIENCE-001`  
**Audit question:** In a dependency-complete disposable environment, do the frozen WAF and PRA chain verifiers and controlled malformed-takedown inputs exhibit their documented behavior without changing HCJC or its source data?  
**Completion condition:** Run both local verifiers, targeted chain tests, aggregate-only inspection, and synthetic missing, malformed, invalid-shape, and unreadable takedown fixtures. Record the post-run worktree state.  
**Technical verdict:** **Partial**. The existing parsed chains verify and link-tamper detection works. Two controlled failure paths do not meet a fail-closed evidence contract: malformed WAF JSON receives a successful empty-log verdict, and a wrapped-object takedown payload is accepted without applying its contained synthetic ID.

## Baseline, scope, and environment

| Field | Evidence |
|---|---|
| Frozen repository | `https://github.com/AICincy/HCJC.git` at `fbe33ca9af7db6e08ab4a6f16515ece26085b241` (`data+site: sweep 2026-09-19T19:28Z`) |
| Execution worktree | Detached A4 worktree: `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-a4` |
| UTC observation window | `2026-09-19T19:28:48Z` through `2026-09-19T20:07:47Z` |
| Interpreter and isolated packages | Windows, Python `3.14.6`, `pydantic 2.13.5`, `pytest 9.1.1`; declared dependencies installed only into ignored `.venv/` in the A4 worktree |
| Frozen source-input identity | `data/waf_block_log.json`: Git blob `c979cb765c11e0dc8f5cb06727fa643a27c36c7c`, observed SHA-256 `bca55d861aa7e4939352ef771f99c090b4a13f4bef1bf42d5d4b05baad7133f7`; `data/pra_requests.json`: Git blob `d4f3987b2b8a6d966862919918c6e19652133bf7`, observed SHA-256 `a792a6df7406bd47a6dd27da0af8a865fa72df748edf88bd48cb5b751296a9fe` |
| Access boundary | Public frozen source, local read-only ledgers, and synthetic files in a system temporary directory only. No source data, workflow, configuration, account, secret, mail, deployment, or official-source comparison was changed or accessed. |
| Privacy boundary | This report contains aggregate counts, dates, hashes, and synthetic-fixture outcomes only. It contains no person-level jail, contact, or credential data. |

## Requirement and evidence matrix

| Requirement or risk | Observable behavior | Fresh evidence | Result | Gap |
|---|---|---|---|---|
| Existing WAF ledger chain | CLI accepts every parsed link in the frozen ledger | `python -m scraper.verify_block_log` exited `0`; reported `137,023` records | Pass, Grade C | A successful parsed-chain check does not prove historic completeness, Git history, or live WAF behavior. |
| Existing PRA ledger chain | CLI accepts every parsed link in the frozen ledger | `python -m scraper.verify_pra_log` exited `0`; reported `352` records | Pass, Grade C | Does not establish current mail configuration, delivery, or present owner intent. |
| Chain tampering detection | Changed predecessor changes break the next link | Two-record synthetic WAF and PRA chains each passed intact; each one-record alteration caused its respective CLI to exit `1` | Pass, Grade D | Small controlled fixture only. |
| Corrupt WAF verifier input | Malformed JSON must not become a successful integrity result | Synthetic malformed WAF JSON made `verify_block_log` exit `0` and state that there were no records | **Fail**, Grade D | The CLI cannot distinguish missing or malformed WAF input through its normal result. |
| Corrupt PRA verifier input | Malformed JSON must fail rather than be accepted as intact | Synthetic malformed PRA JSON exited `1` with `JSONDecodeError` | Partial, Grade D | Failure is loud, but not a normalized verifier result. |
| Missing takedown file | Missing file permits normal output persistence | Synthetic output write completed with one retained synthetic record | Pass, Grade D | Controlled write-boundary evidence only. |
| Malformed or scalar takedown input | Persistence must preserve the prior output | Malformed JSON and scalar JSON each raised `SnapshotCorruptError`; prior synthetic output bytes were unchanged | Pass, Grade D | Full network sweep was deliberately not run. |
| Invalid takedown shape | A non-array payload should not silently alter the seal set | Direct-key object was accepted as keys. Wrapped object was accepted and its contained synthetic ID remained in the output. | **Fail**, Grade D | Static code also permits mappings in `sweep.run`; owner intent and desired schema are unresolved. |
| Unreadable takedown path | Failure must preserve the prior output | A directory at the file path raised `PermissionError`; prior synthetic output bytes were unchanged | Partial, Grade D | Preservation is fail-closed, but `OSError` is not normalized to `SnapshotCorruptError`. |
| Existing relevant tests | Targeted test coverage remains green | `pytest -q tests/test_store.py tests/test_pra_log.py`: `36 passed in 2.14s` | Pass, Grade C | Existing tests encode some permissive WAF-loader behavior and do not eliminate the fixture findings. |

## Aggregate-only chain evidence

| Ledger | Verifier result | Aggregate evidence | What this establishes | What it does not establish |
|---|---|---|---|---|
| WAF | Exit `0`, intact across `137,023` parsed records | Terminal timestamp range: `2026-05-30T23:07:48Z` to `2026-09-18T15:38:36Z` | The frozen, parseable sequence linked correctly at review time | Completeness, source authenticity before the frozen commit, current WAF conditions, or production health |
| PRA | Exit `0`, intact across `352` parsed records | Status counts: `192` sent, `112` dry-run, `48` failed. Terminal timestamp range: `2026-05-26T02:39:01Z` to `2026-06-16T14:47:42Z` | The frozen, parseable sequence linked correctly at review time | Current SMTP, actual receipt/delivery, recipient state, or current configuration |

## Controlled corruption and takedown fixture matrix

All fixtures used synthetic numeric identifiers and non-routable synthetic contact values. They were created under a system temporary directory outside the worktree. No tracked path was written.

| Fixture | Method | Exit or exception | Preservation / detection result | Technical verdict |
|---|---|---|---|---|
| WAF intact chain | Two append-generated synthetic records | CLI exit `0` | Intact chain recognized | Pass |
| WAF linked-record alteration | Altered predecessor in a two-record chain | CLI exit `1` | One broken link detected | Pass |
| PRA intact chain | Two append-generated synthetic records | CLI exit `0` | Intact chain recognized | Pass |
| PRA linked-record alteration | Altered predecessor in a two-record chain | CLI exit `1` | One broken link detected | Pass |
| WAF malformed JSON | Invalid JSON fixture | CLI exit `0` | Reported "no records" rather than corruption | **Fail** |
| PRA malformed JSON | Invalid JSON fixture | CLI exit `1` | `JSONDecodeError` surfaced | Partial |
| Missing `takedowns.json` | No file in synthetic output directory | No exception | Synthetic output written normally | Pass |
| Malformed `takedowns.json` | Invalid JSON | `SnapshotCorruptError` | Last-good synthetic output hash unchanged | Pass |
| Scalar `takedowns.json` | JSON scalar | `SnapshotCorruptError` | Last-good synthetic output hash unchanged | Pass |
| Direct-key object | JSON mapping whose key equals a synthetic ID | No exception | Mapping key was treated as a sealed ID | Partial |
| Wrapped-object mapping | JSON mapping whose value contains a synthetic ID | No exception | Contained synthetic ID remained in output | **Fail** |
| Unreadable path | Directory at `takedowns.json` path | `PermissionError` | Last-good synthetic output hash unchanged | Partial |

## Material findings

### A4-F1: WAF chain CLI converts malformed input into a successful empty-log result

**Severity:** Medium. **Confidence:** High for the isolated component behavior. **Evidence grade:** D. **Claim-source status:** `verified` for the executed behavior; this is not a live-production corruption finding.

`scraper/store.py:74-84` returns an empty list when WAF log JSON is malformed or unreadable. `scraper/verify_block_log.py:21-30` maps an empty list to exit `0` and “nothing to verify.” The controlled malformed fixture reproduced that exact path: exit `0`, not an integrity failure. Link-tamper detection works when the JSON remains parseable, but the CLI’s success result establishes only that all **parsed** records link correctly. It cannot establish that its input was readable or complete.

**Smallest safe next test:** AQ should independently run the malformed-file case against the frozen baseline and determine whether the intended verifier contract requires distinct `missing`, `empty`, and `corrupt` outcomes. No repair was made.

### A4-F2: Takedown schema is internally inconsistent and can silently retain a wrapped synthetic ID

**Severity:** Medium. **Confidence:** High for the isolated component behavior. **Evidence grade:** D. **Claim-source status:** `conflicting`.

`scraper/store.py:216-235` documents a JSON array of inmate-number strings but constructs a set by iterating any JSON value. Scalar input causes a typed failure, while an object is accepted as its keys. `scraper/sweep.py:529-540` separately permits both lists and mappings during the prefilter step, so the source has no single enforced shape contract. A controlled wrapped-object fixture was accepted without exception and the ID held inside its value remained in the output. That is inconsistent with an array-only fail-closed contract and could matter if an operator supplies an object-wrapped list rather than a direct key mapping.

**Smallest safe next test:** AQ should independently reproduce both direct-key and wrapped-object cases, then A0 should obtain an owner decision on whether mappings are supported input. Only after that decision should any schema or documentation remediation be considered.

### A4-O1: Unreadable takedown paths preserve output but do not produce the same typed boundary error

**Severity:** Low. **Confidence:** High. **Evidence grade:** D. **Claim-source status:** `verified` for preservation; exception-normalization intent is `manual review needed`.

The unreadable-path fixture raised `PermissionError` before the write and preserved the last-good synthetic output. This is a safe preservation outcome. `scraper/store.py:227-235` catches parsing and type errors but not `OSError`, so callers receive a different exception category from malformed JSON. The direct synthetic result does not establish a production filesystem condition.

## Commands and failure classification

| Action | Exit | Material result | Classification |
|---|---:|---|---|
| `python -m pip install -e '.[dev]'` in ignored worktree `.venv` | `0` | Declared runtime and development dependencies installed locally | Environment setup succeeded |
| `python -m scraper.verify_block_log` | `0` | Frozen WAF chain intact across `137,023` parsed records | Pass within isolated frozen input |
| `python -m scraper.verify_pra_log` | `0` | Frozen PRA chain intact across `352` parsed records | Pass within isolated frozen input |
| `python -m pytest -q tests/test_store.py tests/test_pra_log.py` | `0` | `36 passed in 2.14s` | Pass |
| First aggregate-only one-line Python command | `1` | Syntax error before useful aggregation output | Test-harness error. No result accepted. |
| Changed aggregate-only script | `0` | Aggregate counts and terminal timestamps collected without record-level output | Pass under a verified anti-churn receipt |
| First synthetic fixture driver | `1` | Synthetic model values failed model validation before fixture execution | Test-harness error. No source or source-data write occurred. |
| Fresh-root corrected fixture driver | `0` | Takedown and chain fixture outcomes recorded above | Pass; changed fixture run recorded under verified anti-churn control |
| Synthetic malformed WAF verifier input | `0` | Corruption treated as empty log | Implementation contract failure |
| Synthetic malformed PRA verifier input | `1` | JSON decode failure surfaced | Partial error handling behavior |

## Source locators and interpretation boundary

- `scraper/verify_block_log.py:1-30` defines the WAF verifier’s empty-log and broken-chain behavior.
- `scraper/verify_pra_log.py:1-30` defines the PRA verifier’s loaded-chain behavior.
- `scraper/store.py:74-157` loads, appends, and verifies the WAF chain.
- `scraper/pra_log.py:47-87` loads, appends, and verifies the PRA chain.
- `scraper/store.py:216-251` loads takedowns and persists `current.json` after the takedown read succeeds.
- `scraper/sweep.py:529-540` independently reads takedowns before the persistence boundary.
- `tests/test_store.py:173-199, 323-364` and `tests/test_pra_log.py:1-112` supply the targeted existing test coverage exercised in this pass.

Source inspection supports implementation existence. The executable results above support only the frozen worktree and controlled fixtures. They do **not** prove current live resilience, WAF effectiveness, actual mail delivery, secret configuration, or the accuracy of the public roster.

## Post-run integrity and deliberately unperformed actions

- `git status --short`, `git diff --check`, and `git diff --name-only` in the A4 worktree produced no output after all commands.
- `.venv/` and `.pytest_cache/` are ignored by the frozen repository’s `.gitignore`; synthetic fixtures remained outside tracked source paths.
- No source, test, workflow, configuration, tracked data, DNS, Pages state, Actions state, secret, mail, public record, or live website was changed.
- No private gate was attempted. Current owner-state and live-resilience questions remain unknown.

## Compact execution trail

| UTC result | Step | Result |
|---|---|---|
| `2026-09-19T20:06:12Z` | A4 governance and work-card load | Pass |
| `2026-09-19T20:06:21Z` | Isolated dependency environment | Pass |
| `2026-09-19T20:06:36Z` | Frozen WAF and PRA chain CLI checks | Pass |
| `2026-09-19T20:06:43Z` | Targeted store and PRA test suite | Pass |
| `2026-09-19T20:06:50Z` | Initial aggregate command | Fail, syntax-only; preserved |
| `2026-09-19T20:06:55Z` | Changed aggregate command under retry control | Pass |
| `2026-09-19T20:07:03Z` | Synthetic takedown and link-tamper fixtures | Pass |
| `2026-09-19T20:07:47Z` | Malformed chain-verifier fixtures | Fail, documented above |

## A0 intake recommendation

Accept the intact-chain and link-tamper results as **isolated evidence**. Return the two source-contract findings, A4-F1 and A4-F2, for independent AQ replication before treating either as an audit-packet decision. The remaining human boundary is limited to an owner decision on whether mapping-shaped takedown input is intentionally supported; no private-system access is required to replicate the component behavior.
