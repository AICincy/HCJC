# JCStream audit - synthesized index

## Run metadata
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Date: 2026-05-14
- Subagents completed: 10/10
- Subagents failed: none
- Pytest baseline: GREEN, 102 passed (see `_pytest_baseline.txt`)
- Total findings: 74 (11 high, 25 medium, 36 low, 2 informational)
- Formatting: zero em/en dashes in any artifact (orchestrator scrubbed two stray hyphenations in sec-net and gov before publication)

## Severity rollup

Sorted by severity, then by confidence, then by ID. A low-confidence finding sits below a higher-confidence finding of the same severity per orchestrator guidance.

| ID | Sev | Conf | One-line summary | Owner skill |
|----|-----|------|------------------|-------------|
| parser-F1 | high | high | `_parse_name` triple-conjunction (heading tag + comma + all-caps) is single-property-fragile; one drift zeroes detail names | parser-robustness |
| parser-F2 | high | high | Charge labels are literal strings; a single-column rename (e.g. `Bond Amount`) silently empties that field with no warning | parser-robustness |
| parser-F3 | high | high | Inline photo extractor pinned to `274px` style hook; any HCSO width tweak loses photos site-wide | parser-robustness |
| data-F1 | high | high | `Snapshot` has no `schema_version`; corrupt-load returns `{}` and the bootstrap floor then accepts any small sweep as canonical | data-integrity |
| sweep-F1 | high | high | Corrupted `current.json` silently re-enters bootstrap mode; composes with `load_current` swallow to canonicalize a degraded roster | sweep-reliability |
| sweep-F2 | high | high | `KeyboardInterrupt` mid-sweep diffs partial `current` against full `previous`, synthesizing a wave of bogus `released` events into the 500-event changelog | sweep-reliability |
| tests-F1 | high | high | `_check_detail_watchdog` has no test; muting the WARNING would be invisible to CI | test-gap-analysis |
| tests-F2 | high | high | `_fetch_one` name fallback and photo carry-forward are untested; the bridge between minor drift and blank-card site has no asserted behavior | test-gap-analysis |
| a11y-F1 | high | high | Lightbox dialog does not trap Tab focus and does not `inert` the background; SR users read background while overlay is active (WCAG 2.4.3, 2.1.2) | html-accessibility |
| a11y-F2 | high | high | Combobox pattern is incomplete (no `aria-activedescendant`, no arrow keys, non-option child inside `role="listbox"`) (WCAG 4.1.2, 2.1.1) | html-accessibility |
| gov-F1 | high | high | JSON-LD `license` attributes the JCStream page to ORC 149.43 instead of CC BY-NC 4.0; self-contradicts the human-readable footer | content-governance |
| tpl-sec-F1 | med | high | JSON-LD block interpolates `inmate.full_name`, `inmate_number`, `booking_number`, `booking_date`, `sex` with HTML-only escaping; should be `tojson` | template-security |
| parser-F4 | med | high | `_DETAIL_ID = r"[?&]id=(\d+)"` assumes query-string IDs; a permalink shift to `/inmate-detail/N/` zeroes the list | parser-robustness |
| data-F2 | med | high | `inmate_count == len(inmates)` and unique `inmate_number` enforced only at write time; no model-level invariants | data-integrity |
| data-F3 | med | high | `_materially_changed` compares `charges` order-sensitively; HCSO charge reorder floods changelog with spurious `updated` events | data-integrity |
| data-F4 | med | high | Empty-string `inmate_number` is permitted by the model; one bucket can swallow multiple records | data-integrity |
| sweep-F3 | med | high | Checkpoint write every 50 details is not gated by the roster-fraction guard; mid-cycle crash can persist a sub-threshold roster | sweep-reliability |
| sweep-F4 | med | high | Detail watchdog warns but never flips `roster_ok`; an HCSO detail-page redesign mid-cycle gets canonicalized | sweep-reliability |
| tests-F3 | med | high | `_split_name` and `_parse_name` heading-shape edge cases (`SMITH`, `SMITH, `, mixed case) are unpinned | test-gap-analysis |
| tests-F4 | med | high | Strict-inequality boundaries of `_sweep_looks_healthy` and `_prune_photos` (exact 0.10, exact 0.5, exact 50) are not tested | test-gap-analysis |
| tests-F6 | med | high | PRA header-injection defense relies on `EmailMessage` validation but is never asserted; a refactor away from EmailMessage silently regresses | test-gap-analysis |
| a11y-F3 | med | high | Tier badge has `tabindex="0"` and `aria-label` but is not a button and lacks `aria-describedby="tier-tip"`; tooltip body never reaches AT | html-accessibility |
| a11y-F4 | med | high | `<time>` elements emit no `datetime` attribute (WCAG 1.3.1) | html-accessibility |
| a11y-F5 | med | high | `#filter-empty` toggles `hidden` but has no `role="status"`; SR users do not hear "no one matches" (WCAG 4.1.3) | html-accessibility |
| arch-F1 | med | high | `web/build.py` is 1282 lines covering Jinja env, ORC classification tables, snapshot reshaping, and seven output emitters | architecture |
| arch-F2 | med | high | `scraper/sweep.py` fuses orchestration with three health guards plus their constants; tests already reach a private `_sweep_looks_healthy` | architecture |
| arch-F3 | med | high | Three PRA modules duplicate ~70 lines of identical SMTP envelope; the security-load-bearing path lives in three copies | architecture |
| gov-F2 | med | high | JSON-LD `dateCreated` is unguarded; renders as `""` when parser does not populate `booking_date`, producing invalid Schema.org | content-governance |
| gov-F3 | med | high | Presumption-of-innocence phrasing drifts across four templates; no canonical sentence appears verbatim everywhere | content-governance |
| gov-F4 | med | high | CC BY-NC 4.0 claim is asserted on inmate pages and README but missing from base.html footer and data.html non-affiliation section | content-governance |
| css-F1 | med | high | `--fg-dim` text on `--surface` and `--surface-hi` fails WCAG AA (4.20, 3.80); affects `.id-chip` and `.recent-activity time` | css-a11y-performance |
| css-F2 | med | high | `.tag-booked` in `.recent-activity` context composites to 3.76 contrast (fails AA); tint alpha tuned against `--bg` only | css-a11y-performance |
| css-F3 | med | high | `.banner` and `.banner strong` declared twice; later block silently overrides `display: flex` to `block` and `<strong>` color to neutral | css-a11y-performance |
| tests-F5 | med | med | Fixture HTML carries real-seeming HCSO names (KHAN HAMMAD ALI, SMITH MICOLE, SMITH JEFFREY); git history pins past HCSO removal lifecycle | test-gap-analysis |
| parser-F5 | med | med | `_BIO_LINE` regex rejects punctuation/digits in label names; an HCSO label like `Class #` is silently dropped | parser-robustness |
| sweep-F5 | med | med | `_prune_photos` runs in `finally` even when `save_current` raised; only the 0.5 catastrophic guard catches deletes | sweep-reliability |
| tpl-sec-F2 | low | high | `esc()` and `escTip()` do not escape single quotes; safe today only because all attribute literals are double-quoted | template-security |
| tpl-sec-F3 | low | high | `inmate_number` from `bio.get("Inmate Number")` is unconstrained text and flows into `photo_filename` and URL attributes | template-security |
| parser-F6 | low | med | `_parse_charges` is globally scoped (`tree.css("tr")`); a future labeled table on the detail page could yield false positives | parser-robustness |
| parser-F7 | low | high | `_extract_inline_photo` conflates "no candidate img" with "decode failed"; logs are aggregate-only | parser-robustness |
| parser-F8 | low | med | Detail page with zero structured fields produces empty `Inmate` without per-record INFO breadcrumb | parser-robustness |
| data-F5 | low | high | `generated_utc` accepted in any format on load; non-Z timestamps would break downstream sort/compare | data-integrity |
| data-F6 | low | high | Changelog is not sorted on save; ordering is currently correct only because saves are serial and the cron clock is monotonic | data-integrity |
| data-F7 | low | med | `data/history.json` is the only retained-over-time artifact and has no Pydantic model; wrong-shape load crashes `_compute_stats` | data-integrity |
| data-F8 | low | high | Photo prune ordering (snapshot before prune) is pinned only by convention; a finally-block reorder would publish dangling photo refs | data-integrity |
| sweep-F6 | low | high | No orchestrator wall-clock budget; runner kills the job mid-checkpoint at 50 minutes rather than producing a clean partial write | sweep-reliability |
| sweep-F7 | low | high | BOM in `data/surnames.txt` produces a silently empty letter; below the 10% threshold so no guard fires | sweep-reliability |
| sweep-F8 | low | high | `pool.map` exception-isolation contract on `_fetch_one` is undocumented; a future re-raise would truncate the sweep silently | sweep-reliability |
| sec-net-F1 | low | high | Module docstring and `DEFAULT_UA` advertise robots.txt and `Crawl-delay: 10` compliance; default crawl delay is 0 and cron does not override | security-networking |
| sec-net-F2 | low | high | Cincinnati Socrata clients fall back to bare `JCStream/0.1` UA when env is unset; contact URL lost | security-networking |
| sec-net-F3 | low | med | HCSO client retries only on `>= 500`; 429 is treated as a hard failure and rolls into `n_failed` | security-networking |
| sec-net-F4 | low | high | `incidents`/`shootings` catch broad `Exception` then fall back to unfiltered query (up to 5000 / 1000 rows) | security-networking |
| sec-net-F5 | low | med | `verify=False` rationale documented at the call site, not the class; future env-driven base-url repoint would silently inherit it | security-networking |
| sec-net-F6 | low | high | Sweep workflow UA drifts from `client.py` `DEFAULT_UA`; two sources of truth for the UA string | security-networking |
| arch-F4 | low | high | `scraper/store.py` mixes pure diff (`diff`, `_materially_changed`) with filesystem I/O | architecture |
| arch-F5 | low | high | `scraper/cfs.py` inlines its own httpx call instead of going through `cincy_open.query` (the other three feeds do) | architecture |
| arch-F6 | low | high | `tests/test_sweep.py` imports private `_sweep_looks_healthy`; signals the guard wants a public name | architecture |
| arch-F7 | low | med | Hardcoded data paths in `sweep.run()` block local re-runs and orchestrator tests | architecture |
| tests-F7 | low | high | `_materially_changed` charge-order semantics are undocumented; no test pins behavior either way | test-gap-analysis |
| tests-F8 | low | high | `make_client` env-var override (`JCSTREAM_BASE_URL`, `JCSTREAM_USER_AGENT`, `JCSTREAM_CRAWL_DELAY`) is untested | test-gap-analysis |
| a11y-F6 | low | med | `.statbar` rows are three sibling spans with no list semantics; SR users hear disconnected fragments per row (WCAG 1.3.1) | html-accessibility |
| a11y-F7 | low | med | Recent-activity card has duplicate thumb and name anchors with no grouping; SR users hear duplicate link list | html-accessibility |
| a11y-F8 | low | low | Dispatch-map JS-off fallback is a raw `dispatches.json` link; not human-readable (WCAG 1.1.1) | html-accessibility |
| gov-F5 | low | high | "There is never a fee" promise drifts to weaker forms on detail pages ("at no cost", "no fee") | content-governance |
| gov-F6 | low | high | `stats.html` lacks ORC 149.43 cite and removal-protocol link | content-governance |
| gov-F7 | low | high | Removal-link visible label drifts (href is consistent); cosmetic | content-governance |
| gov-F8 | low | med | ORC 2953.32 "as amended" hedge names the amending acts on data.html but is plainer on index.html and inmate.html | content-governance |
| css-F4 | low | high | Invalid `details.month, details.coms { open: true }` rule in print block; `open` is not a CSS property | css-a11y-performance |
| css-F5 | low | high | `#c98a8a` and `#9ab4d3` tier hex values are duplicated between `.sr-tier` and `.tier-*` (4 copies of 2 colors) | css-a11y-performance |
| css-F6 | low | high | `.kpi`, `.kpis`, `.num`, `.label` referenced in `stats.html` but absent from `style.css`; KPI cards have no visual treatment | css-a11y-performance |
| css-F7 | low | med | `--family` and `--danger-deep` declared in `:root` but unused; dead variables | css-a11y-performance |
| css-F8 | low | med | `.back-to-top` resting `opacity: 0.55` puts the glyph at 3.86 contrast; UI-component floor (3:1) is met but touch users never trigger hover | css-a11y-performance |
| tpl-sec-F4 | info | high | Giscus widget origin not pinned by an in-template comment; today safe (env-supplied), no defense-in-depth doc | template-security |
| tpl-sec-F5 | info | med | RSS `<guid>` is not hash-stable per record; cosmetic, not a security gap | template-security |

