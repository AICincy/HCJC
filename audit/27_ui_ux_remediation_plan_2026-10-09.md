# UI & UX Remediation Plan — 2026-10-09 (audit 26 follow-on)

Tip SHA: `be62652f02f7ff0c12e970099c660eea0f692cdb` (2026-10-09T15:10:04Z), audited branch `aicincy-audit-ui-ux-oct2026` merged as PR #603 at `2026-10-09T16:24:06Z` (`--admin`, squash).
Live `jcstream:generated-utc` fetched 2026-10-09: `2026-10-09T16:09:32Z` on `/`, `/archive/`, `/statute/`, `/data/`, `/transparency/`, `/inmate/1777439/`, `/help/`, `/visit/`, `/court/`, `/bond-schedule/` (branch-serve `build_type=legacy`, `style.css?v=a4227e7ee0`, `theme-init.js?v=1fb7517bcf`, `main.js?v=20dd7601d5`, deterministic `computed_utc == generated_utc`, `freshness_hours 0.0`, `inmate_count 1145`).
Live workflow inventory at tip: 12 files — `archive-evidence.yml`, `ci.yml`, `clerk_pra_packets.yml`, `codeql.yml`, `lint.yml`, `live-parity.yml`, `maintainer_case_ingest.yml`, `pages.yml`, `rebuild.yml`, `refresh_caselaw.yml`, `staleness-watchdog.yml`, `sweep.yml` (`7,37 * * * *` + 20m skip gate). No dated `audit-output/` packet is current truth.

Source: `audit/26_ui_ux_failures_2026-10-09.md` (16-row ledger, 0 contradicted; 18 cataloged failures R/N/D/S/C plus a11y carryover from `audit/00_index.md`). Scope of that audit: documentation only, no template/CSS/JS drift. This plan is the §5 queue. It does not re-audit.

## Contract

* One row per follow-on PR. Each PR patches the source file plus its readers (tests and any `audit-output/` stub that would otherwise read as current) and lands only after lint green. Trigger `rebuild.yml` only when public HTML or data URLs change.
* Each row carries a test pin that asserts the new behavior and a live re-verify (`curl -s https://www.aretheyinjail.com/<path> | grep jcstream:generated-utc` plus the surface-specific probe) after merge before the row closes.
* Verification baseline for every row: `python -m ruff check .`, `python -m mypy scraper web`, `python -m pytest -q`, `python -m web.build` (prod-equivalent `JCSTREAM_SITE_BASE_URL=""` `JCSTREAM_CNAME=www.aretheyinjail.com`), `python scripts/verify_public_data.py`. Failures block merge.
* Branch-serve invariant holds: `sweep.yml` and `rebuild.yml` build into `docs/` (default `--out`) and commit `data/` + `docs/`; `pages.yml` is secondary. Enforced by `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs` and `tests/test_build_determinism.py`.
* No `force-push` on `main`, no hand-edit of `docs/` or `data/waf_block_log.json` (SHA-256 append-only).

## Sequencing

Ordered by productivity rank then leverage. Rank 1 (false ground truth) is already closed by audit 26. Rank 2 (live public truth / task completion) ships first. Rank 3 (optional hygiene) ships last but still in this plan per instruction.

| Phase | Rank | Theme |
|-------|------|-------|
| 1 — Critical | 2 | Blocks core roster/reference tasks or WCAG high |
| 2 — Stability | 2 | Medium task friction, nav/IA, high-value polish that unblocks Phase 1 |
| 3 — Quality | 2/3 | Low task friction and trust/chrome polish (still rank 2 but lower leverage) |
| 4 — Optional hygiene | 3 | CI pins, workflow hygiene, warning-level feed/style hygiene — last, still closed |

Within each phase rows are ordered by leverage (shared touchpoint or widest audience first).

## Unified remediation sequence (18 cataloged failures + a11y carryover + optional categories)

