# JCStream skills audit — pass 2 (post-fix)

**Run date**: 2026-05-14
**Pass 1 → Pass 2 verdict matrix**:

| # | Skill | Pass 1 | Pass 2 | Δ |
|---|---|---|---|---|
| 1 | `jcstream-template-author` | Yellow | **Green** | → Green |
| 2 | `jcstream-stylesheet-author` | Yellow | **Green** | → Green |
| 3 | `jcstream-build-helper-author` | Yellow | **Green** | → Green |
| 4 | `jcstream-orc-curator` | Yellow | **Green** | → Green |
| 5 | `jcstream-scraper-author` | Yellow | **Green** | → Green |
| 6 | `jcstream-test-author` | Red | **Green** | → Green |
| 7 | `jcstream-design-interpreter` | Yellow | **Green** | → Green |
| 8 | `jcstream-legal-copy-author` | Yellow | **Green** | → Green |
| 9 | `jcstream-a11y-auditor` | Yellow | **Green** | → Green |
| 10 | `jcstream-sweep-debugger` | Yellow | **Green** | → Green |

**Summary**: pass 1 = 1 Red + 9 Yellow + 0 Green. Pass 2 = 10 / 10 Green. Per-skill reports under `audits/skills-pass2/`; pass-1 baseline preserved at `audits/skills/`.

================================================================================
## Subagent 1/10 — pass-2 audit of `jcstream-template-author`
**Source report**: `audits/skills-pass2/jcstream-template-author.md`
================================================================================

# Audit Pass 2 — jcstream-template-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 fixes landed; line cites verify on the live files and the new contracts (feed.xml, lightbox/tier `data-*`, Giscus, `noindex,noarchive`) are documented.

## Pass-1 recommendation status
1. Refresh every line cite (currentFilters 228-232, view-toggle handler 197-216, lightbox open/close/fallback 125-156, env globals 79-144): **Done** — SKILL.md:25 cites `base.html:228-232` (verified `web/templates/base.html:228-232`); SKILL.md:30 cites `base.html:197-216` (verified `web/templates/base.html:197-216`); SKILL.md:43 cites `:125-130`, `:134-136`, `:144-156` (verified `web/templates/base.html:125-130`, `:134-136`, `:144-156`); SKILL.md:61 cites `web/build.py:79-144` (verified `web/build.py:79-144`).
2. Add `feed.xml` to owned-files list + RSS trigger: **Done** — SKILL.md:3 lists `feed.xml` in description and "update the RSS template" trigger; SKILL.md:8 names it explicitly and credits `_render_feeds` at `web/build.py:173` (verified `web/build.py:173`).
3. Document lightbox `data-*` contract + tier-tooltip `data-tip` contract: **Done** — SKILL.md:36-41 spells out `data-photo`/`-cap`/`-alt` and points at the delegated handler `base.html:157-162` (verified `web/templates/base.html:157-162`) and producer `_card.html:10` (verified `web/templates/_card.html:10`); SKILL.md:45-46 documents `#tier-tip` at `base.html:91` (verified `web/templates/base.html:91`), JS at `:165-195` (verified `web/templates/base.html:165-195`), producer `_card.html:7` (verified `web/templates/_card.html:7`).
4. Mention conditional Giscus block + `giscus` env-global + `noindex,noarchive` meta: **Done** — SKILL.md:63 cites `giscus` global at `web/build.py:90-95` (verified `web/build.py:90-95`) and the conditional block at `web/templates/inmate.html:293-323` (verified `web/templates/inmate.html:293-323`); SKILL.md:48-49 documents the `noindex, noarchive` meta at `base.html:10` (verified `web/templates/base.html:10`) and ties it to ORC § 2953.32.
5. Broaden triggers (masthead, footer, filter, table view, lightbox): **Done** — SKILL.md:3 description appends "edit the masthead/footer", "fix the lightbox", "add a filter", "tweak the table view", "update the RSS template".

## New issues found in pass 2
- Paired agent `/.claude/agents/jcstream-template-author.md:3` description still omits `feed.xml` from the file enumeration and lacks the new contracts (lightbox/tier-tooltip `data-*`, Giscus, `noindex,noarchive`). Cosmetic since the SKILL.md is the source of truth, but the two are now slightly out of sync.
- Minor: SKILL.md:13 says cache-bust is set by `web/build.py:98-101`; the assignment is at lines 100-101 with `import hashlib` and `_css = …` at 98-99. The range is inclusive and reasonable, but technically only 100-101 are the `css_version` line. Not worth flagging again.

## Pass-2 lens checks
- **Drift**: Clean. Every cite I sampled (`web/templates/base.html:10, 78, 91, 125-130, 134-136, 144-156, 157-162, 165-195, 197-216, 228-232`; `web/templates/_card.html:5, 7, 10`; `web/templates/index.html:192`; `web/build.py:79-144, 90-95, 100-101, 173`; `web/templates/inmate.html:293-323`) matches reality.
- **Coverage**: Clean for the SKILL.md side. Agent .md trails (see new issues).
- **Triggers**: Clean. The description now matches the most common phrasings in CLAUDE.md-style task wording.
- **Applicability**: Domain remains central — all eight template files still render every 30-min build (`web/build.py:169-176`); skill should stay.