## Cross-cutting patterns

### Pattern 1: heuristic parsing without model validators and with WARN-only watchdogs
- Reports touching it: parser-F1, parser-F2, parser-F3, parser-F8, sweep-F4, tests-F1, tests-F2, tests-F3, data-F4, tpl-sec-F3, gov-F2
- Root cause hypothesis: the parser was tuned against current HCSO HTML using string-and-style fingerprints (`274px`, comma + all-caps heading, literal labels). Defenses are limited to two aggregate watchdogs (`DETAIL_WATCHDOG_NAME_FLOOR`, `DETAIL_WATCHDOG_PHOTO_FLOOR`) that only log; nothing flips `roster_ok` and nothing rejects empty fields at the model layer.
- Recommended owner: parser-robustness for the parser-side tiers; sweep-reliability for promoting the watchdog to a write-blocker; data-integrity for the model validators that close the bypass path.

### Pattern 2: load is forgiving, write is strict; degraded load can promote bad state
- Reports touching it: data-F1, data-F2, data-F5, data-F6, data-F8, sweep-F1, sweep-F2, sweep-F5
- Root cause hypothesis: `load_current` swallows `JSONDecodeError, ValidationError, KeyError, TypeError, AttributeError` and returns `{}`. The sweep guard bootstraps from `{}` unconditionally. The two behaviors are each defensible alone; together they let a corrupted snapshot canonicalize any non-trivial sweep, evict 500 real changelog events, and prune photos against a never-persisted `seen_ids` set.
- Recommended owner: data-integrity for the schema-version + sentinel-on-corrupt-load fix; sweep-reliability for the `_clean_finish` gate on changelog append and the `save_ok` gate on prune.

