# UI & UX Failures Audit — 2026-10-09

Tip SHA: `be62652f02f7ff0c12e970099c660eea0f692cdb` (2026-10-09T15:10:04Z)
Live `jcstream:generated-utc` fetched 2026-10-09: `2026-10-09T16:09:32Z` on `/`, `/archive/`, `/statute/`, `/data/`, `/transparency/`, `/inmate/1777439/`, `/help/`, `/visit/`, `/court/`, `/bond-schedule/` (branch-serve `build_type=legacy`, `style.css?v=a4227e7ee0`, `theme-init.js?v=1fb7517bcf`, `main.js?v=20dd7601d5`, deterministic `computed_utc == generated_utc`, `freshness_hours 0.0`, `inmate_count 1145`).

Live workflow inventory (tip tree, 12 files): `archive-evidence.yml`, `ci.yml`, `clerk_pra_packets.yml`, `codeql.yml`, `lint.yml`, `live-parity.yml`, `maintainer_case_ingest.yml`, `pages.yml`, `rebuild.yml`, `refresh_caselaw.yml`, `staleness-watchdog.yml`, `sweep.yml`. No dated `audit-output/` packet is current truth. Re-verify every claim against tip plus live fetches. `courtclerk.org/data/case_key.html` is not scraped.

## Claim ledger

| # | Claim | Source | Status | File changed |
|---|-------|--------|--------|--------------|
| 1 | Filter bar ships visible and JS enhances rather than gates | `web/templates/_roster_tool.html:1-3`, live `curl /` shows `#filters` plus `noscript` fallback `https://www.aretheyinjail.com/archive/` | verified | — |
| 2 | Tier, offense, activity, sort, and table view sit behind collapsed `details.more-filters` | `web/templates/_roster_tool.html:14-54` `details.more-filters` `summary Filters`, live `curl /` `more-filters` | verified | — |
| 3 | `tier-strip-slim` 4px degree strip is visualization only, not a control | `web/templates/_roster_tool.html:56-63` comment `visualization only; filtering is #filter-tier`, live `role="img" aria-label="Roster by most serious degree: F1 202 ..."` | verified | — |
| 4 | Statute jump bar `#statute-jump-bar` is `hidden` until JS reveals | `web/templates/statute.html:5-9`, live `curl /statute/` `<div class="filter-bar" id="statute-jump-bar" hidden>` | verified | — |
| 5 | Homepage shows roster preview (48 recent) and archive shows full roster (1155) | `web/templates/index.html:roster_preview`, live `/` `48 shown` hint and `/archive/` first card `data-tier` plus `chip-archive Earlier bookings` | verified | — |
| 6 | Search input `placeholder "Name, charge, or ORC code"` with `aria-controls="search-results"` but results container is `role="region" hidden` until JS | `web/templates/_roster_tool.html:10-12`, live `curl /` `aria-controls="search-results"` and `role="region"` | verified | — |
| 7 | Table view toggle `#view-toggle` ships `hidden` and JS unhides | `web/templates/_roster_tool.html:38-41` `hidden`, `web/static/main.js` view-toggle | verified | — |
| 8 | `month-nav` chip rail and `chip-archive Earlier bookings` are the month jump affordance | `web/templates/base.html:55-66`, live `curl /` and `/archive/` `month-nav` `chip-archive` | verified | — |
| 9 | Inmate detail lightbox `#lb` does not trap Tab and does not inert background (a11y-F1) | `web/templates/base.html:107-115` `#lb role=dialog aria-modal hidden`, `audit/00_index.md:a11y-F1` | verified | — |
| 10 | Tier corner badge is `tabindex="0"` without button semantics and tooltip body never reaches AT | `audit/00_index.md:a11y-F3`, `web/templates/_card.html` tier-corner | verified | — |
| 11 | `#filter-empty` empty state toggles `hidden` but relies on `role="status"` alone without polite assertive | `web/templates/_roster_tool.html:73-78`, `audit/00_index.md:a11y-F5` | verified | — |
| 12 | Per-month sections are `<details class="month" id="m-*">` collapsed by default except first | `web/templates/_roster_tool.html:82-93`, live `curl /archive/` `<details class="month" id="m-october-2026" open>` | verified | — |
| 13 | Photo fallback renders initials via `data-initials` and `data-photo-fallback` when booking photo missing or corrupt | `web/templates/_card.html`, live `curl /inmate/1777439/` `data-initials="AK" data-photo-fallback` | verified | — |
| 14 | Footer vintage is anchored to `generated_utc`, not wall clock, via `<time datetime>` and `.generated-stamp` | `web/templates/base.html:86-90` `page_generated_utc`, live `Last updated: <time datetime="2026-10-09T16:09:32Z">` | verified | — |
| 15 | Statute page `197 sections` renders `details.statute-item` ladder plus `rb-grid`; ORC links point to `codes.ohio.gov` | `web/templates/statute.html`, live `curl /statute/` `statute-item-count` `orc-2925-11` | verified | — |
| 16 | Published vintage is deterministic: `docs/data/transparency_metrics.json:computed_utc == data/current.json:generated_utc` and `freshness_hours == generated_utc - last_healthy_sweep_utc` | `web/build.py` anchored via `set_build_now_from_utc`, live `curl /data/transparency_metrics.json` parity `0.0` | verified | — |