Every row lists source finding, touches with file:line, fix direction, test pin, verification, effort, and rollback. `Effort: S` is one file and one test, `M` touches two surfaces or adds a JS handler.

### Phase 1 — Critical (ship first)

#### Step 1: D1 — Lightbox focus trap and `inert` (a11y-F1)

* Source: `26:D1` (high), `00_index:a11y-F1` (high) — `web/templates/base.html:107-115` `#lb role=dialog aria-modal hidden`, `web/static/main.js:lightbox`, live `/inmate/1777439/` photo trigger.
* Why first: sole high-severity WCAG 2.4.3/2.1.2 failure, modal reads background content, keyboard path broken.
* Touches: `web/templates/base.html` (openLB/closeLB plus Tab cycler), `web/static/main.js` (focus trap, `inert` on `#main` + `.masthead`, return focus to `data-photo` trigger). Fallback when `inert` is absent: `aria-hidden` plus Tab cycler.
* Test pin: `tests/test_a11y_lightbox.py::test_lightbox_traps_tab` (open, Tab cycles inside `#lb`, Shift+Tab wraps, Escape closes and returns focus), `tests/test_a11y_lightbox.py::test_lightbox_inerts_background` (while open, `#main` is `inert` or `aria-hidden` and not tabbable). New file or extend `tests/test_cra_boundary.py`.
* Verification: `python -m web.build` then open `docs/inmate/<id>/index.html`, keyboard-only: Tab from close button stays inside `#lb`, Escape returns focus; `python -m pytest -q` green; live `curl -s https://www.aretheyinjail.com/inmate/1777439/ | grep -c 'role="dialog"'` plus manual Tab check.
* Effort: S
* Rollback: revert the JS handler, `inert` attribute is additive so removal restores prior behavior.

#### Step 2: S1 — Statute jump bar without JS gate (high)

* Source: `26:S1` (high) — `web/templates/statute.html:5-9` `#statute-jump-bar hidden`, live `curl /statute/` shows the bar hidden until JS.
* Why second: core reference task fails offline or under script block, 197-section ladder requires scroll/Find.
* Touches: `web/templates/statute.html` (render a server-side `<form action="#orc-2913-02">` with `<select>` or `<input list>` that JS enhances into live filtering, remove `hidden` gate, keep `data-filter` handler as enhancement), `web/static/main.js` (enhance the server form rather than reveal).
* Test pin: `tests/test_statute_jump.py::test_statute_jump_renders_without_js` (rendered `docs/statute/index.html` contains a `<form>` with `action` targeting `#orc-` without requiring JS), `tests/test_statute_jump.py::test_statute_jump_enhances_with_js` (existing jump still filters when JS is present).
* Verification: `python -m web.build`, `grep -c 'statute-jump-bar' docs/statute/index.html` shows no `hidden` gate, form exists; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/statute/ | grep statute-jump-bar` shows the form.
* Effort: S
* Rollback: restore `hidden` attribute.

#### Step 3: R1 — Surface primary filters outside collapsed disclosure (high)

* Source: `26:R1` (high) — `web/templates/_roster_tool.html:14` `details.more-filters` closed, `view-toggle hidden`, live `/` shows filters hidden, blocks narrowing a 1,145-person roster.
* Why third: highest task friction on the hero surface, users type names only and miss charge-level filtering.
* Touches: `web/templates/_roster_tool.html:14-54` (surface `Charge level` (`#filter-tier`) outside the disclosure on desktop or relabel `summary` to `Filters (charge, offense, sort)`, keep `hidden` toggles as progressive-enhancement fallback), `web/templates/index.html:roster_preview` (no data change, markup only), `web/static/style.css` (responsive rule for the surfaced control).
* Test pin: `tests/test_roster_tool.py::test_charge_level_visible_without_opening_filters` (rendered HTML has `#filter-tier` outside `details.more-filters` or the `summary` text contains the affordance string), `tests/test_roster_tool.py::test_filter_disclosure_still_renders` (the `details` still exists for mobile/JS-off).
* Verification: `python -m web.build`, `grep -n filter-tier docs/index.html` shows the control outside the `details`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep -c more-filters` plus visual check.
* Effort: S
* Rollback: move the control back inside the `details`.

### Phase 2 — Stability (medium leverage)

#### Step 4: R4 — Make the roster preview/archive split explicit

* Source: `26:R4` (med) — `web/templates/index.html:roster_preview`, live `/` vs `/archive/`, only `Earlier bookings` chip and noscript line explain the split.
* Touches: `web/templates/index.html` (add `Showing 48 most recent of {{ snapshot.inmate_count }} — Browse all` above the preview plus a sticky `View all {{ snapshot.inmate_count }}` control when `roster_preview` is true), `web/templates/_roster_tool.html` (no logic change).
* Test pin: `tests/test_index_preview.py::test_preview_banner_states_counts` (when `roster_preview` is true, rendered HTML contains both the preview count and the total count and a link to `/archive/`).
* Verification: `python -m web.build`, `grep -c 'View all' docs/index.html`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep -i 'most recent'`.
* Effort: S

