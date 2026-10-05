# Bugfix Requirements Document

## Introduction

This document captures the current project status with known bugs and their fixes for the JCStream project (Hamilton County Justice Center inmate roster mirror). It serves as a status report documenting which major issues have been addressed and which remain open, using the bug condition methodology to systematically validate fixes and preserve existing functionality.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN detail page name heading is title-case (e.g., "John Doe") instead of all-caps THEN the system returns empty `last_name` and `first_name` fields with no warning

1.2 WHEN HCSO renames charge labels (e.g., "Description" → "Charge Description") THEN the system silently empties that field across all records with no warning

1.3 WHEN HCSO changes the inline photo placeholder width (e.g., 274px → 280px) AND no JPEG-SOI byte markers are present THEN the system displays zero photos site-wide with no granular signal

1.4 WHEN HCSO shifts detail page IDs from query-string (`?id=123`) to path-form (`/inmate-detail/123/`) THEN the system skips every list row with no recovery

1.5 WHEN detail page bio labels contain punctuation/digits (e.g., "Class #") THEN the system silently drops those fields from the bio dictionary

1.6 WHEN detail page produces zero structured fields AND it passes `raise_for_status()` THEN the system produces an empty Inmate record without per-record breadcrumbs

1.7 WHEN `KeyboardInterrupt` occurs mid-sweep THEN the system synthesizes a wave of bogus `released` events into the changelog by diffing partial current against full previous

1.8 WHEN snapshot load fails with corrupt `data/current.json` THEN the system swallows the error, returns `{}`, and the bootstrap floor accepts any small sweep as canonical

1.9 WHEN lightbox dialog is open AND user presses Tab key THEN the system moves focus to underlying page elements instead of cycling inside the dialog

1.10 WHEN search combobox is expanded AND user presses arrow keys THEN the system does not navigate options because `aria-activedescendant` is not implemented

1.11 WHEN tier badge is focused AND user hovers or focuses THEN the system shows tooltip visually but screen reader users hear only the short `aria-label`, not the longer `card_tip` body

1.12 WHEN filter results are zeroed by user search input THEN the system toggles `#filter-empty` visibility but screen reader users do not hear "No one in custody matches that filter"

1.13 WHEN HCSO returns 429 rate limit response THEN the system treats it as a hard failure that rolls into `n_failed` without honoring `Retry-After` header or retrying

1.14 WHEN Cincinnati Socrata schema changes AND all `where` clauses throw errors THEN the system catches broad `Exception`, logs debug, and falls back to unfiltered query of up to 5000/1000 rows

1.15 WHEN `scraper/client.py` docstring claims "Honors `Crawl-delay: 10` from robots.txt" AND `DEFAULT_CRAWL_DELAY = 0.0` AND workflow does not override it THEN the system behavior contradicts documentation

### Expected Behavior (Correct)

2.1 WHEN detail page name heading is title-case (e.g., "John Doe") instead of all-caps THEN the system SHALL extract name from `meta[property="og:title"]` fallback, then `<title>` fallback, then log debug breadcrumb

2.2 WHEN HCSO renames charge labels (e.g., "Description" → "Charge Description") THEN the system SHALL emit per-label coverage telemetry and warn when any high-prevalence label drops below 50% across sample

2.3 WHEN HCSO changes the inline photo placeholder width (e.g., 274px → 280px) THEN the system SHALL extract photo bytes using JPEG-SOI byte-marker fallback and log INFO when fallback fires

2.4 WHEN HCSO shifts detail page IDs from query-string to path-form THEN the system SHALL match both patterns with regex `r"(?:[?&]id=|/inmate-detail/)(\d+)"`

2.5 WHEN detail page bio labels contain punctuation/digits (e.g., "Class #") THEN the system SHALL accept labels matching `r"^\s*([A-Za-z][A-Za-z0-9 #/_-]*?)\s*:\s*(.*?)\s*$"`

2.6 WHEN detail page produces zero structured fields AND it passes `raise_for_status()` THEN the system SHALL emit `log.info("detail page produced no structured fields for id=%s", inmate_number)`

