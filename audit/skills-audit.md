# JCStream skill audits — combined report

- **Run date**: 2026-05-14
- **Branch**: `claude/export-skill-agent-zip-gspVE`
- **Method**: 10 `general-purpose` subagents in parallel, one per `jcstream-*` skill, audited along four lenses (drift, coverage gaps, trigger-phrase quality, applicability).
- **Per-skill reports**: `audits/skills/<name>.md`

## Verdict roll-up

| # | Skill | Verdict | One-line summary |
|---|---|---|---|
| 1 | `jcstream-template-author` | Yellow | Conventions and contracts are accurate, but every cited line number has drifted and the env-globals catalog stops short of the real registration block. |
| 2 | `jcstream-stylesheet-author` | Yellow | Token system, anti-patterns, and tier palette are accurate, but the mobile-breakpoint count and ladder-cell line range are wrong, and several owned components (lightbox, recent-bookings photo-stack, CFS/dispatch map, stacked-bar/timeline, stats page) go unmentioned. |
| 3 | `jcstream-build-helper-author` | Yellow | Core contract and named helpers/maps still match code, but model field lists are incomplete and the registration block has grown well past what SKILL.md cites. |
| 4 | `jcstream-orc-curator` | Yellow | Schemas, conventions, and ladder are all accurate, but the cited log-line location is stale by ~1150 lines and the log level is mischaracterised as a "warning." |
| 5 | `jcstream-scraper-author` | Yellow | Core sweep-guard claims are accurate, but the SKILL.md misses three feeds, two new guards, the orchestrator wall-clock cap, and points the verify command at a test file that does not exist. |
| 6 | `jcstream-test-author` | Red | Multiple stale numeric claims, two non-existent dependencies are recommended for use, one referenced test file does not exist, and ~half of the actual test suite is unmentioned. |
| 7 | `jcstream-design-interpreter` | Yellow | Output contract and mapping table verify cleanly, but the playbook invents helper names, overstates the loaded fonts, and omits three active porting primitives (lightbox/inert, view-toggle, data-* filter hooks). |
| 8 | `jcstream-legal-copy-author` | Yellow | Every named claim verifies, but the SKILL omits the CC BY-NC 4.0 licensing copy and the inmate page's "no-fee" tail is inconsistent with the contract the SKILL itself asserts. |
| 9 | `jcstream-a11y-auditor` | Yellow | Concept and ARIA inventory are accurate, but several `file:line` cites have drifted and a few notable patterns (skip-link, outline:0 on filter inputs, unguarded transitions/animation) are missing. |
| 10 | `jcstream-sweep-debugger` | Yellow | Core thresholds and triage flow are accurate, but the skill misses the entire detail-page watchdog + wall-clock cap + checkpoint guards and points at a non-existent test file. |

---

================================================================================
## Subagent 1/10 — audit of `jcstream-template-author`
**Source report**: `audits/skills/jcstream-template-author.md`
================================================================================

# Audit — jcstream-template-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-template-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-template-author.md
- **Verdict**: Yellow
- **One-line summary**: Conventions and contracts are accurate, but every cited line number has drifted and the env-globals catalog stops short of the real registration block.

## A. Drift
- SKILL.md:13 — claims `build.py:100-101` for `css_version`; actual line is `web/build.py:100` only (single statement spanning 100-101 logically, but the cite is fine). The `import hashlib as _hl` sits at `web/build.py:98` so the "lines 100-101" framing is ok-ish but undercites context.
- SKILL.md:20 — says the `data-*` attrs are set in `_card.html:5`; verified at `web/templates/_card.html:5`. OK.
- SKILL.md:25 — claims `currentFilters()` lives at `base.html:239-241`; actual definition is `web/templates/base.html:228-232`. Drift of ~10 lines.
- SKILL.md:30 — "Button: `index.html` (`<button id="view-toggle">`)"; the real markup at `web/templates/index.html:192` is `<button type="button" class="view-toggle" id="view-toggle" aria-pressed="false" hidden>`. Line number missing, attribute set understated (the `hidden` + `aria-pressed` are load-bearing — JS un-hides at `base.html:200` and toggles aria-pressed at `:206`).
- SKILL.md:31 — "JS handler: `base.html:160-178`"; actual handler block is `web/templates/base.html:197-216`. Drift of ~37 lines.
- SKILL.md:32 — "CSS: `style.css:481-516`"; verified at `web/static/style.css:481-516`. OK.
- SKILL.md:36 — "`base.html:125-135` sets `inert`"; actual `inert` open at `web/templates/base.html:125-130`, close at `:134-136`, Tab-cycler fallback at `:144-156`. The single range conflates open + close + fallback.
- SKILL.md:45 — "helpers registered in `build.py:79-126`"; registrations actually run `web/build.py:79-144` (e.g. `bond_total`, `days_in_custody`, `charges_by_chapter`, `crimes_of_month`, `orc_freq`, `codes_ohio_url`, `related_inmates`, `all_inmates_total`, `inmates_by_id`, `all_chapters` are all past line 126). Range is short by 18 lines.

## B. Coverage gaps
- `web/templates/feed.xml` exists (`web/templates/feed.xml:1-19`) and is rendered via `_render_feeds` — SKILL.md frontmatter and the body never list it, so a "fix the RSS template" prompt won't auto-route.
- The shared lightbox markup contract — `<div class="lightbox" id="lb" role="dialog" aria-modal="true">` at `web/templates/base.html:78`, plus the `data-photo` / `data-photo-cap` / `data-photo-alt` trigger contract used by `_card.html:10` and the click delegate at `base.html:157-162` — is invoked by every thumbnail but isn't documented.
- The shared tier-tooltip pattern (`#tier-tip` at `base.html:91`, `data-tip` consumed at `base.html:165-195`, written by `_card.html:7`) is a cross-template contract that only the tooltip-tweaker would otherwise discover by archaeology.
- Conditional Giscus comments block at `web/templates/inmate.html:293-318` (gated on `giscus.repo_id`) is owned by this skill but unmentioned; the `giscus` env-global at `web/build.py:90-95` is also missing from the catalog.
- The `noindex, noarchive` robots meta at `web/templates/base.html:10` is load-bearing for the ORC § 2953.32 expungement contract — worth a one-liner so it isn't accidentally removed.
- The search type-ahead dropdown at `web/templates/base.html:267-360` lazy-loads `/search.json`; if a template task touches `#search-box` markup the skill gives no warning that JS depends on the id.