### Pattern 3: ARIA semantics declared but not honored by JS
- Reports touching it: a11y-F1, a11y-F2, a11y-F3, a11y-F5
- Root cause hypothesis: the templates announce a contract (`role="dialog" aria-modal`, `role="combobox" aria-controls`, `role="tooltip"`, `hidden`-toggled empty state) that the inline JS in `base.html` only partially implements. The lightbox has Escape close but no focus trap; the combobox has Escape only, no arrow keys, no `aria-activedescendant`; the tooltip has no `aria-describedby` from its trigger; the filter empty-state has no `role="status"`. The pattern is "ARIA was sprinkled, JS was not finished."
- Recommended owner: html-accessibility for the markup + JS, with html-template-security cross-checking once the combobox is demoted (changes the JSON-LD-adjacent code paths).

### Pattern 4: concentration of concerns in a few large modules
- Reports touching it: arch-F1, arch-F2, arch-F3, arch-F4, sweep-F2 (the entangled try/finally that fuses snapshot, diff, changelog, prune)
- Root cause hypothesis: the project grew naturally and three modules absorbed everything in their vicinity. `web/build.py` (1282 lines) merges Jinja env wiring, ORC classification, snapshot reshaping, and seven output emitters. `scraper/sweep.py` (355 lines) fuses orchestration with three health guards. Three PRA modules duplicate the SMTP envelope. None of these are coupling bugs; the dependency direction (`web -> scraper`, never the reverse) is clean. They are cohesion problems.
- Recommended owner: architecture for the splits; sweep-reliability for the try/finally rework that pairs with arch-F2.