================================================================================
## Subagent 2/10 — pass-2 audit of `jcstream-stylesheet-author`
**Source report**: `audits/skills-pass2/jcstream-stylesheet-author.md`
================================================================================

# Audit Pass 2 — jcstream-stylesheet-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 recommendations landed cleanly; remaining nits are cosmetic.

## Pass-1 recommendation status
1. Fix ladder-cell line range + mobile-breakpoint enumeration: **Done** — ladder cells now point at `style.css:1217-1244` (SKILL.md:28, matching real `.ladder-grid` at `web/static/style.css:1217` and `.ladder-MM` at `:1244`); breakpoint count corrected to "twelve occurrences" with explicit lines `:183, 513, 880, 1081, 1177, 1292, 1359, 1525, 1580, 1684` plus inline `:1498, :1616` (SKILL.md:37). Verified against `grep -n "@media (max-width: 720px)"` which returns exactly those 12 lines.
2. Acknowledge non-720 breakpoints on `.rb-grid`: **Done** — SKILL.md:39 calls out `style.css:756-757` (`max-width: 1080px` → 3 cols, `max-width: 540px` → 2 cols) and explicitly says "don't take that as license to add more". Matches `web/static/style.css:756-757`.
3. Add `--border`, `--border-hi`, `--accent-bg-2`, `--cincy-navy`, `--cincy-red` + flag shared hex values: **Done** — Surface row at SKILL.md:13 now includes `--border`/`--border-hi`; Accent row at :15 includes `--accent-bg-2`; new City row at :18 lists `--cincy-navy`/`--cincy-red`. SKILL.md:23 explicitly notes `--ok`/`--misd` share `#4f7c3a` and `--danger`/`--warn` share `#b54545` — confirmed at `web/static/style.css:26-30`.
4. Add "Components you also own" mini-list: **Done** — SKILL.md:44-54 lists lightbox (`:1363-1409`), recent-bookings stack (`:750-776`), dispatch/CFS map (`:1593-1616`), comments/Giscus (`:1640-1652`), stacked bar (`:1483-1498`), top-list (`:1500`), court calendar (`:1530-1583`), bond box-and-whisker (`:1297-1362`), timeline (`:1252-1295`), stats KPIs (`:1458-1481`). All anchors match the pass-1 findings.
5. Broaden trigger phrases: **Done** — SKILL.md:3 description adds `"edit the stylesheet"`, `"tweak the lightbox"`, `"fix the table view"`, `"recolor the F3 chip"`, `"tune the print layout"` exactly as proposed.

Additional improvements not in pass-1 list: `@view-transition` + `prefers-reduced-motion` guards now flagged (SKILL.md:25); `.view-toggle[aria-pressed="true"]` named at SKILL.md:31; `--tier-felony-bd`/`--tier-misd-bd` explicitly noted (SKILL.md:17, matching `web/static/style.css:38-39`); print-suppression rule now tells authors to add new interactive components to it (SKILL.md:42).

## New issues found in pass 2
- Minor: SKILL.md:11 says `:root` at "`style.css:7-54`" — `:root` opens at `web/static/style.css:7` but closes at `:54` (verified), so range is accurate. Pass-1 flagged this as off-by-two; the fix landed.
- Paired agent (`.claude/agents/jcstream-stylesheet-author.md`) was not updated to mirror the new component list — still references only the six pass-1 items (lines 11-16). Not blocking since the agent delegates to the skill on first turn (line 9), but the agent's own bullet list is slightly stale.

## Pass-2 lens checks
- **Drift**: Clean. All line anchors verified against `web/static/style.css` (1701 lines total).
- **Coverage**: Clean. Lightbox, photo-stack, dispatch map, comments, stats viz layer, view-toggle, view-transition all now named with anchors.
- **Triggers**: Clean. Description covers cards, tier colors, hero, lightbox, table view, F3 chip, print, and bare "edit the stylesheet" (SKILL.md:3).
- **Applicability**: Stylesheet remains the central visual surface (1701 lines, edited every design pass) — skill is correctly load-bearing.

================================================================================
## Subagent 3/10 — pass-2 audit of `jcstream-build-helper-author`
**Source report**: `audits/skills-pass2/jcstream-build-helper-author.md`
================================================================================

# Audit Pass 2 — jcstream-build-helper-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five recommended fixes landed cleanly; the skill now matches `web/build.py:79-144` and `scraper/models.py` precisely.