## C. Trigger-phrase quality
- Current description (paraphrased): "editing or creating Jinja templates under web/templates/ — base.html, index.html, inmate.html, stats.html, statute.html, data.html, _card.html. Covers css_version, data-* filter hooks, body.is-table, lightbox inert, base.html block overrides. Trigger phrases: 'edit the inmate page', 'add a section to the homepage', 'fix template rendering'."
- Issues: `feed.xml` is missing from the file enumeration; trigger set omits the most natural phrasings — "update the footer", "tweak the masthead", "fix the lightbox", "add a filter", "table view", "RSS feed".
- Proposed rewording: add `feed.xml` to the file list and append triggers like "edit the masthead/footer", "fix the lightbox", "add a filter", "tweak the table view", "update the RSS template".

## D. Applicability
- Domain is alive and central — all eight files under `web/templates/` are rendered every 30-min build (`web/build.py:169-176`); skill should stay.

## Recommended fixes (priority order)
1. Refresh every line cite: `currentFilters` -> 228-232, view-toggle handler -> 197-216, lightbox open/close/fallback -> 125-156, env globals -> 79-144.
2. Add `feed.xml` to the owned-files list in both frontmatter and body, and add "RSS feed" trigger.
3. Document the lightbox trigger contract (`data-photo`/`-cap`/`-alt`) and the tier-tooltip `data-tip` contract — both are cross-template patterns with implicit JS dependencies.
4. Mention the conditional Giscus block and the `giscus` env-global; mention the `noindex, noarchive` meta tied to ORC § 2953.32.
5. Broaden trigger phrases (masthead, footer, filter, table view, lightbox).

================================================================================
## Subagent 2/10 — audit of `jcstream-stylesheet-author`
**Source report**: `audits/skills/jcstream-stylesheet-author.md`
================================================================================

# Audit — jcstream-stylesheet-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-stylesheet-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-stylesheet-author.md
- **Verdict**: Yellow
- **One-line summary**: Token system, anti-patterns, and tier palette are accurate, but the mobile-breakpoint count and ladder-cell line range are wrong, and several owned components (lightbox, recent-bookings photo-stack, CFS/dispatch map, stacked-bar/timeline, stats page) go unmentioned.

## A. Drift
- SKILL.md:34 says "(six occurrences: `:183, :513, :880, :1081, :1177`)" — only 5 line numbers listed and the real count of `@media (max-width: 720px)` is **12** (`web/static/style.css:183, 513, 880, 1081, 1177, 1292, 1359, 1525, 1580, 1684`, plus inline ones at `:1498, :1616`). The trailing print-mode mobile block at `style.css:1684` is the canonical bottom anchor, not `:1177`.
- SKILL.md:25 places ladder cells at "`style.css:1008-area`". Line 1008 is `.tier-row` — actual `.ladder-grid` / `.ladder-cell` / `.ladder-F1`…`.ladder-MM` definitions are at `web/static/style.css:1217-1244`, inside the "Severity ladder" section (`web/static/style.css:1195`).
- SKILL.md:11 says ":root block at `style.css:5-54`". `:root` actually opens at `web/static/style.css:7` and closes at `:54` — minor off-by-two on the start.
- SKILL.md:17 lists tier tokens but omits `--tier-felony-bd` / `--tier-misd-bd` callout that they're border-color twins of the bg pair (`web/static/style.css:38-39`); existing copy is technically correct, just incomplete.
- SKILL.md:16 lists `--ok` and `--misd` but both literally evaluate to `#4f7c3a` (`web/static/style.css:29-30`) — readers may assume they are independently tunable; they currently are not.

## B. Coverage gaps
- `--border` / `--border-hi` (`web/static/style.css:13-14`) and `--accent-bg-2` (`:25`) are not in the token table at SKILL.md:13-21 even though they're load-bearing for hover/border treatments (`web/static/style.css:220, 673`).
- City-accent tokens `--cincy-navy` / `--cincy-red` (`web/static/style.css:42-43`) are unmentioned — they're used by CFS captions and easy to clobber.
- `.lightbox` system at `web/static/style.css:1363-1409` (used by inmate mugshot zoom, suppressed in print at `:1664`) — owned, undocumented.
- Recent-bookings photo-stack (`.rb-grid`, `.rb-card` with its own `content-visibility` at `web/static/style.css:768`, plus `@media (max-width:1080px)` and `:540` breakpoints at `:756-757`) — these are the **only non-720 breakpoints** in the file and contradict the "extend the existing 720 px block" rule (SKILL.md:34).
- Dispatch / CFS map block (`web/static/style.css:1593-1616`) and Comments / Giscus block (`:1640-1652`) — both interactive-only, both already correctly suppressed in `@media print` (`:1665`); SKILL.md doesn't tell future authors to add new interactive elements to that print-suppression list.
- Stacked severity bar (`.stacked-leg` at `web/static/style.css:1483-1498`), top-list (`:1500`), court calendar (`:1530-1583`), bond box-and-whisker (`:1297-1362`), time-in-custody timeline (`:1252-1295`), stats KPIs (`:1458-1481`) — entire stats/inmate visualization layer is unmentioned.
- `.view-toggle[aria-pressed="true"]` (`web/static/style.css:478`) — the table-mode toggle handle that drives `body.is-table`; mentioned consequentially but not by name.
- `@view-transition` (`web/static/style.css:60`) and `prefers-reduced-motion` guard (`:59`) — affect cross-page animation; should be flagged so authors don't break them.

## C. Trigger-phrase quality
- Current description (paraphrased): "Use when editing web/static/style.css. Covers light-theme tokens, 10-tier ladder, body.is-table, content-visibility, 720 px breakpoint, print rule. Trigger phrases: restyle the cards / fix the tier colors / make the hero bigger / add a CSS rule."
- Issues: triggers skew toward homepage cards/hero. Common phrasings like "tweak the mugshot lightbox", "table view is broken on mobile", "the print stylesheet drops too much", "recolor the F3 chip", "fix the dispatch map height", "the comments section overlaps" wouldn't obviously match. Also "stylesheet" / "CSS" as bare verbs ("the CSS is broken", "edit style.css") are missing.
- Proposed rewording (additive only): add `, "edit the stylesheet", "tweak the lightbox", "fix the table view", "recolor the F3 chip", "tune the print layout"` to the trigger list.

## D. Applicability
- Domain is alive and central — `web/static/style.css` is 1701 lines, edited every design pass, owns the entire visual surface; skill should not be retired.