2.7 WHEN `KeyboardInterrupt` occurs mid-sweep THEN the system SHALL set `_clean_finish` flag only after full changelog append, preventing synthetic `released` wave from partial diff

2.8 WHEN snapshot load fails with corrupt `data/current.json` THEN the system SHALL return a sentinel (not `{}`), validate `schema_version`, and refuse to bootstrap degraded sweep

2.9 WHEN lightbox dialog is open AND user presses Tab key THEN the system SHALL either (A) set `inert` on all body children except dialog OR (B) cycle focus between close button and backdrop

2.10 WHEN search combobox is expanded AND user presses arrow keys THEN the system SHALL implement arrow-key navigation with `aria-activedescendant` updates OR demote to searchbox pattern without ARIA listbox semantics

2.11 WHEN tier badge is focused OR hovered THEN the system SHALL either (A) convert to `<button type="button">` with `aria-describedby="tier-tip"` that toggles on show/hide OR (B) drop the visual tooltip from AT tree

2.12 WHEN filter results are zeroed by user search input THEN the system SHALL add `role="status"` to `#filter-empty` so screen readers announce empty state change

2.13 WHEN HCSO returns 429 rate limit response THEN the system SHALL add 429 to retry branch with capped `Retry-After` honor (maximum 30 seconds)

2.14 WHEN Cincinnati Socrata schema changes AND all `where` clauses throw errors THEN the system SHALL narrow exception scope to `httpx.HTTPStatusError`, let `httpx.RequestError` propagate, and cap fallback limit

2.15 WHEN `scraper/client.py` docstring claims "Honors `Crawl-delay: 10` from robots.txt" AND workflow does not honor it THEN the system SHALL reconcile docstring and UA string to match observed behavior (parallelism-is-the-limiter reality)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN detail page name heading is all-caps with comma (e.g., "DOE, JOHN") THEN the system SHALL CONTINUE TO extract name from heading tier without fallback

3.2 WHEN HCSO charge labels match expected names (Description, ORC Code) THEN the system SHALL CONTINUE TO parse charges with same behavior as today

3.3 WHEN inline photo has 274px width hook AND valid base64 THEN the system SHALL CONTINUE TO extract photo bytes using preferred 274px selector

3.4 WHEN sweep is healthy with ≥50% roster fraction AND ≥70% names found THEN the system SHALL CONTINUE TO write current.json and append to changelog

3.5 WHEN detail page has proper HTML structure AND parsers succeed THEN the system SHALL CONTINUE TO produce Inmate records with bio, name, and charges

3.6 WHEN list row exists AND detail fetch fails THEN the system SHALL CONTINUE TO use list-row name fallback (`_fetch_one` at sweep.py:262)

3.7 WHEN sweep completes without interruption THEN the system SHALL CONTINUE TO diff current against previous, emit changelog events, and prune old photos

3.8 WHEN build process runs AND docs/ directory swap completes THEN the system SHALL CONTINUE TO preserve CNAME and explicitly preserved review file

3.9 WHEN search input receives focus AND user types THEN the system SHALL CONTINUE TO fetch suggestions from `search.json` and display autocomplete results

3.10 WHEN page renders AND JavaScript is enabled THEN the system SHALL CONTINUE TO lazy-load Leaflet map and render shooting/CFS lists below map

3.11 WHEN SMTP sends PRA emails AND dry-run mode is active THEN the system SHALL CONTINUE TO log `to`, `subject`, and message body without secrets

3.12 WHEN httpx client retries AND status is 5xx THEN the system SHALL CONTINUE TO retry once at 0.5s, then 1s with exponential backoff

3.13 WHEN `data/current.json` loads AND file has valid schema AND no corruption THEN the system SHALL CONTINUE TO validate against Pydantic model and return Inmate list

3.14 WHEN screen reader user navigates roster AND cards are rendered THEN the system SHALL CONTINUE TO announce name, charge, ID chip, and filter count with aria-live

3.15 WHEN crawler indexes published site AND noindex meta tags are present THEN the system SHALL CONTINUE TO respect noindex directive and exclude records from index