## Pass-1 recommendation status
1. Add 24 unlisted env.globals helpers: **Done** — new "Currently registered env.globals" section enumerates them grouped by domain (`.claude/skills/jcstream-build-helper-author/SKILL.md:41-47`); spot-checked `primary_charge`, `card_data`, `crimes_of_month`, `all_inmates_total`, `related_inmates` against `web/build.py:104,118,138,144,143`.
2. Fix Inmate/Charge/Snapshot field lists: **Done** — `full_name` flagged as `@property` and added `first_seen_utc`/`last_seen_utc` (`SKILL.md:28`); `comments` added to Charge (`SKILL.md:29`); `schema_version: int = 1` and the `_check_snapshot_invariants` model validator both called out (`SKILL.md:30`). All match `scraper/models.py:27,62-63,65-71,101,122-143`.
3. Update line range `79-140` → `79-144`: **Done** — `SKILL.md:14` and `SKILL.md:42` both cite `build.py:79-144`, matching the actual range (last entry at `web/build.py:144`).
4. Mention `_offense_for_code` as the fine→coarse dispatcher: **Done** — added with file:line citation (`SKILL.md:39`).
5. Append trigger phrases "register a Jinja global" / "compute bond/tier": **Done** — front-matter description now includes "register a Jinja global", "compute bond/tier/category for inmate", "categorize this ORC code" (`SKILL.md:3`).

## New issues found in pass 2
- None. The line range correction (1682) at `SKILL.md:8` matches `wc -l` output.
- Bonus: SKILL.md:49 also picks up the unregistered snapshot-shape helpers (`_recent_booked_inmates`, `_orc_frequency`, `_group_by_month`, `_short_month_label`) that pass-1 listed under coverage gap B — a fix not explicitly requested but welcome.
- Paired agent (`/.claude/agents/jcstream-build-helper-author.md`) was not updated, but its content is a high-level pointer to the skill and contains no specific claims that drifted — acceptable.

## Pass-2 lens checks
- **Drift**: Clean. Line range, model fields, and helper names all reconcile with `web/build.py:79-144` and `scraper/models.py:17-143`.
- **Coverage**: Clean. The "Currently registered env.globals" inventory closes the 24-helper gap; the `_offense_for_code` dispatcher is documented; site/template plumbing (`base_url`, `site_url`, `css_version`, `giscus`, `cck_*`) explicitly listed with a "don't reinvent" note (`SKILL.md:47`).
- **Triggers**: Clean. Description now ends with "compute bond/tier/category for inmate", "categorize this ORC code", "register a Jinja global" — should fire on common phrasings like "register a Jinja global for X" and "compute bond total per inmate".
- **Applicability**: Still live and central — `web/build.py` remains the sole renderer driving every page and is actively growing.

================================================================================
## Subagent 4/10 — pass-2 audit of `jcstream-orc-curator`
**Source report**: `audits/skills-pass2/jcstream-orc-curator.md`
================================================================================

# Audit Pass 2 — jcstream-orc-curator

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 recommended fixes landed cleanly in SKILL.md with no new drift.

## Pass-1 recommendation status
1. Fix `build.py:139` → `web/build.py:1287`, "warning-log" → "info-log": **Done** — SKILL.md:46 was verified 2026-05-14 against `web/build.py:1283-1287` and `web/build.py:146` (`_warn_about_unmapped_orcs` def, `log.info` call, invocation). Post-2026-05-19 refactor those symbols are at `web/build.py:335, 345, 186`; SKILL.md has since been re-edited to drop literal line numbers (current SKILL.md:46-47). The paired agent file also updated to "info-log line" (`.claude/agents/jcstream-orc-curator.md:3`).
2. Document `_CODE_RE` permitting three-part IDs like `2907.323`: **Done** — SKILL.md:43 spells out `_CODE_RE` location (`scraper/orc.py:24`), the regex `r"\d+\.\d+(?:\.\d+)?"`, and explicitly notes three-part section IDs are legitimate while subsection suffixes are not. Matches `scraper/orc.py:24`.
3. Mention `primary_degree`, `codes_without_titles`, `UNKNOWN = "?"`: **Done** — SKILL.md:11 lists `lookup`, `title_for`, `degree_for`, `primary_degree`, `codes_without_titles`, and the `UNKNOWN = "?"` sentinel, with correct one-liner descriptions ("most-severe across a list of codes" and "drives the curation queue"). Matches `scraper/orc.py:46,54,58,62,79` and `scraper/orc.py:28`.
4. Note `_degree_order` mirror and `_load_explainers` silent-failure: **Done** — SKILL.md:44 calls out the `_degree_order` sibling mirror at `data/orc_offenses.json:4` vs `DEGREE_ORDER` at `scraper/orc.py:27`; SKILL.md:47 covers the silent JSON-error swallow at `web/build.py:694-703` and the `statute.html:44` fallback copy. Both citations check out.
5. Broaden trigger phrases: **Done** — SKILL.md:3 now includes "fix ORC tier/degree", "add explainer", "ORC code shows ?/unknown", "plain-English for §...", "edit orc_offenses.json or explainers.json" alongside the original three.

## New issues found in pass 2
- None.