### Pattern 5: wording and representation drift across surfaces that should say the same thing
- Reports touching it: gov-F3, gov-F4, gov-F5, gov-F7, gov-F8, sec-net-F1, sec-net-F6, css-F3, css-F5
- Root cause hypothesis: the same content surfaces in multiple files (presumption of innocence in four templates, no-fee promise in three, UA string in `client.py` and `sweep.yml`, tier hexes in `.sr-tier` and `.tier-*`, banner styling block declared twice). Each surface looks right in isolation; together they drift. The fix is single-source-of-truth, applied surface-by-surface.
- Recommended owner: content-governance for the legal-text canonicalization; security-networking for the UA reconciliation; css-a11y-performance for the duplicated `.banner` and tier hexes.

### Pattern 6: JSON-LD on inmate pages is the single highest-leverage shared touchpoint
- Reports touching it: tpl-sec-F1, gov-F1, gov-F2, data-F4, tpl-sec-F3 (`inmate_number` validator)
- Root cause hypothesis: the JSON-LD block in `inmate.html:18-29` is a structured-data emission that crawlers index regardless of the `noindex` posture. It currently has three independent issues filed against it from three different subagents: HTML-only escaping in JSON string literals (template-security), the `license` predicate misattributing the page to the source authority (governance), and `dateCreated:""` on missing parser data (governance, with a parser-robustness cross-ref). Closing all three is one template patch.
- Recommended owner: template-security drives the patch; content-governance reviews the wording; parser-robustness fixes `booking_date` null safety upstream.