## Recommended fixes (priority order)
1. Fix the ladder-cell line range (point at `web/static/style.css:1217-1244`, not `:1008-area`) and the mobile-breakpoint enumeration (12 occurrences, not 6; list the real anchor lines or stop enumerating).
2. Acknowledge the two non-720 breakpoints on `.rb-grid` (`:756-757`) so the "no new breakpoints" rule isn't taken as absolute.
3. Add tokens `--border`, `--border-hi`, `--accent-bg-2`, `--cincy-navy`, `--cincy-red` to the table; note that `--ok` and `--misd` (and `--danger` / `--warn`) currently share hex values.
4. Add a "Components you also own" mini-list: lightbox, recent-bookings stack, dispatch map, comments, stacked-bar, timeline, bond box-and-whisker, stats KPIs — each with its `style.css:` anchor.
5. Broaden the trigger phrases as proposed in section C.

================================================================================
## Subagent 3/10 — audit of `jcstream-build-helper-author`
**Source report**: `audits/skills/jcstream-build-helper-author.md`
================================================================================

# Audit — jcstream-build-helper-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-build-helper-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-build-helper-author.md
- **Verdict**: Yellow
- **One-line summary**: Core contract and named helpers/maps still match code, but model field lists are incomplete and the registration block has grown well past what SKILL.md cites.

## A. Drift
- `web/build.py:79-140` cited as the registration range; actual block runs `web/build.py:111-184` post-2026-05-19 refactor (line 184 registers `all_inmates_total`). The SKILL.md cite is pre-refactor.
- "(~1700 lines)" — file was 1682 lines pre-2026-05-19; now 922 after the classify.py / shape.py split (`web/build.py:922`).
- `Inmate` field list omits `first_seen_utc` and `last_seen_utc` (`scraper/models.py:62-63`) and lists `full_name` as a field, but it is a `@property` on `Inmate` (`scraper/models.py:65-71`).
- `Charge` field list omits `comments` (`scraper/models.py:27`).
- `Snapshot` field list omits `schema_version: int = 1` (`scraper/models.py:101`) and the `_check_snapshot_invariants` model validator that enforces `inmate_count == len(inmates)` (`scraper/models.py:122-143`) — both are load-bearing for any helper that mutates or constructs snapshots.
- `_DEGREE_RE`, `_CHAPTER_LABEL`, `_OFFENSE_CATEGORY`, `_CLS_RANK`, `_parse_book_date`, `_parse_bond_amount`, `_charge_tier`, `_primary_tier`, `_primary_degree` all still exist but moved post-2026-05-19 to `web/classify.py` (`:26,51,101,84,150,173,387,440,461`); `_days_in_custody` moved to `web/shape.py:534`.

## B. Coverage gaps
- 24 env.globals-registered helpers are unmentioned. Registration sites all sit in `web/build.py:111-184`; def sites moved out of build.py in the 2026-05-19 refactor: `primary_charge` (`web/build.py:141`, def `web/shape.py:587`), `primary_chapter` (`web/build.py:142`, def `web/shape.py:602`), `tier_max` (`web/build.py:145`, def `web/classify.py:467`), `tier_ladder` (`web/build.py:146`), `display_date` (`web/build.py:150`, def `web/classify.py:189`), `timeline_markers` (`web/build.py:149`, def `web/shape.py:229`), `similar_by_statute` (`web/build.py:151`, def `web/shape.py:289`), `tier_counts` (`web/build.py:152`, def `web/classify.py:424`), `avatar_initials` (`web/build.py:154`, def `web/classify.py:257`), `card_data` (`web/build.py:155`, def `web/shape.py:471`), `card_tip` (`web/build.py:156`, def `web/shape.py:484`), `expand_race` / `expand_sex` (`web/build.py:157-158`, defs `web/classify.py:275,285`), `approx_age` (`web/build.py:159`, def `web/classify.py:217`), `booking_seq` (`web/build.py:160`, def `web/classify.py:239`), `bond_by_tier` (`web/build.py:164`, def `web/shape.py:352`), `next_court_date` (`web/build.py:165`, def `web/shape.py:371`), `case_numbers` (`web/build.py:166`, def `web/shape.py:445`), `charge_status_summary` (`web/build.py:167`, def `web/shape.py:455`), `bond_total` (`web/build.py:175`, def `web/shape.py:522`), `charges_by_chapter` (`web/build.py:177`, def `web/shape.py:552`), `crimes_of_month` (`web/build.py:178`, def `web/shape.py:77`), `orc_freq` (`web/build.py:181`), `codes_ohio_url` (`web/build.py:182`, def `web/classify.py:352`), `related_inmates` (`web/build.py:183`, def `web/shape.py:60`).
- Key non-registered helper used by every category lookup: `_offense_for_code` (`web/classify.py:369`) — the entry point to the fine→coarse fallback; should be called out alongside the maps.
- Snapshot-shape helpers `_recent_booked_inmates` (`web/shape.py:91`), `_orc_frequency` (`web/classify.py:479`), `_group_by_month` (`web/shape.py:621`), `_short_month_label` (`web/classify.py:199`) — all feed env.globals or templates, none mentioned.
- `giscus`, `css_version`, `base_url`, `site_url`, `inmates_by_id`, `all_chapters` env.globals (`web/build.py:111,115,120-126,130,174,179`) — not Python helpers per se, but worth one line so authors don't reinvent them.

## C. Trigger-phrase quality
- Current description (paraphrased): "adding/modifying Python helper functions in web/build.py for Jinja templates; covers env.globals registration, Inmate/Snapshot models, the regex/maps, date helpers; phrases like 'add a helper for X', 'compute Y per inmate', 'expose Z to templates'."
- Issues: Solid coverage. Could miss "compute bond total", "register a Jinja global", "primary charge logic" — which are common real phrasings. Minor.
- Proposed rewording: append phrases "register a Jinja global", "compute bond/tier/category for inmate", "categorize this ORC code". Otherwise leave as-is.

## D. Applicability
- Live and core — `web/build.py` is the sole renderer driving every page; the helper layer is actively expanding (24+ unlisted helpers).

## Recommended fixes (priority order)
1. Add the 24 unlisted env.globals helpers to "Helpers you can build on" (or a new "Currently registered" subsection) so authors don't duplicate work.
2. Fix `Inmate`/`Charge`/`Snapshot` field lists: note `full_name` as `@property`, add `first_seen_utc`/`last_seen_utc`/`comments`/`schema_version`, mention the snapshot invariants validator.
3. Update line range "around `build.py:79-140`" to `79-144` (or drop the literal range).
4. Mention `_offense_for_code` as the dispatcher between `_OFFENSE_CATEGORY` and `_CHAPTER_LABEL`.
5. Optionally append "register a Jinja global" / "compute bond/tier" trigger phrases.

================================================================================
## Subagent 4/10 — audit of `jcstream-orc-curator`
**Source report**: `audits/skills/jcstream-orc-curator.md`
================================================================================