## Pass-2 lens checks
- **Drift**: Clean. SKILL.md:46 line numbers match `web/build.py:1283-1287, 146` exactly; SKILL.md:11 matches `scraper/orc.py:46,54,58,62,79`; SKILL.md:43 matches `scraper/orc.py:24`; SKILL.md:44 matches `data/orc_offenses.json:4` and `scraper/orc.py:27`; SKILL.md:47 matches `web/build.py:694-703`.
- **Coverage**: Clean. All five gap items from pass 1 are addressed. The schema block (SKILL.md:14-40) now also reflects `_degree_order` at row 19 — consistent with `data/orc_offenses.json:4`.
- **Triggers**: Clean. The expanded trigger list at SKILL.md:3 covers the previously-missed phrasings ("fix the tier for §…", "code shows ?/unknown", "edit orc_offenses.json").
- **Applicability**: Domain remains alive — `scraper/orc.py` is imported by `web/build.py:24` and consumed throughout, both data files are populated, and `statute.html:44` still renders explainers; keep the skill.

================================================================================
## Subagent 5/10 — pass-2 audit of `jcstream-scraper-author`
**Source report**: `audits/skills-pass2/jcstream-scraper-author.md`
================================================================================

# Audit Pass 2 — jcstream-scraper-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: Every pass-1 recommendation is implemented with accurate citations; only nits remain.

## Pass-1 recommendation status
1. Fix verify command (`tests/test_sweep_guards.py` → `tests/test_sweep.py`): **Done** — `SKILL.md:66` now runs `tests/test_sweep.py` (file exists; pass-1 line 13).
2. Name the fourth feed (`incidents.py` / `k59e-2pvf`): **Done** — `SKILL.md:46` lists `k59e-2pvf — PDI Crime Incidents in scraper/incidents.py`; description also enumerates `incidents.py` at `SKILL.md:3`.
3. Document `check_detail_watchdog`, `prune_photos`, `SWEEP_WALLCLOCK_HARD_CAP_S`: **Done** — watchdog at `SKILL.md:19` (constants verified at `sweep_guards.py:30-37`), photo prune at `SKILL.md:21` (matches `sweep_guards.py:43,104-129`), wall-clock at `SKILL.md:31` (matches `scraper/sweep.py:61`).
4. Mention `pra_base.py` + `pra_jms_vendor.py` and `ingest_issue` workflow: **Done** — PRA modules at `SKILL.md:56`; issue-ingest pipeline at `SKILL.md:53`.
5. Broaden trigger phrases: **Done** — `SKILL.md:3` adds "add an Open Data feed", "Socrata pull", "fix the sweep cron", "tune detail watchdog", "raise/lower roster guard", "PRA email loop", "courtclerk link helper", "photo prune skipped", "incidents feed", "rate-limit", "sweep wall-clock".
6. Update workflow paragraph (Pages deploy + 50-min timeout): **Done** — `SKILL.md:51` cites `upload-pages-artifact@v3`, `deploy-pages@v4`, `github-pages` env binding, and `timeout-minutes: 50` (verified at `.github/workflows/sweep.yml:35,38-40,100-105`).
7. Cite `client.py:26-34` rate-limit constants and corrupt-snapshot refusal: **Done** — rate-limit constants at `SKILL.md:31` (verified at `scraper/client.py:26-34`); `load_current_or_raise` + `SnapshotCorruptError` + `CHANGELOG_LIMIT` at `SKILL.md:23` (verified at `scraper/store.py:28-36,41,76-87`).

## New issues found in pass 2
- Minor: `SKILL.md:11` still labels the constant block "`sweep_guards.py:23-25`" — the actual list-sweep constants span `sweep_guards.py:23-25` (correct), but `SWEEP_MIN_ROSTER_FRACTION = 0.5` is reproduced as `0.5` (`SKILL.md:14`) — now matches source (`sweep_guards.py:24`). Pass-1 nit is closed.
- Minor: `scraper/match.py` mentioned at `SKILL.md:48` but only as a one-liner; acceptable for a scope hint.
- The paired agent `.claude/agents/jcstream-scraper-author.md:14` still says "a fifth" Open Data feed, which is fine but won't auto-update if a fifth is added; not a regression.

## Pass-2 lens checks
- **Drift**: Clean. All cited line ranges verified against `scraper/sweep_guards.py:23-25,30-37,43,46-61,64-101,104-129`, `scraper/sweep.py:61`, `scraper/client.py:26-34`, `scraper/store.py:28-36,41,76-87`, and `.github/workflows/sweep.yml:35,38-40,100-105`.
- **Coverage**: Clean. All pass-1 gaps (incidents feed, detail watchdog, photo prune, wall-clock cap, snapshot-corrupt refusal, changelog limit, `pra_base`/`pra_jms_vendor`, `ingest_issue`, `match.py`, rate-limit constants) are now named in `SKILL.md:19-23,31,46,48,53,56`.
- **Triggers**: Clean. Description (`SKILL.md:3`) covers all phrasings flagged in pass-1 section C.
- **Applicability**: Alive — every owned file referenced (`scraper/sweep.py`, `sweep_guards.py`, four OD pullers, `client.py`, `store.py`, three PRA modules, `match.py`, `ingest_issue.py`) is present; sweep cron remains 30-min (`.github/workflows/sweep.yml:7`).