## Conflicts

One mild conflict on the direction of `_materially_changed` charge ordering.

- Finding A (data-F3) recommends changing `_materially_changed` to compare charges order-insensitively (canonical sort or set), preventing spurious `updated` events when HCSO reshuffles the same content.
- Finding B (tests-F7) frames the same property as "document or fix" and shows a test that *asserts* order-sensitivity as the current contract, hedging that order might intentionally signal lead-charge ranking.
- Why they conflict: data-F3 picks "fix" and tests-F7 leans "document". They are not contradictory in code (only one will ship) but they propose opposite tests.
- Recommended resolution: ship data-F3 (canonical-sort comparison). The "lead-charge ranking" hypothesis behind tests-F7 is speculative; today the parser preserves document order with no ranking semantics, and the cost of spurious `updated` events on a HCSO reorder is concrete (changelog flood, RSS feed churn). Replace the tests-F7 assertion with the order-INSENSITIVE test described in data-F3 (`tests/test_store.py::test_diff_ignores_charge_reorder_with_same_content`).

No other contradictions detected. Several findings overlap in scope (Pattern 6 above is the densest example), but every overlap is complementary, not contradictory.

## Unified remediation sequence

Grouped by phase, ordered within each phase by leverage (highest first). Every step is independently green-able against the 102-test pytest baseline.

### Phase 1 - critical

These are the "would-impact-the-published-roster-or-pages" items.

- Step 1: Patch the inmate.html JSON-LD block (escaping + license + dateCreated guard)
  - Source findings: tpl-sec-F1, gov-F1, gov-F2
  - Touches: web/templates/inmate.html (single block, ~15 lines)
  - Why this position: one template patch closes three findings from three subagents; zero migration; visible improvement in machine-readable metadata.
  - Verification: `python -m web.build` and run a rendered detail page through https://validator.schema.org/ for a synthetic name containing a quote; `python -m pytest -q` stays green.
  - Estimated effort: S
  - Phase: 1