# Audit — jcstream-orc-curator

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-orc-curator/SKILL.md
- **Paired agent**: .claude/agents/jcstream-orc-curator.md
- **Verdict**: Yellow
- **One-line summary**: Schemas, conventions, and ladder are all accurate, but the cited log-line location is stale by ~1150 lines and the log level is mischaracterised as a "warning."

## A. Drift
- SKILL.md:46 cites `build.py:139` for the unmapped-codes log; the actual call is at `web/build.py:345` inside `_warn_about_unmapped_orcs` (defined at `web/build.py:335`, invoked at `web/build.py:186`). Post-2026-05-19 refactor — line 139 is no longer the `inmates_by_id` registration (`env.globals["inmates_by_id"]` is now at `web/build.py:179`).
- SKILL.md:3, 46 and the agent file (`.claude/agents/jcstream-orc-curator.md:3`) call this a "warning-log" / "warns"; in fact it logs at `log.info` level (`web/build.py:345`), so a `grep "WARNING"` will miss it. The user-facing string in the verify block (SKILL.md:66) does match: `"ORC titles missing"`.
- SKILL.md:43 names the normalizer `orc_mod.normalize_code`; the function is defined as bare `normalize_code` in `scraper/orc.py:39`. `orc_mod` is only the import alias used inside `web/build.py:24`. Minor but potentially confusing for someone grepping `scraper/orc.py`.

## B. Coverage gaps
- The skill never mentions `lookup()` (`scraper/orc.py:46`), `primary_degree()` (`scraper/orc.py:62`), `codes_without_titles()` (`scraper/orc.py:79`), or the `UNKNOWN = "?"` sentinel (`scraper/orc.py:28`) that returns when a degree is missing. `primary_degree`/`codes_without_titles` are the very functions that drive the curation queue and tier coloring.
- The regex governing what counts as an ORC code, `_CODE_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")` (`scraper/orc.py:24`), accepts a third dotted group (e.g. `2907.323` at `data/orc_offenses.json:30`). SKILL.md says "no subsection" but doesn't acknowledge the legitimate three-part section numbers already in the file.
- The skill doesn't mention that `_load_explainers` (`web/classify.py:506`) silently swallows JSON errors and that `statute.html:44` falls back to the "No plain-English explainer is on file" copy — useful context for "why did my new entry not appear."
- Current data inventory is uneven: 109 entries in `data/orc_offenses.json` versus 37 in `data/explainers.json` (head/tail counts). The skill could note that explainers cover only the top-of-roster subset rendered by `_render_statute_page` (`web/build.py:781`, top_n=60).
- No mention that `data/orc_offenses.json:4` carries `_degree_order` as a sibling array that must stay in sync with `DEGREE_ORDER` in `scraper/orc.py:27`.

## C. Trigger-phrase quality
- Current description (paraphrased): maintains ORC mappings; covers normalization, the 10-tier ladder, and the unmapped-codes warning. Triggers: "add an ORC code", "explainer for §...", "missing statute title".
- Issues: triggers are reasonable but narrow. Common phrasings that would *not* match: "what does 2907.05 mean", "fix the tier for §2925.11", "this code shows no title", "add a plain-English explainer", "the chip is grey/unknown for this charge", "update orc_offenses.json".
- Proposed rewording: add triggers like "fix ORC tier/degree", "add explainer", "ORC code shows ?/unknown", "plain-English for §...", "edit orc_offenses.json or explainers.json".

## D. Applicability
Domain is alive: `scraper/orc.py` is referenced 18 times in `web/build.py`, both data files exist with active content, and `statute.html` consumes explainers — keep the skill.

## Recommended fixes (priority order)
1. Update `build.py:139` → `web/build.py:1287` (function `_warn_about_unmapped_orcs`); change "warning-log" wording to "info-log" since it uses `log.info`.
2. Add a sentence explaining `_CODE_RE` permits `\d+\.\d+\.\d+`-style section IDs (e.g. `2907.323`), so three-part keys are legitimate while subsection suffixes (`A2`) are not.
3. Mention `primary_degree`, `codes_without_titles`, and the `UNKNOWN = "?"` sentinel in the "You own" section of SKILL.md.
4. Note the `_degree_order` mirror in `data/orc_offenses.json:4` and the silent-failure behavior of `_load_explainers` (`web/build.py:694`).
5. Broaden trigger phrases per section C.

================================================================================
## Subagent 5/10 — audit of `jcstream-scraper-author`
**Source report**: `audits/skills/jcstream-scraper-author.md`
================================================================================

# Audit — jcstream-scraper-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-scraper-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-scraper-author.md
- **Verdict**: Yellow
- **One-line summary**: Core sweep-guard claims are accurate, but the SKILL.md misses three feeds, two new guards, the orchestrator wall-clock cap, and points the verify command at a test file that does not exist.

## A. Drift
- SKILL.md:11 cites `sweep_guards.py:23-25` — accurate (`scraper/sweep_guards.py:23-25`), but lists `0.50` while the actual constant is `0.5` (`scraper/sweep_guards.py:24`). Trivial.
- SKILL.md:17 cites `sweep_looks_healthy()` at `sweep_guards.py:57-66` — actual span is `sweep_guards.py:46-61` (signature on 46, returns on 61).
- SKILL.md:38 says the fourth Cincinnati feed is "in `cincy_open.py`" — wrong. `scraper/cincy_open.py:1-62` is a generic Socrata helper; the four real feeds are `cfs.py` (`qiik-bpks`), `cfs_pdi.py` (`gexm-h6bt`), `shootings.py` (`sfea-4ksu`), and `incidents.py` (`k59e-2pvf`). The SKILL.md never names `incidents.py`.
- SKILL.md:56 verify command names `tests/test_sweep_guards.py` — that file does not exist; only `tests/test_sweep.py` exists (guard tests live there, e.g. `tests/test_sweep.py:169,178,185`).
- SKILL.md:43 says workflow "commits, pushes" but omits the `actions/upload-pages-artifact@v3` + `deploy-pages@v4` steps (`.github/workflows/sweep.yml:100-105`) and the `github-pages` environment binding (`sweep.yml:38-40`).