#### Step 5: N1 — Promote reference pages to a visible desktop top bar

* Source: `26:N1` (med) — `web/templates/base.html:48-53` drawer `details.nav-menu`, `web/templates/_nav_groups.html`, direct access to `/statute/`, `/bond-schedule/`, `/court/` requires opening the drawer.
* Touches: `web/templates/base.html:38-66` (add a `desktop-only` top bar with `/archive/`, `/statute/`, `/bond-schedule/`, `/data/`, keep the drawer for mobile), `web/static/style.css` (top-bar layout, `display:none` below breakpoint), `web/templates/_nav_groups.html` (no duplication, drawer remains canonical for mobile).
* Test pin: `tests/test_nav.py::test_desktop_top_bar_links` (rendered `docs/index.html` contains top-bar anchors to the four reference pages with `aria-current` handling).
* Verification: `python -m web.build`, `grep -c 'top-bar' docs/index.html`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep top-bar` (desktop) plus mobile drawer still works.
* Effort: M

#### Step 6: R2 — Tier strip legend and keyboard affordance

* Source: `26:R2` (med) — `web/templates/_roster_tool.html:58-63` `tier-strip-slim role=img` 4px, non-interactive, `aria-label` carries `F1 202 · F2 200 · M1 298` but no keyboard target.
* Touches: `web/templates/_roster_tool.html:56-63` (add a text legend adjacent to the strip or make segments focusable buttons that set `#filter-tier`, keep the 4px bar as visual echo), `web/static/main.js` (segment click sets the tier filter), `web/static/style.css` (legend spacing).
* Test pin: `tests/test_roster_tool.py::test_tier_strip_legend_present` (rendered HTML has a legend with degree counts adjacent to `tier-strip-slim` or tier segments are `<button>` with `aria-label`).
* Verification: `python -m web.build`, `grep -c tier-strip docs/index.html`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep tier-strip`.
* Effort: S

#### Step 7: R3 — Search placeholder and ORC explainer link

* Source: `26:R3` (med) — `web/templates/_roster_tool.html:11` placeholder `Name, charge, or ORC code`, `web/templates/_card.html:data-search`, ORC explainers live on `/statute/` not on cards.
* Touches: `web/templates/_roster_tool.html:10-12` (annotate placeholder `Search — try a name or ORC 2913.02`, link the empty state to `/statute/#orc-2913-02`), `web/templates/_roster_tool.html:73-78` (empty-state link, see R7).
* Test pin: `tests/test_roster_tool.py::test_search_placeholder_mentions_orc_example` (placeholder contains `ORC` and an example code and the empty state contains a link to `/statute/`).
* Verification: `python -m web.build`, `grep -c 'ORC 2913' docs/index.html`; `python -m pytest -q`.
* Effort: S