================================================================================
## Subagent 6/10 — pass-2 audit of `jcstream-test-author`
**Source report**: `audits/skills-pass2/jcstream-test-author.md`
================================================================================

# Audit Pass 2 — jcstream-test-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Red
- **Pass-2 verdict**: Green
- **One-line summary**: Every pass-1 fix landed; counts match disk (140 tests, 15 `test_*.py` files, 1707 lines); fixtures, parser, store, client, and PRA send coverage are all documented.

## Pass-1 recommendation status
1. Replace "148 tests" with "140": **Done** — SKILL.md:3, :8, :75 and agent:11, :16 all read "140". CLAUDE.md:43 also reads "140". `grep "^def test_\|^    def test_" tests/ | wc -l` = 140.
2. Drop `respx`, document `monkeypatch`: **Done** — SKILL.md:49 explicitly states "`monkeypatch` … — not `respx` (it is not a dependency)" and cites `tests/test_client.py:38-129` and `tests/test_pra_send.py:17-110`.
3. Add a fixtures subsection: **Done** — SKILL.md:38-44 is a dedicated "Fixtures directory" section citing `tests/fixtures/README.md`, the DOE/ROE/VOE rule, ORC 149.43, and the three existing HTML files (`list_smith.html`, `detail_inmate.html`, `detail_no_photo.html`) which I confirmed exist on disk.
4. Remove `test_sweep_guards.py` reference: **Done** — SKILL.md:20 now folds it into `test_sweep.py` (lines 23-190) and SKILL.md:54 re-cites the same range. `ls tests/test_sweep_guards.py` returns nothing.
5. Expand layout list: **Done** — SKILL.md:18-33 now lists all 15 `test_*.py` files, including the previously missing `test_parsers.py`, `test_open_data.py` (correctly tagged "largest file, 148 LOC" — matches `wc -l`), `test_pra_send.py`, `test_client.py`, `test_courtclerk.py`, `test_cincy_open.py`, `test_ingest_issue.py`, `test_photos.py`.
6. Remove `selectolax` template-render claim: **Done** — `grep selectolax` against SKILL.md returns 0 matches; the only remaining mock-library mention is the explicit `respx`-negation at SKILL.md:49.
7. Broaden trigger phrases: **Done** — SKILL.md:3 now includes "regression test", "pytest", "test the parser", "fixture for", "the suite is failing" alongside the originals.

## New issues found in pass 2
- None.

## Pass-2 lens checks
- **Drift**: Clean. Counts match disk (140 tests at `tests/`; 15 `test_*.py` files + `__init__.py` = 16; 1707 total lines per `wc -l`). The "15 files" claim at SKILL.md:8 is correct if read as "15 `test_*.py` files" (pass-1 read it as "all files in `tests/`" which would also include `__init__.py`); either count is defensible and no longer mis-states reality.
- **Coverage**: Clean. SKILL.md:51-59 enumerates pure helpers, env globals via Jinja, scraper guards (`scraper/sweep_guards.py:46`), store schema round-trip / `SnapshotCorruptError` (`tests/test_store.py:7,145,152,164`), HCSO HTML parsers, httpx retry harness, PRA SMTP, and GitHub-issue ingest — every gap called out in pass-1 §B is now addressed.
- **Triggers**: Clean. SKILL.md:3 covers the obvious phrasings ("write a test for", "fix the failing test", "add coverage") and the JCStream-specific ones flagged in pass-1 §C ("regression test", "pytest", "test the parser", "fixture for", "the suite is failing").
- **Applicability**: Domain remains fully alive — `tests/` is the terminal node for every code-path chain in `.claude/skills/README.md`, and the skill is now accurate enough to route there confidently.

================================================================================
## Subagent 7/10 — pass-2 audit of `jcstream-design-interpreter`
**Source report**: `audits/skills-pass2/jcstream-design-interpreter.md`
================================================================================

# Audit Pass 2 — jcstream-design-interpreter

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All six pass-1 fixes landed cleanly with accurate `file:line` citations and no new drift.