- Step 2: Lightbox focus trap (inert + Tab cycler fallback)
  - Source findings: a11y-F1
  - Touches: web/templates/base.html (openLB/closeLB plus a Tab keydown handler)
  - Why this position: highest-impact keyboard/AT defect; surgical JS change with documented fallback for browsers without `inert`.
  - Verification: manual keyboard test (Tab from close button must cycle inside `#lb`); axe-core or built-in browser accessibility tree; pytest unaffected.
  - Estimated effort: S
  - Phase: 1

- Step 3: Parser drift defenses (tiered `_parse_name`, JPEG-SOI photo fallback, per-label coverage telemetry)
  - Source findings: parser-F1, parser-F2, parser-F3
  - Touches: scraper/parsers.py, scraper/sweep.py (label-aggregation hook), tests/fixtures/ (two new fixtures)
  - Why this position: three "stop the bleed when HCSO drifts" defenses; tier-1 keeps current behavior unchanged so it lands without churn.
  - Verification: existing pytest stays green (current fixtures hit tier 1); two new tests assert the tier-2/tier-3 and the JPEG-SOI fallback paths fire on synthetic drift fixtures.
  - Estimated effort: M
  - Phase: 1

- Step 4: Snapshot schema versioning and corrupt-load sentinel
  - Source findings: data-F1, sweep-F1
  - Touches: scraper/models.py, scraper/store.py, scraper/sweep.py (sentinel handling)
  - Why this position: closes the "corrupted current.json silently bootstraps to a degraded sweep" composition; pure-additive (existing files default to `schema_version=1`).
  - Verification: load existing `data/current.json` and assert version=1; synthesize a v99 file and assert the sweep refuses to bootstrap; assert `JSONDecodeError` returns a sentinel (not `{}`) and the sweep rejects the cycle; full pytest green.
  - Estimated effort: M
  - Phase: 1

- Step 5: Changelog clean-finish gate (no synthetic `released` wave on interrupt)
  - Source findings: sweep-F2
  - Touches: scraper/sweep.py (try/finally with `_clean_finish` flag)
  - Why this position: highest-impact data-integrity bug; an interrupted sweep can evict 500 real events from the rolling changelog. The fix is local to one function.
  - Verification: new test that interrupts mid-loop and asserts the changelog appends zero `released` events; full pytest green.
  - Estimated effort: S
  - Phase: 1

- Step 6: Watchdog + fetch_one test coverage
  - Source findings: tests-F1, tests-F2
  - Touches: tests/test_sweep.py (or new tests/test_fetch_one.py)
  - Why this position: these tests lock in the WARNING contracts that Steps 3-5 rely on. Without them, a refactor could mute the watchdog or change the fallback shape silently.
  - Verification: three watchdog `caplog` assertions plus two `_fetch_one` fallback assertions; full pytest green.
  - Estimated effort: S
  - Phase: 1

### Phase 2 - stability

These tighten the seams around Phase 1 fixes.

- Step 7: Pydantic model invariants (count, uniqueness, empty-id, timestamp shape)
  - Source findings: data-F2, data-F4, data-F5
  - Touches: scraper/models.py, tests/test_models.py
  - Verification: three new model-validator tests; existing 102 pass.
  - Estimated effort: S
  - Phase: 2

- Step 8: Order-insensitive charges compare + stable changelog sort
  - Source findings: data-F3, data-F6, tests-F7 (replaces its assertion with the order-insensitive one)
  - Touches: scraper/store.py, tests/test_store.py
  - Verification: new test that same-content reordered charges produce no `updated`; new test that out-of-order events save sorted.
  - Estimated effort: S
  - Phase: 2

- Step 9: Combobox demotion + tooltip describedby + datetime + filter-empty status
  - Source findings: a11y-F2, a11y-F3, a11y-F4, a11y-F5
  - Touches: web/templates/base.html, web/templates/index.html, web/templates/_card.html, web/templates/inmate.html, web/build.py (datetime emission helper)
  - Verification: rendered HTML diff; manual screen-reader pass; pytest green.
  - Estimated effort: M
  - Phase: 2