#### Step 8: D2 — Photo fallback caption

* Source: `26:D2` (med) — `web/templates/inmate.html` `figure.record-photo is-placeholder`, live `/inmate/1777439/` `data-initials` `data-photo-fallback`.
* Touches: `web/templates/inmate.html` (render `Photo unavailable from source` text adjacent to the placeholder when the HCSO file is absent, keep initials as visual fallback), `web/templates/_card.html` (no change, card placeholder stays `data-initials` only).
* Test pin: `tests/test_inmate_photo.py::test_placeholder_renders_caption` (when `photo_filename` is absent, rendered inmate HTML contains the caption string).
* Verification: `python -m web.build`, `grep -c 'Photo unavailable' docs/inmate/*/index.html` for a fixture id; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/inmate/1777439/ | grep -i 'Photo unavailable'` when applicable.
* Effort: S

#### Step 9: R7 + a11y-F5 — Empty filter state with contextual help and `role=status`

* Source: `26:R7` (low) + `26:ledger#11` + `00_index:a11y-F5` — `web/templates/_roster_tool.html:73-78` `#filter-empty` `role=status` hidden, polite guidance but no suggestion to widen the query.
* Touches: `web/templates/_roster_tool.html:73-78` (add contextual help `Try clearing Charge level` when `#filter-tier` is active and `Try a last name only` when the query contains a space, ensure `role=status` plus `aria-live=polite` so SR users hear it), `web/static/main.js` (contextual text swap).
* Test pin: `tests/test_filter_empty.py::test_filter_empty_has_status_and_context` (rendered HTML has `#filter-empty` with `role=status` and `aria-live`, JS path tested via `test_filter_empty.py` or `test_roster_tool.py`).
* Verification: `python -m web.build`, `grep -c 'filter-empty' docs/index.html`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep filter-empty`.
* Effort: S

#### Step 10: a11y-F2 — Search combobox demotion and keyboard

* Source: `00_index:a11y-F2` (high), `26:ledger#6` `aria-controls=search-results` + `role=region hidden` — combobox pattern is incomplete (no `aria-activedescendant`, no arrow keys, stray child inside `role=listbox`).
* Touches: `web/templates/_roster_tool.html:10-12` (demote to `type=search` with `role=combobox` only if listbox semantics are complete, else plain search with `aria-controls`, remove stray child inside `role=listbox`), `web/static/main.js` (arrow-key handler, `aria-activedescendant` sync).
* Test pin: `tests/test_a11y_search.py::test_search_has_valid_combobox_or_plain_search` (either valid combobox with `aria-activedescendant` and listbox children are all `role=option`, or plain search without combobox role).
* Verification: `python -m web.build`, rendered `docs/index.html` diff; `python -m pytest -q`; axe-core or manual arrow-key test.
* Effort: M

#### Step 11: a11y-F3 — Tier badge tooltip via `aria-describedby`

* Source: `00_index:a11y-F3` (med), `26:ledger#10` tier corner `tabindex=0` without button semantics — `web/templates/_card.html` tier-corner, `web/templates/base.html:107` `#tier-tip`.
* Touches: `web/templates/_card.html` (tier corner becomes `<button>` with `aria-describedby="tier-tip"` or the tip body is exposed via `aria-describedby`), `web/templates/base.html` (`#tier-tip` with `role=tooltip`).
* Test pin: `tests/test_a11y_tier.py::test_tier_badge_describedby` (tier badge has `aria-describedby` pointing at `#tier-tip` and the tip contains the human-readable tier text).
* Verification: `python -m web.build`, `grep -c tier-tip docs/index.html`; `python -m pytest -q`.
* Effort: S

### Phase 3 — Quality and trust/chrome polish

#### Step 12: R5 — Sort control adjacent to the list header