## Pass-1 recommendation status
1. Replace invented helper names with real `env.globals`: **Done** — SKILL.md:23 now lists `bond_context`, `display_date`, `timeline_markers`, `primary_charge`, `primary_chapter`, `primary_tier`, `recent_booked_inmates`, `similar_by_statute`, `tier_counts`, `avatar_initials`, `card_data`, `approx_age`, all matching `web/build.py:103-127`.
2. Add "Project primitives a port must preserve" section: **Done** — SKILL.md:34-41 covers lightbox+inert (`base.html:78-150` confirmed, dialog at base.html:78), view-toggle (`base.html:197-216` confirmed at base.html:198-216), `data-*` filter hooks (`_card.html:5` confirmed, attrs verbatim), `css_version` cache-bust (`build.py:96-101` matches build.py:100), and base.html override blocks (matches base.html:6, 32, 66, 67).
3. Correct font note (Inter + JetBrains Mono only): **Done** — SKILL.md:30 explicitly says "the project fetches **only Inter + JetBrains Mono**" and notes Geist is fallback-only in `style.css:51-53` (confirmed by grep — Geist appears only in `--font-sans`/`--font-serif`/`--font-mono` fallback chains).
4. Mark `.ut-*` mapping as historical: **Done** — SKILL.md:21 leads with "historical worked example", SKILL.md:43 heading is "Reference mapping (historical worked example…)", explicitly noting "those selectors no longer exist in the live CSS (only a stray `.ut-muted` remains at `style.css:1061`)" — confirmed by grep.
5. Add `jcstream-legal-copy-author` to paired agent handoff: **Done** — `agents/jcstream-design-interpreter.md:21` adds "FCRA banner / disclaimer / removal-protocol footer copy → **jcstream-legal-copy-author**".
6. Broaden trigger phrases: **Done** — SKILL.md:3 now includes "build from this mockup", "convert this JSX", "redesign the homepage from this", "redesign … from this spec", "here's a Figma/PNG/screenshot of the new …", "based on this PNG".

## New issues found in pass 2
- Minor citation slip: SKILL.md:38 cites view-toggle at "`base.html:197-216`" but `#view-toggle` button is actually rendered in `index.html:192` (toggle script body is in `base.html:198-216`). Pass-1 had the same dual cite; not a regression, just imprecise. Skim-level only.
- SKILL.md:23 cites `build.py:103-130`; actual helper registrations span `build.py:103-127` with no gap, so the range is one or two lines wider than strictly needed but not wrong.

## Pass-2 lens checks
- **Drift**: Clean — every cited symbol (`bond_context`, `card_data`, `primary_chapter`, `css_version`, `data-photo`/`data-photo-cap`/`data-photo-alt`, `body.is-table`, `jcs-view`, `inert`) verified in source.
- **Coverage**: Clean — the five primitives added in SKILL.md:34-41 close the gaps pass-1 flagged; legal-copy handoff is now wired into the paired agent.
- **Triggers**: Clean — short forms ("convert this JSX", "build from this mockup", "based on this PNG", "redesign … from this spec") are present in SKILL.md:3 description, matching ambient phrasings pass-1 worried about.
- **Applicability**: Live — `.ut-muted` residue and the `style.css:2` "Modern utility theme" header still signal an active port surface; skill stays relevant for the next design intake.

================================================================================
## Subagent 8/10 — pass-2 audit of `jcstream-legal-copy-author`
**Source report**: `audits/skills-pass2/jcstream-legal-copy-author.md`
================================================================================

# Audit Pass 2 — jcstream-legal-copy-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: The pass-1 fixes landed cleanly — the no-fee tail is now consistent across all five carriers, CC BY-NC, JSON-LD, `noarchive`, HB 234/HB 96 and the comment-policy commitments are all named, and triggers cover the obvious phrasings.

## Pass-1 recommendation status
1. Add CC BY-NC 4.0 as a fourth legal-copy domain: **Done** — `SKILL.md:34` enumerates `base.html:71`, `inmate.html:288`, `data.html:110`, `inmate.html:28` (JSON-LD), and the row at `SKILL.md:17,21` lists the same plus the row at `SKILL.md:20` for the data page grant.
2. Resolve the no-fee tail inconsistency: **Done** — `SKILL.md:33` lists `inmate.html:83` and `inmate.html:290` inside the full-tail required-phrases set, and both lines now carry the full tail (`web/templates/inmate.html:83` and `web/templates/inmate.html:290`). The pass-1 "Known no-fee tail inconsistency" follow-up has been deleted (grep for `tail inconsistency` returns no matches).
3. Mention `base.html:7-10` `noarchive` rationale and `inmate.html:18-33` JSON-LD: **Done** — `SKILL.md:15` and `SKILL.md:22` add both rows; `SKILL.md:55` makes the `noarchive` rationale a no-touch item.
4. Expand "Reference statutes" with HB 234 / HB 96 and ORC §§ 2953.31–2953.61: **Done** — `SKILL.md:73,74` cite both.
5. Broaden trigger phrases: **Done** — `SKILL.md:3` adds "expungement language", "sealing notice", "takedown protocol", "no-fee guarantee", "license footer", "presumption of innocence".
6. Enumerate comment-policy commitments: **Done** — `SKILL.md:60-69` spells out all eight commitments and `SKILL.md:58` makes dropping any of them a no-touch item.