## B. Coverage gaps
- `scraper/incidents.py:1-83` — fourth OD feed (`k59e-2pvf`), wired into `sweep.yml:65-67`; not mentioned by name.
- `check_detail_watchdog()` and constants `DETAIL_WATCHDOG_*` (`scraper/sweep_guards.py:30-37,64-101`) — a second-tier guard with hard BLOCK at name-rate < 0.60 over ≥100 attempts; entirely absent from the skill.
- `prune_photos()` + `PHOTO_PRUNE_MAX_FRACTION = 0.5` (`scraper/sweep_guards.py:43,104-129`) — the third guard, not mentioned.
- `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` (`scraper/sweep.py:61`) — orchestrator's wall-clock budget; should be in "Rate-limit etiquette" or "Workflow contract".
- `SnapshotCorruptError` + `load_current_or_raise` (`scraper/store.py:28-36,76-87`) — sweep refuses cycle on corrupt prior; explicitly invariant.
- `scraper/pra_jms_vendor.py:1-110` — third PRA module (JMS-vendor request) and `pra_base.py` (`scraper/pra_base.py:1-67`) consolidating SMTP transport; SKILL.md only names `pra.py` + `pra_capias.py`.
- `scraper/ingest_issue.py` + `.github/workflows/ingest_case_data.yml` — issue-form → `data/courtclerk_cases.json` ingest pipeline, not mentioned.
- `scraper/match.py:1-85` — CFS↔inmate matcher; not mentioned.
- `scraper/client.py` constants `DEFAULT_CONCURRENCY=32`, `DEFAULT_CRAWL_DELAY=0.0`, `RETRY_AFTER_CAP_S=30.0` (`scraper/client.py:26-34`) — the actual rate-limit budget; SKILL.md's "Rate-limit etiquette" prose doesn't cite them.
- `data/changelog.json` rolling window `CHANGELOG_LIMIT = 500` (`scraper/store.py:41`) — sweep-side invariant.

## C. Trigger-phrase quality
- Current description (paraphrased): scraper/, HCSO sweep, four OD feeds (cfs/cfs_pdi/shootings), courtclerk URL helpers, PRA loop, sweep guards, atomic write, 30-min cron. Triggers: "add a new data feed", "fix the HCSO scraper", "tune the sweep guard".
- Issues: triggers do not match common phrasings like "rate-limit", "PRA email", "Socrata", "incidents feed", "courtclerk URL", "photo prune", "detail watchdog", or "sweep wall-clock". A user saying "the cron is timing out" or "add an incidents column" would not auto-fire this skill.
- Proposed rewording: add to triggers — "add an Open Data feed", "Socrata pull", "fix the sweep cron", "tune detail watchdog", "raise/lower roster guard", "PRA email loop", "courtclerk link helper", "photo prune skipped".

## D. Applicability
- Alive — every owned file is present, the sweep cron runs every 30 min (`.github/workflows/sweep.yml:7`), and the PRA loop has a daily workflow (`.github/workflows/pra_daily.yml:7`); not retirable.

## Recommended fixes (priority order)
1. Fix the verify command (`tests/test_sweep_guards.py` → `tests/test_sweep.py`).
2. Name the fourth feed (`incidents.py` / `k59e-2pvf`) and replace the "in `cincy_open.py`" line.
3. Document `check_detail_watchdog`, `prune_photos`, and `SWEEP_WALLCLOCK_HARD_CAP_S` in the guards section.
4. Mention `pra_base.py` + `pra_jms_vendor.py` and the `ingest_issue` workflow in scope.
5. Broaden trigger phrases per section C.
6. Update the workflow paragraph to include the Pages deploy steps and 50-min `timeout-minutes`.
7. Cite `client.py:26-34` rate-limit constants and the corrupt-snapshot refusal at `store.py:76-87`.

================================================================================
## Subagent 6/10 — audit of `jcstream-test-author`
**Source report**: `audits/skills/jcstream-test-author.md`
================================================================================

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
- **`selectolax` template-parse pattern is aspirational.** SKILL.md:41 says "render with a fixture snapshot, parse the result with `selectolax`". `grep selectolax tests/` returns nothing. `selectolax` is a real dep (`pyproject.toml:13`) used only in `scraper/parsers.py:10` and copy at `web/build.py:878`. No test renders a Jinja template through `selectolax`.
- **`Snapshot(inmates=[...])` constructor pattern.** SKILL.md:34 says "Inline `Snapshot(inmates=[...])` constructors are fine". `Snapshot` is constructed in `tests/test_models.py:54,63,73,81,87` only — the build-helper tests in `tests/test_build.py:14-26` use `Inmate` directly, not `Snapshot`. Pattern is partially accurate but miscredits where it appears.
- **Layout list omits `_card.html`-style breakdown.** SKILL.md:18-28 lists 8 file slots (with "…"); the unlisted real files include test_parsers.py (163 LOC), test_open_data.py (148 LOC, the largest), test_pra_send.py (117 LOC), test_client.py (133 LOC), test_ingest_issue.py (85 LOC), test_courtclerk.py, test_cincy_open.py, test_photos.py.

## B. Coverage gaps
- **`tests/fixtures/` HTML scaffold is unmentioned.** `tests/fixtures/README.md:1-30` defines a strict naming policy (DOE/ROE/VOE + JOHN/JANE), the no-real-records rule under ORC 149.43, and three offline HTML fixtures (`list_smith.html`, `detail_inmate.html`, `detail_no_photo.html`). This is the single most important convention for this skill and SKILL.md never mentions the directory.
- **HTML parser test pattern.** `tests/test_parsers.py:1-163` is the canonical example of feeding fixture HTML through `parse_detail_page`/`parse_list_page` (`tests/test_parsers.py:5`), exercising the orphan-row guard, the `?id=` → `/inmate-detail/N/` permalink shift, and base64 photo extraction — none of this surfaces in SKILL.md.
- **`SnapshotCorruptError` / store schema-version contract.** `tests/test_store.py:7,145,152,164` enforces the schema_version round-trip. SKILL.md:25 mentions test_store.py vaguely as "photo cache / data writes" but misses the corruption-guard contract.
- **PRA SMTP send path.** `tests/test_pra_send.py` (117 LOC) covers the live-send branch (STARTTLS at 587, implicit TLS at 465, missing-credentials skip, SMTP failure). SKILL.md:26 only acknowledges "PRA email loop (dry-run path)".
- **HCSO httpx client retry/backoff harness.** `tests/test_client.py:38-129` is the template for retry-on-5xx, Retry-After honoring, and env-var override testing — a pattern future scraper tests should mirror. Not mentioned.
- **GitHub-issue ingest tests.** `tests/test_ingest_issue.py:1-85` (parses issue body, builds case record, upserts) is invisible in SKILL.md but represents an active code path.
- **Cincinnati Open Data shape tests.** `tests/test_open_data.py` (148 LOC, the biggest file) and `tests/test_cincy_open.py` cover the four open-data feeds called out in CLAUDE.md.

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

================================================================================
## Subagent 7/10 — audit of `jcstream-design-interpreter`
**Source report**: `audits/skills/jcstream-design-interpreter.md`
================================================================================