* Source: `26:R5` (low) — `web/templates/_roster_tool.html:23-30` `#filter-sort` inside `Filters`, invisible until opened.
* Touches: `web/templates/_roster_tool.html:23-30` (duplicate or move sort adjacent to the card count/list header, keep the `Filters` copy for mobile parity, both drive the same `data-filter` handler), `web/static/main.js` (bind the duplicated control to the existing handler).
* Test pin: `tests/test_roster_tool.py::test_sort_control_at_list_header` (rendered HTML has a sort control outside `details.more-filters` adjacent to the list header and it shares the `#filter-sort` handler).
* Verification: `python -m web.build`, `grep -c filter-sort docs/index.html` >= 2 or header-adjacent; `python -m pytest -q`.
* Effort: S

#### Step 13: R6 — Reset affordance without JS gate

* Source: `26:R6` (low) — `web/templates/_roster_tool.html:38-42` `Reset filters` and `Table view` ship `hidden`.
* Touches: `web/templates/_roster_tool.html:38-42` (render reset as a link to `/archive/` without JS, reveal via JS adds progressive enhancement rather than gating), `web/static/main.js` (enhance the link into a filter-reset button when JS is present).
* Test pin: `tests/test_roster_tool.py::test_reset_renders_as_link_without_js` (rendered HTML has a `Reset` link to `/archive/` that is not `hidden` before JS).
* Verification: `python -m web.build`, `grep -c 'Reset filters' docs/index.html`; `python -m pytest -q`.
* Effort: S

#### Step 14: Statute polish — S2 + S3

* Source: `26:S2` (low) `details.statute-item` only first open, no expand-all; `26:S3` (low) `codes.ohio.gov` target blank without affordance — `web/templates/statute.html`.
* Touches: `web/templates/statute.html` (add `Expand all · Collapse all` controls that toggle `details[open]`), `web/static/main.js` (persist `statute-expanded` in `localStorage`), `web/static/style.css` (external-link indicator via CSS and `aria-label` suffix `opens codes.ohio.gov` on `a.orc-code`).
* Test pin: `tests/test_statute.py::test_statute_expand_all_controls` (rendered HTML has expand/collapse controls), `tests/test_statute.py::test_orc_links_have_external_affordance` (ORC links have `rel=noopener` and the external indicator class/label).
* Verification: `python -m web.build`, `grep -c 'Expand all' docs/statute/index.html`; `python -m pytest -q`.
* Effort: S

#### Step 15: Navigation polish — N2 + N3 + C1

* Source: `26:N2` (low) `month-nav` horizontal scroll without overflow affordance, `26:N3` (low) three nav surfaces duplicate, `26:C1` (low) `brand` lockup without one-line purpose — `web/templates/base.html:38-66`, `web/templates/_nav_groups.html`, `web/templates/_more_reference.html`, `web/templates/base.html:footer-links`.
* Touches: `web/templates/base.html:55-66` (`month-nav` gets `scroll-snap` plus left/right fade and `role=navigation` that announces overflow, keep `Earlier bookings` terminus always visible), `web/templates/base.html:78-108` + `web/templates/_more_reference.html` (designate the drawer as primary, demote the footer to `data`, `source`, `legal`, `rss`, remove the redundant strip on pages that already show the drawer), `web/templates/base.html:38-42` (`brand` subhead `Current public roster. Presumed innocent until proven guilty.` on `/` above the filter bar, see `web/templates/index.html:section-h`).
* Test pin: `tests/test_nav_polish.py::test_month_nav_has_overflow_affordance`, `tests/test_footer.py::test_footer_grouped`, `tests/test_index.py::test_brand_subhead_on_home`.
* Verification: `python -m web.build`, `grep -c month-nav docs/archive/index.html`, `grep -c 'Presumed innocent' docs/index.html`; `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/archive/ | grep month-nav`.
* Effort: M

#### Step 16: D3 — Presumption banner per-session dismiss