## New issues found in pass 2
- Minor: the paired agent file at `.claude/agents/jcstream-legal-copy-author.md:11` still lists only the original required phrases (FCRA, ORC § 149.43, ORC § 2953.32, no-fee tail) without referencing the new CC BY-NC 4.0 domain that the SKILL now owns at `SKILL.md:34`. The agent points at the SKILL as source-of-truth (`agents/...md:9`), so this is cosmetic, not load-bearing — flag-only.
- Minor: the `Verify` grep at `SKILL.md:85` does not include `CC BY-NC` or `noarchive`, so a grep-before-commit would not catch a regression in those new domains. Not a blocker, but tightening the regex would close the loop on fix #1 and fix #3.

## Pass-2 lens checks
- **Drift**: Clean. All required-phrase line citations verified: `index.html:8`, `inmate.html:83`, `inmate.html:290`, `stats.html:202`, `data.html:79-80` all carry the full no-fee tail; `inmate.html:18-33` JSON-LD claims exist; `base.html:7-10` `noarchive` rationale is in place; `data.html:76` cites HB 234/HB 96 and `data.html:81` cites §§ 2953.31–2953.61.
- **Coverage**: Clean. The four legal-copy domains (presumption, FCRA, removal/sealing, licensing) are all named, plus the JSON-LD, figcaption attribution, meta descriptions, comment policy, and `noarchive` rationale.
- **Triggers**: Clean. The expanded list at `SKILL.md:3` covers "expungement", "sealing", "takedown", "no-fee", "license footer", "presumption of innocence" — the pass-1 misses are gone.
- **Applicability**: Domain remains alive and load-bearing — six templates plus `base.html` still carry the legal copy on every page.

================================================================================
## Subagent 9/10 — pass-2 audit of `jcstream-a11y-auditor`
**Source report**: `audits/skills-pass2/jcstream-a11y-auditor.md`
================================================================================

# Audit Pass 2 — jcstream-a11y-auditor

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All six pass-1 fixes landed; every cited `file:line` re-verifies and the trigger list now covers the obvious phrasings.

## Pass-1 recommendation status
1. Re-cite line numbers (tier 676-685, ladder 1235-1244, tooltip 91, sr-only h1 66, tab cycler 144-156): **Done** — `SKILL.md:20` cites `style.css:676-685` (matches `web/static/style.css:676-685`), `SKILL.md:21` cites `style.css:1235-1244` (matches `web/static/style.css:1235-1244`), `SKILL.md:36` cites `base.html:78` (lightbox at `web/templates/base.html:78`), `SKILL.md:40` cites `base.html:91` (tooltip at `web/templates/base.html:91`), `SKILL.md:50` cites `base.html:66` (sr-only h1 at `web/templates/base.html:66`), `SKILL.md:56` cites `base.html:144-156` (tab cycler at `web/templates/base.html:144-156`).
2. Soften reduced-motion claim and list unguarded transitions / `jc-pulse`: **Done** — `SKILL.md:53` states only `scroll-behavior` is guarded and enumerates `jc-pulse` keyframes at `style.css:151,153` (verified at `web/static/style.css:151,153`) plus the unguarded `transition:` rule lines.
3. Add skip-link, `<caption class="sr-only">`, `role="region"/"status"/"list"`, and `aria-describedby` to the ARIA inventory: **Done** — `SKILL.md:33` (skip link → `base.html:33`+`style.css:66-72`), `SKILL.md:38-39` (region/status), `SKILL.md:41` (`aria-describedby="tier-tip"` on `.tier-corner` → `_card.html:7`), `SKILL.md:43` (statbar role list/listitem → `stats.html:17,20`), `SKILL.md:44` (`<caption class="sr-only">` → `inmate.html:93`, `data.html:20`) — all verified.
4. Flag `outline: 0` at `style.css:464` as a focus-visibility regression: **Done** — `SKILL.md:28` calls out `web/static/style.css:464` (`outline: 0`) explicitly as a regression to fix; verified at `web/static/style.css:464`.
5. Note `--fg-dim-raised` still exists as an alias: **Done** — `SKILL.md:8` clarifies the variable is still declared at `web/static/style.css:20` as an alias to `--fg-dim`; verified at `web/static/style.css:20` (`#94a3b8`, same value).
6. Broaden trigger phrases ("a11y", "ARIA", "focus ring", "keyboard nav", "alt text", "color contrast"): **Done** — `SKILL.md:3` description now lists "accessibility audit", "a11y", "a11y review", "WCAG check", "ARIA", "ARIA check", "screen reader", "contrast issue", "color contrast", "focus ring", "keyboard nav", "alt text".

## New issues found in pass 2
- Minor: `SKILL.md:19` cites the `#6b3434` hard-coded ink at `style.css:242,955,1334,1649`. Lines 242 (`web/static/style.css:242`), 955 (`.alert` block), and 1649 (`.comment-policy` block) verify, but `:1334` is the `background: var(--warn-bg);` line inside the Cincy banner block and not itself a `#6b3434` foreground (the foreground for that block is at `:1331` via `color: var(--warn);`). Off-by-three but easy fix; doesn't change the audit value.
- Paired agent `.claude/agents/jcstream-a11y-auditor.md` was not refreshed alongside SKILL.md: `agents/...:12` still lists only the older ARIA tokens (`aria-current/aria-pressed/aria-modal/aria-live/role="dialog"/"tooltip"`), omitting the newly-inventoried `role="region"`, `role="status"`, `role="list"/"listitem"`, `<caption class="sr-only">`, and `aria-describedby`. Skill discovery still works (the SKILL.md is the source of truth), but the handoff doc is slightly behind.