Contradicted claims: none in this run. Every claim above matches tip plus live fetches.

## Verified UI & UX failures as of 2026-10-09

Failures are grouped by surface. Severity reflects user impact on task completion, not code risk. Each item cites the live URL or tip file that proves it.

### 1 — Roster tools (homepage and archive)

| ID | Severity | Failure | Evidence | Impact | Fix direction |
|----|----------|---------|----------|--------|---------------|
| R1 | high | Primary filters hide behind collapsed `Filters` disclosure. Tier, offense, activity, sort, and table view require an extra click. First-time users do not discover them. | `web/templates/_roster_tool.html:14`, live `/` `details.more-filters` closed, `view-toggle hidden` | Blocks narrowing a 1,145-person roster. Users type names only and miss charge-level filtering. | Surface `Charge level` outside the disclosure on desktop, or label the disclosure `Filters (charge, offense, sort)`. Progressive enhancement keeps `hidden` toggles as fallback. |
| R2 | med | Tier strip `tier-strip-slim` is 4px tall, `role="img"` only, non-interactive. Visual weight is too low to convey `F1 202 · F2 200 · M1 298` share. Users assume it is a filter. | `web/templates/_roster_tool.html:58-63`, live `tier-strip-slim` `aria-label` carries numbers but no keyboard target | Users miss the roster composition cue. Screen reader users hear the `aria-label` but sighted users do not. | Add a text legend adjacent to the strip or make segments focusable buttons that set `#filter-tier`. Keep the 4px bar as visual echo. |
| R3 | med | Search placeholder `Name, charge, or ORC code` overpromises ORC recall. Typing `2913.02` filters `data-search` but ORC explainers live on `/statute/`, not on cards. | `web/templates/_roster_tool.html:11`, `web/templates/_card.html:data-search` | Users type a statute and see raw matches without context. Trust drops when the hit list looks arbitrary. | Annotate the placeholder `Search — try a name or ORC 2913.02` and link the empty state to `/statute/#orc-2913-02`. |
| R4 | med | Roster split is implicit. Homepage shows a preview, archive shows the full roster, but only the `Earlier bookings` chip and `Browse the complete current roster` noscript line explain it. | live `/` vs `/archive/`, `web/templates/index.html:roster_preview` | Users think the site caps at the first month. They do not click through to `Earlier bookings`. | Add `Showing 48 most recent of 1,145 — Browse all` above the preview plus a sticky `View all 1,145` control when `roster_preview` is true. |
| R5 | low | Sort control `#filter-sort` lives inside `Filters` (R1). `newest first / longest held / most serious / name A-Z` is invisible until opened. `Sort` affordance is not at the list header. | `web/templates/_roster_tool.html:23-30` | Users cannot re-rank without opening Filters. Table view users expect controls adjacent to the list. | Move sort adjacent to the card count or duplicate it as a list-header control that drives the same `data-filter` handler. |
| R6 | low | `Reset filters` and `Table view` ship `hidden` and appear only after JS. No-JS users have no reset affordance beyond browser back. | `web/templates/_roster_tool.html:38-42` | Keyboard and No-JS users cannot clear state without reload. | Render the reset as a link to `/archive/` without JS. Reveal via JS adds progressive enhancement rather than gating. |
| R7 | low | Empty filter state is polite guidance but visually quiet. `#filter-empty` reads `No one in custody matches that filter.` plus `Get free help` and HCSO source link, but no suggestion to open `Filters` or widen the query. | `web/templates/_roster_tool.html:73-78` | Users assume the roster is empty. They do not retry with broader filters. | Add contextual help: `Try clearing Charge level` when `#filter-tier` is active, and `Try a last name only` when the query contains a space. |