* Source: `26:D3` (low) — `web/templates/_legal_disclosure.html`, `web/templates/inmate.html` alert above the fold on every detail page.
* Touches: `web/templates/_legal_disclosure.html` + `web/templates/inmate.html` (collapse to a dismissible alert once per session with `localStorage` `presumption-dismissed`, persistent presumption text in the footer, keep the full language on `/data/`), `web/static/main.js` (dismiss handler).
* Test pin: `tests/test_legal_disclosure.py::test_presumption_dismissible` (rendered inmate HTML has a dismiss button with `aria-label` and the footer still contains the presumption sentence).
* Verification: `python -m web.build`, `grep -c 'presumed innocent' docs/inmate/*/index.html` still present in footer, alert has dismiss; `python -m pytest -q`.
* Effort: S

#### Step 17: Trust surfaces — C2 + C3

* Source: `26:C2` (low) footer legal block four dense paragraphs plus nine links in one cluster, `26:C3` (low) `generated-stamp` in footer below external links and `running desktop-only` in masthead — `web/templates/base.html:45` `desktop-only`, `web/templates/base.html:85-90` `page_generated_utc`.
* Touches: `web/templates/base.html:78-108` (group footer into `Data & access`, `Legal`, `Project` columns, keep the four paragraphs but separate them visually), `web/templates/base.html:45` + `web/templates/index.html:section-h` (show `Updated Sep 23, 7:35 PM ET` adjacent to the result count on all viewports, keep the footer vintage as archival copy, remove `desktop-only` from the running count or duplicate it at the list header).
* Test pin: `tests/test_footer.py::test_footer_grouped_columns`, `tests/test_vintage.py::test_vintage_adjacent_to_count` (rendered index/archive HTML has a vintage `<time datetime>` adjacent to the count, not only in the footer).
* Verification: `python -m web.build`, `grep -c generated-stamp docs/index.html` shows two vintages (header-adjacent + footer); `python -m pytest -q`; live `curl -s https://www.aretheyinjail.com/ | grep -c '<time datetime'`.
* Effort: S

#### Step 18: a11y-F6..F8 + a11y-F4 carryover

* Source: `00_index:a11y-F6` statbar list semantics, `a11y-F7` duplicate recent-activity anchors, `a11y-F8` dispatch-map fallback link, `a11y-F4` closed (verify no other `<time>` lacks `datetime`) plus `00_index` phase 3 item 20.
* Touches: `web/templates/index.html` / `web/templates/stats.html` (`.statbar` rows as `<ul>/<li>` or `role=list`/`role=listitem`), `web/templates/_card.html` / `web/templates/index.html:recent-activity` (group duplicate thumb+name anchors with one labelled link), `web/templates/data.html` or `web/templates/_dispatch_map.html` (dispatch-map JS-off fallback is human-readable, not a raw `dispatches.json` link), sweep of all `<time>` elements to ensure `datetime` is present.
* Test pin: `tests/test_a11y_polish.py::test_statbar_has_list_semantics`, `tests/test_a11y_polish.py::test_recent_activity_single_anchor`, `tests/test_a11y_polish.py::test_time_has_datetime`.
* Verification: `python -m web.build`, rendered diff is minimal; `python -m pytest -q`; axe-core pass on `/`, `/archive/`, `/inmate/<id>/`, `/statute/`.
* Effort: M

### Phase 4 — Optional hygiene (rank 3, still in this plan)

These are not in the 18 but are required to close because optional does not mean skip when the edit is local. Each is small and lands after the user-visible rows so it does not compete for lift.

#### Step 19: Workflow and CI pin hygiene