# Audit — jcstream-design-interpreter

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-design-interpreter/SKILL.md
- **Paired agent**: .claude/agents/jcstream-design-interpreter.md
- **Verdict**: Yellow
- **One-line summary**: Output contract and mapping table verify cleanly, but the playbook invents helper names, overstates the loaded fonts, and omits three active porting primitives (lightbox/inert, view-toggle, data-* filter hooks).

## A. Drift
- **Invented helper names.** SKILL.md:23 cites "(`fmtAge`, `daysSince`, `bondContext`, …)" as data-need examples. None exist in `web/build.py`; actual `env.globals` are `bond_context`, `display_date`, `timeline_markers`, `primary_charge`, `recent_booked_inmates`, `similar_by_statute`, etc. (`web/build.py:103-116`). Reads as JSX camelCase that survived the port; misleading as a project reference.
- **Font claim overstated.** SKILL.md:30 says "the project uses Geist/Inter + JetBrains Mono via Google Fonts (preconnected in `base.html`)". `base.html:22-24` only preconnects/loads `Inter` + `JetBrains+Mono`; `Geist`/`Geist Mono` appear only as CSS fallbacks (`style.css:51-53`) and are never fetched. A new design relying on Geist would silently fall through to Inter.
- **`.ut-*` mapping table reads as current state.** SKILL.md:21,34-50 still phrase "the modern-utility direction we ported" as ongoing. Grep across `web/` finds zero `.ut-*` selectors except a stray `.ut-muted` at `style.css:1061`. The table is fine as a worked example but should be marked historical.

## B. Coverage gaps
- **Lightbox + `inert` focus management** (`base.html:78-150`, `style.css:1364-1397`): one shared `<div class="lightbox" role="dialog" aria-modal="true" hidden>`, JS swaps the image, siblings get `inert`, Tab-cycler fallback. Any image-detail design must reuse this dialog rather than create a parallel one.
- **View-toggle pattern** (`index.html:192`, `base.html:197-213`, `style.css:478-482`): `body.is-table` flip with `aria-pressed` + `localStorage`. A roster-listing redesign that drops the toggle button or omits the table-mode CSS branch silently regresses the site.
- **`data-*` filter hooks** (`_card.html:5`, `index.html:176-189`, `base.html:222-241`): client-side filter bar keys off `data-tier`/`data-chap`/`data-name`/`data-search` + `data-filter`. New card markup without these attributes breaks search.
- **`css_version` cache-bust** (`web/build.py:100`): sha256 of style.css contents — CLAUDE.md:44-45 explicitly warns not to key it off the data timestamp. Worth one playbook line so a port doesn't invent a parallel scheme.
- **`base.html` override blocks** (`base.html` defines `title`, `body_class`, `sr_h1`, `content`): a design port should extend these, not duplicate `<head>`. Not mentioned.
- **Paired agent missing legal-copy handoff** (`agents/jcstream-design-interpreter.md:16-20`): redesigns touching the FCRA banner / disclaimer / removal protocol footer should route to `jcstream-legal-copy-author`.

## C. Trigger-phrase quality
- Current description (paraphrased): fires on Figma export, JSX mockup, screenshot, design zip, or hand-drawn spec; lists "port this design", "implement the mockup", "translate the Figma", "from this screenshot".
- Issues: coverage is reasonable but misses common short forms — "redesign the homepage from this", "build from this mockup", "here's a screenshot of the new …", "convert this JSX". "From this screenshot" alone is a weak match for ambient phrasings like "based on this PNG".
- Proposed rewording: append "build from this mockup", "convert this JSX", "redesign … from this spec", "here's a Figma/PNG/screenshot of the new …" to the trigger examples.

## D. Applicability
- Live — the active stylesheet still calls itself "Modern utility theme" (`style.css:2`), the `.ut-*` mapping table is the residue of a real port, and design work cycles regularly; keep the skill, do not retire.

## Recommended fixes (priority order)
1. Replace `fmtAge`/`daysSince`/`bondContext` with real helper names from `web/build.py:103-116` (`bond_context`, `display_date`, `timeline_markers`, etc.).
2. Add a "Project primitives a port must preserve" section: lightbox+inert (`base.html:78-150`), view-toggle (`base.html:197-213`), `data-*` filter attributes (`_card.html:5`), `css_version` cache-bust (`build.py:100`), `base.html` override blocks.
3. Correct the font note at SKILL.md:30 — only Inter + JetBrains Mono are fetched; Geist is a fallback only.
4. Reword the `.ut-*` mapping preamble so the table reads as a historical worked example rather than the current selector inventory.
5. Add `jcstream-legal-copy-author` to the paired agent's downstream handoff list.
6. Broaden trigger phrases per section C.

================================================================================
## Subagent 8/10 — audit of `jcstream-legal-copy-author`
**Source report**: `audits/skills/jcstream-legal-copy-author.md`
================================================================================

# Audit — jcstream-legal-copy-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-legal-copy-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-legal-copy-author.md
- **Verdict**: Yellow
- **One-line summary**: Every named claim verifies, but the SKILL omits the CC BY-NC 4.0 licensing copy and the inmate page's "no-fee" tail is inconsistent with the contract the SKILL itself asserts.

## A. Drift
- Path/line claims hold: `web/templates/index.html:5-9` is the legal banner (`<aside class="banner" aria-label="Legal notice">` opens at line 5, closes at line 9). Verified phrases at `index.html:6,7,8`, `base.html:71`, `stats.html:12,202`, `statute.html:13`, `data.html:60,68,75,84-88`, `inmate.html:62,83,295`.
- **Required-phrase contract violation in actual code, not in SKILL**: SKILL.md:29 says the no-fee guarantee is "**repeated on every page that mentions removal**" with the verbatim tail "and there never will be". `web/templates/inmate.html:83` says "**there is never a fee**" (no tail) and `web/templates/inmate.html:290` repeats the short form. This is an internal inconsistency the SKILL should flag as something to *fix*, not as canonical state.
- SKILL.md:13 says the index banner contains "ORC 2953.32" — confirmed at `web/templates/index.html:8`.
- SKILL.md:30 removal endpoint `https://github.com/AICincy/JCStream/issues` matches every site occurrence (`index.html:8`, `inmate.html:83,290,307`, `stats.html:202`, `data.html:78,101`).