### 2 — Navigation and information architecture

| ID | Severity | Failure | Evidence | Impact | Fix direction |
|----|----------|---------|----------|--------|---------------|
| N1 | med | Drawer `details.nav-menu` is the sole global nav. Roster tools (7 links), Court reference (8), Site (3) live behind a hamburger with no persistent top-level tabs. Direct access to `/statute/`, `/bond-schedule/`, `/court/` requires opening the drawer. | `web/templates/base.html:48-53`, `web/templates/_nav_groups.html` | The site is a reference tool. Reference pages behave like hidden utilities. | Promote `/archive/`, `/statute/`, `/bond-schedule/`, `/data/` to a visible top bar on desktop. Keep the drawer for mobile. |
| N2 | low | `month-nav` chip rail is horizontal scroll on mobile. No overflow affordance and no `aria-label` direction hint beyond `Jump to month`. Chips wrap only on very narrow viewports. | `web/templates/base.html:55-66`, live `/archive/` `month-nav-inner` | Users do not realize the rail scrolls. Older months are offscreen without a scroll cue. | Add `scroll-snap` plus left/right fade and `role="navigation"` that announces overflow. Keep the `Earlier bookings` terminus always visible. |
| N3 | low | Three nav surfaces duplicate each other: drawer groups, `More` reference strip, and footer links. Active state sync lives on the drawer alone (`active_nav`). | `web/templates/_nav_groups.html`, `web/templates/_more_reference.html`, `web/templates/base.html:footer-links` | Users see the same link cluster in three densities without a clear primary. | Designate the drawer as primary and demote the footer to `data`, `source`, `legal`, `rss`. Remove the redundant strip on pages that already show the drawer. |

### 3 — Detail pages (inmate profiles)

| ID | Severity | Failure | Evidence | Impact | Fix direction |
|----|----------|---------|----------|--------|---------------|
| D1 | high | Lightbox `#lb role=dialog aria-modal` does not trap Focus and does not `inert` the background. Tab cycles into the page behind the overlay. (Carryover `a11y-F1`.) | `web/templates/base.html:107-115`, `web/static/main.js:lightbox` | Keyboard and screen reader users read background content while the photo is modal. WCAG 2.4.3, 2.1.2 failure. | Add focus trap to `#lb` and set `inert` on `#main` plus `.masthead` while open. Return focus to `data-photo` trigger on close. |
| D2 | med | Booking photo fallback is initials in a `data-initials` span or `img data-photo-fallback`. No caption says the photo is unavailable from HCSO vs. withheld for privacy. | `web/templates/inmate.html`, live `/inmate/1777439/` `figure.record-photo` `is-placeholder` | Users assume a broken image. Trust cue is missing. | Render `Photo unavailable from source` text adjacent to the placeholder when the HCSO file is absent. Keep the initials as visual fallback. |
| D3 | low | Presumption-of-innocence alert is verbatim everywhere but sits above the fold on every detail page, pushing charges below the fold on mobile. | `web/templates/_legal_disclosure.html`, `web/templates/inmate.html` alert | Repeated exposure causes banner blindness and pushes the reason for the visit down. | Collapse to a dismissible alert once per session with persistent presumption text in the footer. Keep the full language on `/data/`. |

### 4 — Statute lookup

| ID | Severity | Failure | Evidence | Impact | Fix direction |
|----|----------|---------|----------|--------|---------------|
| S1 | high | Statute jump bar `#statute-jump-bar` is `hidden` until JS runs. Without JS the 197-section ladder requires scrolling and Find. | `web/templates/statute.html`, live `curl /statute/` `id="statute-jump-bar" hidden` | Core reference task fails offline or under script block. | Render a server-side `<form action="#orc-2913-02">` jump that JS enhances into live filtering. Do not gate the control behind JS. |
| S2 | low | `details.statute-item` ladder expanded by default only for the first offense. Other sections require per-section clicks. No expand-all control. | live `/statute/` `details.statute-item open` only on first | Comparability task across offenses requires N clicks. | Add `Expand all · Collapse all` controls that toggle `details[open]` and persist `statute-expanded` in `localStorage`. |
| S3 | low | ORC links jump to `codes.ohio.gov` target blank without an external-link affordance beyond `rel=noopener`. | `web/templates/statute.html` `orc-code` | Users do not anticipate a new tab. | Add an external indicator via CSS and `aria-label` suffix `opens codes.ohio.gov`. |