- Step 10: Sweep guard hardening (checkpoint fraction, watchdog block, prune-after-save)
  - Source findings: sweep-F3, sweep-F4, sweep-F5
  - Touches: scraper/sweep.py (three small guards; new constants only, no threshold changes to existing 0.10 / 0.50 / 50)
  - Verification: three new sweep tests; full pytest green.
  - Estimated effort: M
  - Phase: 2

- Step 11: Networking defenses (429 retry, narrow except, UA reconciliation)
  - Source findings: sec-net-F1, sec-net-F2, sec-net-F3, sec-net-F4, sec-net-F6
  - Touches: scraper/client.py, scraper/cincy_open.py, scraper/cfs.py, scraper/incidents.py, scraper/shootings.py, .github/workflows/sweep.yml
  - Verification: new client unit test for 429 retry with capped `Retry-After`; existing tests green.
  - Estimated effort: M
  - Phase: 2

- Step 12: Template-security tightening (single-quote escape; `inmate_number` validator)
  - Source findings: tpl-sec-F2, tpl-sec-F3
  - Touches: web/templates/base.html (esc/escTip), scraper/models.py, tests/test_models.py
  - Verification: existing tests green; one new model test asserts `inmate_number=".."` raises.
  - Estimated effort: S
  - Phase: 2

- Step 13: CSS contrast bumps and duplicate-banner cleanup
  - Source findings: css-F1, css-F2, css-F3, css-F8
  - Touches: web/static/style.css (new `--fg-dim-raised` var, tag-alpha nudges, banner consolidation, back-to-top resting opacity)
  - Verification: rebuild; visual diff confirms only the four targeted spots change; contrast-pass spreadsheet rerun.
  - Estimated effort: S
  - Phase: 2

- Step 14: Fixture scrub and PRA header-injection test
  - Source findings: tests-F5, tests-F6, parser-F5
  - Touches: tests/fixtures/detail_inmate.html, tests/fixtures/list_smith.html, tests/test_parsers.py (expected-name updates), tests/test_pra.py (CRLF rejection test), scraper/parsers.py (`_BIO_LINE` relax)
  - Verification: pytest green; new `tests/fixtures/README.md` documents the no-real-names rule.
  - Estimated effort: S
  - Phase: 2

- Step 15: Architecture splits that have test hooks (sweep_guards, pra_base, cfs->cincy_open)
  - Source findings: arch-F2, arch-F3, arch-F5, arch-F6
  - Touches: new scraper/sweep_guards.py, new scraper/pra_base.py, scraper/cfs.py rewrite, tests/test_sweep.py import line
  - Verification: pytest stays at exactly the same count and passes; manual `python -m scraper.pra --dry-run` smoke for each of three PRA callers.
  - Estimated effort: M
  - Phase: 2

### Phase 3 - quality and governance

These are polish, governance, and lower-leverage cleanup.

- Step 16: Governance wording canonicalization (presumption, no-fee, CC BY-NC alignment, removal label)
  - Source findings: gov-F3, gov-F4, gov-F5, gov-F6, gov-F7, gov-F8
  - Touches: web/templates/index.html, inmate.html, stats.html, data.html, base.html
  - Verification: rebuild; rendered diff confirms canonical sentences appear verbatim across all required surfaces.
  - Estimated effort: S
  - Phase: 3

- Step 17: web/build.py split into build + classify + shape
  - Source findings: arch-F1
  - Touches: web/build.py, new web/classify.py, new web/shape.py
  - Verification: rebuild and `diff -r docs/ docs.backup/` shows zero byte changes; pytest green.
  - Estimated effort: M
  - Phase: 3