## B. Coverage gaps
- **CC BY-NC 4.0 license assertion is unowned**: appears at `web/templates/base.html:71`, `web/templates/inmate.html:28,288`, `web/templates/data.html:110`. This is a legal-copy claim (licensing the JCStream-arranged data) and the SKILL never mentions it.
- **`noarchive` robots meta with sealing/expungement rationale** at `web/templates/base.html:7-10` — explicit ORC § 2953.32 reasoning the SKILL does not cover.
- **JSON-LD legal claims** at `web/templates/inmate.html:18-33` ("isAccessibleForFree", license URL → ORC § 149.43) — structured-data legal claims not mentioned.
- **Figcaption attribution** `Booking photo · ORC § 149.43` at `web/templates/inmate.html:45` — third statute citation per inmate page, not listed.
- **HB 234 / HB 96 amendment references** at `web/templates/data.html:76`, plus the broader **ORC §§ 2953.31–2953.61** citation at `web/templates/data.html:81` — both extend the "Reference statutes" list at SKILL.md:52-55.
- **Meta `description` and `og:description`** at `web/templates/base.html:12,19` — SKILL.md:19 lists these in the table but the body never names them as required-phrase carriers (both contain "presumed innocent" claims).
- **Comment-policy block content** at `web/templates/inmate.html:295-308` is much richer than the SKILL hints (covers removal of identifying info, threats, defamation, thread closure on roster removal) — the SKILL says "comment-policy block" but doesn't enumerate the categories the policy commits to.
- **`statute.html:13` alert** uses "Charges are accusations only" — SKILL's required-phrase list (SKILL.md:25) is "charges are accusations only" (lowercase c) — verify casing intent.

## C. Trigger-phrase quality
- Current description (paraphrased): "user-facing legal language… presumed-innocent banners, FCRA disclaimer, ORC § 149.43, ORC § 2953.32, no-fee guarantee, comment-policy block. Triggers: 'update the disclaimer', 'rephrase the banner', 'fix the FCRA notice', 'removal policy'."
- Issues: triggers miss common phrasings — "expungement", "sealing", "takedown", "presumption of innocence", "no-fee", "comment policy", "DMCA-style removal", "license notice", "CC BY-NC". A user saying "fix the expungement language" or "update the takedown policy" would not obviously route here from triggers alone.
- Proposed rewording: append "expungement language", "sealing notice", "takedown protocol", "no-fee guarantee", "license footer", "presumption of innocence" to the trigger list.

## D. Applicability
- Domain is alive — six owned templates plus the base footer all carry active legal copy that ships on every page; the skill is load-bearing, not stale.

## Recommended fixes (priority order)
1. Add CC BY-NC 4.0 licensing as a fourth legal-copy domain (footer, inmate attribution, data.html) — currently invisible to this specialist.
2. Resolve the no-fee tail inconsistency: either update the SKILL contract to say "tail required only on the homepage, stats, and data" or flag `inmate.html:83,290` as broken and require the tail there too.
3. Mention the `base.html:7-10` `noarchive` rationale and the `inmate.html:18-33` JSON-LD license claim under "Files and where the copy lives".
4. Expand "Reference statutes" with HB 234 / HB 96 amendments and ORC §§ 2953.31–2953.61 (already in `data.html:76,81`).
5. Broaden trigger phrases to include "expungement", "sealing", "takedown", "license", "no-fee".
6. Enumerate the comment-policy commitments (identifying info, threats, defamation, thread-closure-on-removal) so edits can't silently drop categories.

================================================================================
## Subagent 9/10 — audit of `jcstream-a11y-auditor`
**Source report**: `audits/skills/jcstream-a11y-auditor.md`
================================================================================

# Audit — jcstream-a11y-auditor

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-a11y-auditor/SKILL.md
- **Paired agent**: .claude/agents/jcstream-a11y-auditor.md
- **Verdict**: Yellow
- **One-line summary**: Concept and ARIA inventory are accurate, but several `file:line` cites have drifted and a few notable patterns (skip-link, outline:0 on filter inputs, unguarded transitions/animation) are missing.

## A. Drift
- **Tier-chip line range wrong.** SKILL says "`style.css:677-686`"; tier-F1..MM rules actually span `web/static/style.css:676-685` (off-by-one and missing `tier-M3` at line 683). Note `tier-M3` is at 683 between `tier-M2` (682) and `tier-M4` (684).
- **Ladder line range is a placeholder, not a range.** SKILL says "`style.css:1008-area`"; ladder colors are `web/static/style.css:1235-1244`.
- **base.html line refs are off.**
  - SKILL: "Lightbox dialog … `base.html:78`" — correct (`web/templates/base.html:78`).
  - SKILL: "Tier tooltip … `base.html:80`" — actually `web/templates/base.html:91`.
  - SKILL: "sr-only h1 … `base.html:55`" — actually `web/templates/base.html:66`.
  - SKILL: "Lightbox tab cycle (`base.html:135-149`)" — actually `web/templates/base.html:144-156`.
- **Reduced-motion claim is overstated.** SKILL: "Sparkline / spark-card transitions don't run when the user opts out." Only `scroll-behavior` is guarded at `web/static/style.css:59`; the `jc-pulse` keyframes (`style.css:151,153`) and many `transition:` rules (`style.css:70,168,397,475,573,767,1150,1224,1486,1511`) have no `prefers-reduced-motion` guard.
- **Token table omits `--fg-dim-raised`.** SKILL says it was "retired (now equal to `--fg-dim`)"; it's still declared at `web/static/style.css:20` (value `#94a3b8`, identical to `--fg-dim`). The variable persists; only its tuning was retired.
- **Focus-ring claim partly stale.** SKILL: "current outline at 2px, accent color." Only two rules match (`web/static/style.css:1431,1634`); filter inputs explicitly strip focus with `outline: 0` at `web/static/style.css:464` — a legit a11y concern not flagged.

## B. Coverage gaps
- **Skip link** at `web/templates/base.html:33` + `web/static/style.css:66-72` — central WCAG 2.4.1 affordance, never mentioned.
- **`<caption class="sr-only">` table semantics** at `web/templates/inmate.html:93` and `web/templates/data.html:20` — sr-only is mentioned only for the homepage h1.
- **`aria-describedby` + tooltip wiring** at `web/templates/_card.html:7` (`aria-describedby="tier-tip"`) — not in the ARIA inventory.
- **`role="region" aria-label="Search results"`** at `web/templates/index.html:190` and **`role="status"` empty-state** at `web/templates/index.html:198` — not enumerated.
- **`role="list"/"listitem"` on statbars** at `web/templates/stats.html:17,20,75-78,166-172` — undocumented pattern.
- **Color-only focus removal on filter controls** (`web/static/style.css:464`) — exactly the anti-pattern the skill should flag.
- **`#6b3434` hard-coded ink on `--warn-bg`** also reused at `style.css:242,1334-1649` (alert + Cincy banners), not just `.alert p` as the table implies.