* Source: `AUDIT-CONTRACT.md` productivity rank 3 and `00_index` deferred, this plan includes them explicitly per instruction.
* What to do: inventory `*.yml` under `.github/workflows/` at tip (12 files), verify every `uses:` is on a pinned SHA with an ` # vX.Y.Z` comment, Node runtime is 22 (CI uses `actions/setup-node@8207627... # v7.0.0`, `node-version: 22`), no `Node 20` / unpinned / missing-config annotation remains, dead workflow names from memos are not re-added.
* Touches: `.github/workflows/ci.yml`, `lint.yml`, `pages.yml`, etc. only if a pin drifts; today all pins are on SHA and Node 22 so this step is verification plus a test that locks the contract.
* Test pin: `tests/test_publish_workflows.py` already asserts branch-serve; add `tests/test_workflow_pins.py::test_pins_are_sha` (every `uses:` is `@<40-hex>` with a version comment and `setup-node` is Node 22) if not already present.
* Verification: `python -m pytest -q`, `rg 'uses:' .github/workflows/` shows SHAs, `python -m ruff check .` green.
* Effort: S

#### Step 20: Feed and template hygiene

* Source: `26:ledger#5`/`ledger#12` preview vs archive counts, `26:S3` external affordance already covered, plus `00_index` css-F4..F8 low hygiene carried here as optional.
* What to do: (a) Cincinnati Open Data feed hygiene — warning-level feed misses stay warning (do not promote to write-blockers), collapse guards remain `warn` not `block` for feeds; (b) CSS hygiene — remove the invalid `details.month, details.coms { open: true }` rule if still present, dedupe tier hexes if duplicated, drop unused `--family`/`--danger-deep` only after `grep` against `docs/` proves dead; (c) RSS `guid` is not hash-stable — defer unless a feed churn bug is proven (out of scope).
* Touches: `web/static/style.css` (only the invalid-rule removal or var cleanup), `scraper/cincy_open.py` / `scraper/open_data_feeds.py` (no threshold change, warning-level only).
* Test pin: `tests/test_style.py::test_no_invalid_open_rule` (parse `style.css` and assert no `open: true`), existing feed tests stay green.
* Verification: `python -m web.build`, `diff -r docs/ docs.backup/` minimal; `python -m pytest -q`.
* Effort: S

## Cross-cutting test and build gates

Each PR must also satisfy these gates that audit 26 relies on:

* Deterministic build: `docs/data/transparency_metrics.json:computed_utc == data/current.json:generated_utc` and `freshness_hours == generated_utc - last_healthy_sweep_utc` (`tests/test_build_determinism.py`).
* Branch-serve publish: `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs` (sweep/rebuild build into `docs/` and commit `data/`+`docs/`).
* No Supabase in the Python pipeline (`tests/test_architectural_compliance.py`).
* Evidence log append-only: do not hand-edit `data/waf_block_log.json`.
* Live re-verify after merge: `curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc`, plus the surface-specific probe for that row (e.g. `/statute/` for S1, `/inmate/<id>/` for D1).

## What this plan archives or deletes

* `audit-output/ui-aesthetic-remediation-report-2026-09-22.md` stays an `ARCHIVED — not current` stub per `26:What the next agent must not reload`. Any future PR that contradicts a claim in that stub must replace the stub or add a new dated stub rather than leaving a long narrative that reads as current.
* No other dated `audit-output/` packet is current truth. Do not cite any file there without re-verifying against tip `main` and a live fetch of `/`, `/archive/`, `/statute/`, and `data/current.json`.
* Sweep cadence comments that still say 15-minute or hourly remain contradicted — source is `sweep.yml` `7,37 * * * *` with a 20-minute skip gate.

## Gates

Remaining human gate: none for this plan. Next work is code, one row per PR per the contract above. After each merge, re-fetch the live page or workflow file before closing the row.

## Method note

Plan anchored to tip `be62652f` plus live fetches on `2026-10-09` as documented in `audit/26_ui_ux_failures_2026-10-09.md`. No file under `audit-output/` dated before the tip was treated as current truth. No scrape of `courtclerk.org/data/` was performed. `AUDIT-CONTRACT.md` is the authority for productivity ranking and optional-does-not-mean-skip.