### 5 — System chrome and trust surfaces

| ID | Severity | Failure | Evidence | Impact | Fix direction |
|----|----------|---------|----------|--------|---------------|
| C1 | low | `brand` lockup is `JCStream — Hamilton County · Justice Center mirror` without a one-line purpose statement on first paint. Homepage hero relies on the roster list to explain the site. | `web/templates/base.html:38-42` | First-time visitors do not know the site is a roster mirror, not jail services. | Add a one-sentence subhead on `/` above the filter bar: `Current public roster. Presumed innocent until proven guilty.` |
| C2 | low | Footer legal block is four dense paragraphs plus nine links in one cluster. Legal notices compete with access and data links. | `web/templates/base.html:78-108` | Scanning cost is high. The access dashboard link drowns. | Group footer into `Data & access`, `Legal`, `Project` columns. Keep the four paragraphs but separate them visually. |
| C3 | low | `generated-stamp Last updated: <time datetime>` is in the footer below external links. Freshness is not adjacent to the roster count in the masthead on mobile (`.running.desktop-only`). | `web/templates/base.html:45` `desktop-only`, `web/templates/base.html:85-90` | Mobile users do not see the vintage adjacent to the list they are filtering. | Show `Updated Sep 23, 7:35 PM ET` adjacent to the result count on all viewports. Keep the footer vintage as archival copy. |

### 6 — Accessibility carryover from synthesized index

The synthesized index `audit/00_index.md` already lists structural accessibility failures verified in tip code. They remain open until a PR ships a fix.

| ID | Status on 2026-10-09 | Note |
|----|----------------------|------|
| a11y-F1 | open | Lightbox focus trap and `inert`. See D1. |
| a11y-F2 | open | Combobox `aria-activedescendant`, arrow keys, stray child inside `role=listbox`. See R6 search-results pattern. |
| a11y-F3 | open | Tier badge tooltip body not exposed via `aria-describedby`. |
| a11y-F4 | closed | `<time datetime>` is present on the vintage stamp since deterministic build. Verify no other `<time>` lacks it. |
| a11y-F5 | open | `#filter-empty role=status` without assertive announcement. |
| a11y-F6..F8 | open | Statbar list semantics, duplicate recent-activity anchors, dispatch-map fallback link. Lower severity. |

## Files changed

No source files are changed in this audit pass. Failures are documented above with evidence and fix direction. Each failure maps to a template or style file named in the Evidence column. A remediation PR should patch the file plus its readers (tests and any `audit-output/` stub that would otherwise read as current).

## What the next agent must not reload

- `audit-output/ui-aesthetic-remediation-report-2026-09-22.md` remains an `ARCHIVED — not current` stub. Re-verify every claim against tip `main` and `https://www.aretheyinjail.com` before citing it.
- Dated claims in prior chat summaries that describe `docs/` from an old snapshot rather than live fetches of `/`, `/archive/`, `/statute/`, and `data/current.json`.
- Sweep cadence comments that still say 15-minute or hourly. Source is `sweep.yml` `7,37 * * * *` with a 20-minute skip gate.

## Gates

Remaining human gate: none for this audit. Next work is code: pick one row per PR, patch the template or style, add or update the test that pins the behavior, archive any `audit-output/` packet the change contradicts, lint, then re-fetch the live page after merge before closing the row.

## Method note

Every row was re-verified against tip `main` at `be62652f` and live fetches on `2026-10-09` via `curl.exe -s https://www.aretheyinjail.com/` plus path probes for `/archive/`, `/statute/`, `/data/current.json`, `/data/transparency_metrics.json`, `/inmate/1777439/`, `/help/`, `/visit/`, `/court/`, `/bond-schedule/`. No file under `audit-output/` dated before the tip was treated as current truth. Contradicted claims would have required a file edit in this run. No claim was contradicted. No scrape of `courtclerk.org/data/` was performed.