## C. Trigger-phrase quality
- Current description (paraphrased): "WCAG AA contrast on light theme; ARIA correctness (aria-current/aria-pressed/aria-modal); keyboard nav; sr-only; reduced-motion. Triggers: 'accessibility audit', 'WCAG check', 'screen reader', 'contrast issue'."
- Issues: Misses common phrasings: "a11y", "ARIA", "keyboard navigation", "focus ring", "tab order", "color contrast", "alt text", "role=…".
- Proposed rewording: add to triggers "a11y review", "ARIA check", "focus ring", "keyboard nav", "alt text", "color contrast" and the strings `"a11y"` / `"ARIA"`.

## D. Applicability
Domain is fully alive — every cited file is owned, ARIA patterns are present, and the audits/ tree already contains sibling reports; keep the skill.

## Recommended fixes (priority order)
1. Re-cite line numbers: tier 676-685, ladder 1235-1244, tooltip 91, sr-only h1 66, tab cycler 144-156.
2. Soften the reduced-motion claim — only `scroll-behavior` is guarded; list the unguarded transitions/`jc-pulse` as gaps to fix.
3. Add skip-link, `<caption class="sr-only">`, `role="region"/"status"/"list"`, and `aria-describedby` to the ARIA inventory.
4. Flag `outline: 0` at `style.css:464` as an existing focus-visibility regression.
5. Note that `--fg-dim-raised` still exists (alias to `--fg-dim`) so audits don't grep-and-miss it.
6. Broaden trigger phrases to include "a11y", "ARIA", "focus ring", "keyboard nav", "alt text", "color contrast".

================================================================================
## Subagent 10/10 — audit of `jcstream-sweep-debugger`
**Source report**: `audits/skills/jcstream-sweep-debugger.md`
================================================================================

# Audit — jcstream-sweep-debugger

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-sweep-debugger/SKILL.md
- **Paired agent**: .claude/agents/jcstream-sweep-debugger.md
- **Verdict**: Yellow
- **One-line summary**: Core thresholds and triage flow are accurate, but the skill misses the entire detail-page watchdog + wall-clock cap + checkpoint guards and points at a non-existent test file.

## A. Drift
- SKILL.md:69 instructs `pytest -q tests/test_sweep_guards.py` but no such file exists; guard tests live in `tests/test_sweep.py:6-12` (imports `from scraper import sweep, sweep_guards`). Command will fail.
- SKILL.md:8 cites `_sweep_looks_healthy` as in-tree; the underscore name is now only a back-compat alias at `scraper/sweep.py:65` (`_sweep_looks_healthy = sweep_looks_healthy`). The real function is `sweep_looks_healthy` in `scraper/sweep_guards.py:46`. Minor — but `grep _sweep_looks_healthy` will mislead a reader.
- SKILL.md:28 cites `scraper/sweep_guards.py:23-25` for the three thresholds. Correct as of `sweep_guards.py:23-25`.
- SKILL.md:46 says `data/history.json` is "Stubby today (≈200 bytes)" — accurate (`wc -c` returns 209 bytes), but it omits that history.json is written by `web/build.py:456-511`, *not* by the sweep, so a stale history.json points at the build, not the scraper.

## B. Coverage gaps
- **Detail-page watchdog**: `sweep_guards.py:64-101` (`check_detail_watchdog`) is a second silent-fallback path with WARN floors (`DETAIL_WATCHDOG_NAME_FLOOR=0.70`, `PHOTO_FLOOR=0.50`) and BLOCK pair (`BLOCK_MIN_SAMPLE=100`, `BLOCK_NAME_FLOOR=0.60`). Triggered at `scraper/sweep.py:197-200` and sets `roster_ok=False`. The skill never mentions it — yet "stale photos but fresh roster count" is exactly when it fires.
- **Wall-clock cap**: `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` at `scraper/sweep.py:61`, enforced at `sweep.py:152-157`. A partial roster persisted via this path will look like a "small" sweep without tripping the 50% floor; missing from the triage flow.
- **Checkpoint guard**: `scraper/sweep.py:183-196` skips intermediate `save_current` checkpoints when in-memory roster is below 50% of previous. A stuck count can come from this even though the final-write path looks fine.
- **Corrupt-snapshot bail**: `scraper/sweep.py:80-90` returns 0 on `SnapshotCorruptError` keeping the broken file in place. A new failure mode worth a triage bullet.
- **Save failure path**: `scraper/sweep.py:212-216` (`save_current` `OSError` → skip changelog & prune) — disk-full / atomic-rename failure also produces "exit 0, no commit" with a different log line.
- **Photo prune skip**: `sweep_guards.py:104-129` (`PHOTO_PRUNE_MAX_FRACTION = 0.5`) silently skips prune when >50% of photos would be deleted. Useful when the symptom is "photos for released inmates aren't disappearing".
- **Atomic write contract**: `scraper/store.py:44-54` (`_atomic_write_text` via tmp + `os.replace`) — CLAUDE.md preamble cites this, the SKILL.md does not.

## C. Trigger-phrase quality
- Current description (paraphrased): "use when investigating why a sweep didn't produce fresh data — flat roster, empty changelog, stale photos, exit-0 sweep with no commit". Triggers: "sweep didn't update", "stuck count", "no changes in changelog", "scraper looks idle".
- Issues: phrasing is solid for the obvious symptoms but won't fire on detail-watchdog symptoms ("photos missing names", "nameless inmates", "photos not updating") or on the new wall-clock/checkpoint paths ("partial sweep", "sweep timed out", "sweep keeps bailing").
- Proposed rewording: add "stale photos", "partial sweep", "sweep bailed", "nameless records", "detail watchdog" to the trigger phrase list.

## D. Applicability
- Domain is alive — `scraper/sweep.py`, `scraper/sweep_guards.py`, `data/{current,changelog,history}.json`, and `.github/workflows/sweep.yml` are all current and on the 30-min cron; skill should be kept.

## Recommended fixes (priority order)
1. Fix the broken pytest invocation at SKILL.md:69 — point at `tests/test_sweep.py` (no `test_sweep_guards.py` exists).
2. Add a Step-3b table for the detail-watchdog (WARN + BLOCK pairs at `sweep_guards.py:30-37`) — it's the second silent-fallback and the skill is currently blind to it.
3. Add wall-clock cap, checkpoint-guard, save-failure, and corrupt-snapshot rows to the failure-mode table (all in `scraper/sweep.py`).
4. Note that `data/history.json` is owned by `web/build.py:456` (`_update_history`), not the sweep — prevents misrouted debugging.
5. Broaden trigger phrases to cover detail-page / partial-sweep symptoms.