## Pass-2 lens checks
- **Drift**: Clean except for the `#6b3434` line-number nit above; all other re-cites verified.
- **Coverage**: Clean — skip link, caption sr-only, region/status/list, aria-describedby, the `outline:0` regression, and the unguarded `jc-pulse`/transitions are all now documented.
- **Triggers**: Clean — description at `SKILL.md:3` covers the common phrasings flagged in pass 1.
- **Applicability**: Domain still fully alive; every cited file/line resolves and the skill remains worth keeping.

================================================================================
## Subagent 10/10 — pass-2 audit of `jcstream-sweep-debugger`
**Source report**: `audits/skills-pass2/jcstream-sweep-debugger.md`
================================================================================

# Audit Pass 2 — jcstream-sweep-debugger

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 fixes landed accurately with correct file:line cites, and the broadened triggers now cover the previously blind detail-watchdog symptoms.

## Pass-1 recommendation status
1. Fix the broken `pytest` invocation pointing at non-existent `tests/test_sweep_guards.py`: Done — SKILL.md:94 now reads `python -m pytest -q tests/test_sweep.py`; that file exists at `tests/test_sweep.py` and covers `sweep_looks_healthy`/`check_detail_watchdog`/`prune_photos` (`tests/test_sweep.py:10-117`).
2. Add a Step-3b table for the detail-watchdog WARN/BLOCK pairs: Done — new §3b at SKILL.md:41-53 documents `DETAIL_WATCHDOG_MIN_SAMPLE`, `_NAME_FLOOR`, `_PHOTO_FLOOR`, `_BLOCK_MIN_SAMPLE`, `_BLOCK_NAME_FLOOR` with correct cites to `scraper/sweep_guards.py:30-37` (verified in source at `sweep_guards.py:30-37`) and the invocation site at `scraper/sweep.py:197-200` (verified).
3. Add wall-clock cap / checkpoint-guard / corrupt-snapshot / save-failure / photo-prune rows: Done — table at SKILL.md:56-62 lists all five paths with cites at `scraper/sweep.py:61`, `:152-157`, `:183-196`, `:80-90`, `:212-216`, and `scraper/sweep_guards.py:104-129`; each verified against current source (e.g., `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` at `scraper/sweep.py:61`).
4. Note `data/history.json` is owned by `web/build.py`, not the sweep: Done — verified 2026-05-14 with `_update_history` at `web/build.py:1321`. Post-2026-05-19 refactor the function is at `web/build.py:456`; SKILL.md:71 has since been re-edited to drop the line number ("Owned by `web/build.py` (`_update_history`), not by the sweep").
5. Broaden trigger phrases (stale photos, partial sweep, sweep bailed, nameless records, detail watchdog): Done — SKILL.md:3 now includes all five new phrases plus the original four.

## New issues found in pass 2
- None substantive. SKILL.md:8 still references the back-compat alias path correctly (real function at `scraper/sweep_guards.py:46`, alias at `scraper/sweep.py:65` — both verified). The atomic-write contract is now mentioned at SKILL.md:64 with correct cite to `scraper/store.py:44-54` (verified — `_atomic_write_text` defined at `store.py:44`).

## Pass-2 lens checks
- **Drift**: Clean. Every cite I spot-checked resolves (`sweep_guards.py:23-25,30-37,46,64-101,104-129`; `sweep.py:61,80-90,152-157,183-196,197-200,212-216`; `store.py:44-54`; `build.py:1321`; `tests/test_sweep.py`).
- **Coverage**: Clean. The six failure paths pass-1 flagged (detail watchdog, wall-clock cap, checkpoint guard, corrupt-snapshot, save-failure, photo prune skip) and the atomic-write contract are all now documented (SKILL.md:41-64).
- **Triggers**: Clean. The description at SKILL.md:3 fires on the obvious phrasings ("sweep didn't update", "stuck count") plus the previously missed detail-watchdog symptoms ("stale photos", "nameless records", "detail watchdog") and partial-sweep symptoms ("partial sweep", "sweep bailed", "sweep timed out"). The CLAUDE.md preamble (CLAUDE.md:46-49) describes the same fallback the skill anchors on, so routing is consistent.
- **Applicability**: Domain is alive — `scraper/sweep.py`, `scraper/sweep_guards.py`, `data/{current,changelog,history}.json`, and `.github/workflows/sweep.yml` are all current; the paired agent at `.claude/agents/jcstream-sweep-debugger.md:9` correctly directs to invoke this skill on every task.