- Step 18: Lower-priority parser breadcrumbs and scope hardening
  - Source findings: parser-F4, parser-F6, parser-F7, parser-F8
  - Touches: scraper/parsers.py (regex alternative for path-form id, scoped charge parse, two new log lines)
  - Verification: existing tests green; one new test for the path-form id regex alternative.
  - Estimated effort: S
  - Phase: 3

- Step 19: Lower-priority sweep breadcrumbs (wall-clock cap, BOM strip, pool.map comment)
  - Source findings: sweep-F6, sweep-F7, sweep-F8
  - Touches: scraper/sweep.py
  - Verification: BOM-strip test reads a synthetic file with a leading `﻿` and asserts `A` not `﻿A`; full pytest green.
  - Estimated effort: S
  - Phase: 3

- Step 20: a11y polish, css polish, history.json model, remaining tests
  - Source findings: a11y-F6, a11y-F7, a11y-F8, css-F4, css-F5, css-F6, css-F7, data-F7, data-F8, tests-F4, tests-F8
  - Touches: scattered single-file edits across templates, css, scraper/models.py, tests/
  - Verification: pytest green; rendered diff is minimal.
  - Estimated effort: M
  - Phase: 3

## Quick wins

Five additive, no-migration, high-confidence changes.

1. css-F4: delete the invalid `details.month, details.coms { open: true; }` rule in `web/static/style.css:993`. One-line removal; the next line already provides the actual print-expansion behavior.
2. sweep-F7: prepend `text.lstrip("﻿")` once in `_read_surnames` (`scraper/sweep.py:317-322`). One-line addition; zero behavioral change for non-BOM files.
3. parser-F4: extend `_DETAIL_ID` to `r"(?:[?&]id=|/inmate-detail/)(\d+)"` (`scraper/parsers.py:17`). One regex literal; future-proofs a permalink shift that would otherwise zero the list and need a fix-and-deploy cycle.
4. a11y-F5: add `role="status"` to `#filter-empty` in `web/templates/index.html:127`. One attribute; SR users hear the empty-state announcement.
5. a11y-F4: emit `<time datetime="{{ value }}">{{ value }}</time>` at every `<time>` site (index.html:66, inmate.html:167, 178). Pure addition, unlocks WCAG 1.3.1.

## Deferred / out of scope

Each item links to its source finding and a reason.

- arch-F4 (`store.py` diff move): pure cleanup with no test hook beyond what arch-F2 already gives; defer until a separate reason to touch `store.py` appears.
- arch-F7 (`SweepPaths` dataclass): testability win, not a correctness gap; defer until adding orchestrator tests that need a tmp dir.
- tpl-sec-F4 (Giscus provenance comment): safe today; pure documentation; bundle with Step 16 if convenient.
- tpl-sec-F5 (RSS GUID stabilization): cosmetic; out of security scope; defer.
- a11y-F8 (dispatch-map text fallback): low-confidence, design trade-off against progressive-enhancement posture; needs owner input.
- gov-F8 (ORC 2953.32 currency vs amending acts): "as amended" hedge is present everywhere; the strongest form on data.html is good enough. ORC citation currency against current Ohio law marked **unverified - live source out of scope**.
- sec-net-F5 (class-level `verify=False` docstring): one-line documentation; bundle opportunistically.
- css-F7 (unused `--family` / `--danger-deep`): bundle into Step 20; requires a final grep against `docs/` before deletion.

## Appendix - subagent reports

- [sec-net](./01_security_networking.md) - 6 findings
- [parser](./02_parser_robustness.md) - 8 findings
- [data](./03_data_integrity.md) - 8 findings
- [tpl-sec](./04_template_security.md) - 5 findings
- [sweep](./05_sweep_reliability.md) - 8 findings
- [tests](./06_test_gap.md) - 8 findings
- [a11y](./07_html_accessibility.md) - 8 findings
- [arch](./08_python_architecture.md) - 7 findings
- [gov](./09_content_governance.md) - 8 findings
- [css](./10_css_a11y_performance.md) - 8 findings

End of index.
