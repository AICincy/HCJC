---
title: Product and UI/UX
reference_namespace: V1
status: approved
authority: v1-product
owner_repository: AICincy/HCJC
document_family: product
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-69
  relation: implements
  to: A-41
- from: V1-74
  relation: implements
  to: A-40
- from: V1-82
  relation: implements
  to: A-21
---

# Product and UI/UX

> **Authority:** Controls the descriptive reference for V1 routes, information hierarchy, visual system, interactions, responsive behavior, and accessibility.

V1 is a server-generated static civic-information interface enhanced by browser JavaScript. Its design prioritizes current roster search, source context, legal framing, public-data exploration, and access to practical resources.

## V1-65 Public Route Hierarchy

The builder renders the roster home page, individual inmate pages, statistics, data and methodology, statute, court, courts guide, bond disparity, visit, help, and transparency routes, together with RSS and machine-readable outputs.

**Implementation and verification references:** `web/build.py`, `web/templates/`, `tests/test_outputs.py`.

## V1-66 Shared Page Shell and Navigation

`base.html` provides metadata, skip navigation, masthead branding, source seals, current count, responsive disclosure navigation, shared footer, lightbox, tooltip container, and deferred JavaScript. Navigation links expose the principal statistics, court, statute, bond, visit, help, access, data, RSS, and repository destinations.

**Implementation and verification references:** `web/templates/base.html`, `web/static/style.css`, `web/static/main.js`, `tests/test_build.py`.

## V1-67 Roster Search and Filtering

The home page renders a roster search and filter bar that JavaScript enhances with text matching, selected record filters, match counts, reset behavior, query-derived tier selection, empty-state messaging, and match highlighting. A generated search index supplies lookup suggestions.

**Implementation and verification references:** `web/templates/index.html`, `web/static/main.js`, `web/build.py`, `tests/test_build.py`.

## V1-68 Roster Card and Table Views

Current records are rendered as responsive cards grouped by booking month. A JavaScript toggle applies a table-like presentation and persists the preference in `localStorage["jcs-view"]`; the original card representation remains the default and no-JavaScript view.

**Implementation and verification references:** `web/templates/_card.html`, `web/templates/index.html`, `web/static/main.js`, `web/static/style.css`.

## V1-69 Individual Custody Page

**Shared concept:** [A-41 Current Custody Status](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-41-current-custody-status).

An individual page presents source identity fields, custody dates, booking photo, charges, cases, bond and court context, severity and time ladders, peer comparisons, candidate dispatch calls, status history, source attribution, and legal framing.

**Implementation and verification references:** `web/templates/inmate.html`, `web/shape/inmates.py`, `web/shape/bond.py`, `web/shape/timeline.py`, `tests/test_build.py`.

## V1-70 Statistics and Context Pages

The statistics, bond, court, courts, visit, help, data, statute, and transparency pages provide aggregate measures, explanatory context, public resources, source methodology, and operational transparency beyond individual custody records.

**Implementation and verification references:** `web/templates/stats.html`, `web/templates/bond-disparity.html`, `web/templates/court.html`, `web/templates/courts.html`, `web/templates/visit.html`, `web/templates/help.html`, `web/templates/data.html`, `web/templates/transparency.html`.

## V1-71 Public Sans and IBM Plex Mono Typography

The stylesheet self-hosts Public Sans for interface and prose and IBM Plex Mono for identifiers, reference codes, numbers, and technical data. System fallbacks preserve the typographic roles when a font cannot load.

**Implementation and verification references:** `web/static/style.css`, `web/static/fonts/`, `tests/test_outputs.py`.

## V1-72 Warm Neutral Civic-Modern Palette

The implemented light theme uses `#F6F5F3` and `#FBFAF9` backgrounds, white surfaces, warm gray borders, near-black text, muted gray metadata, and `#B33A2A` as the principal signal color. The interface uses restrained borders, shadows, and radii rather than a dark-mode alternate.

**Implementation and verification references:** `web/static/style.css`, `audit/2026-05-14_compact-redesign-session.md`.

## V1-73 Severity and Category Color Systems

The stylesheet defines separate semantic tokens for case categories, offense categories, felony tiers, and misdemeanor tiers. Color is additive to labels, ordering, weight, and placement, and comments record contrast review for supported surfaces.

**Implementation and verification references:** `web/static/style.css`, `web/classify.py`, `audit/10_css_a11y_performance.md`.

## V1-74 Progressive Enhancement

**Shared concept:** [A-40 Progressive Enhancement](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-40-progressive-enhancement).

The base HTML remains navigable and content-complete without JavaScript. JavaScript adds search assistance, filters, highlighting, table view, lightbox behavior, tooltips, map interaction, and responsive navigation while retaining ordinary links and disclosure content as fallbacks.

**Implementation and verification references:** `web/static/main.js`, `web/templates/base.html`, `web/templates/index.html`.

## V1-75 Booking Photo Lightbox

A shared dialog opens normalized booking photos from restricted filenames, sets descriptive alternative text and captions, supports backdrop and Escape dismissal, confines focus, restores prior focus, and falls back to ordinary navigation when enhancement cannot open.

**Implementation and verification references:** `web/templates/base.html`, `web/static/main.js`, `web/static/style.css`.

## V1-76 Tooltips and Disclosure Navigation

Tier badges expose structured tooltips through `data-tip`, keyboard focus, `aria-describedby`, DOM-created text, and Escape dismissal. Hash navigation automatically opens a containing `details` element, and statute selection is revealed only when JavaScript can operate it.

**Implementation and verification references:** `web/static/main.js`, `web/templates/base.html`, `web/templates/statute.html`.

## V1-77 Responsive Behavior

The stylesheet provides desktop and small-screen layouts for masthead navigation, current-count placement, card grids, filters, tables, content panels, and page-specific sections. Mobile navigation uses a disclosure drawer while preserving its expanded no-JavaScript form.

**Implementation and verification references:** `web/static/style.css`, `web/templates/base.html`, `web/templates/index.html`.

## V1-78 Accessibility Behavior

**Shared concept:** [A-40 Progressive Enhancement](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-40-progressive-enhancement).

Implemented accessibility features include a skip link, semantic landmarks, descriptive labels, visible focus, keyboard-operable disclosures, dialog focus management, screen-reader text, accessible sparklines, reduced-motion support, structured tables and description lists, and non-color severity cues.

**Implementation and verification references:** `web/templates/base.html`, `web/static/style.css`, `web/static/main.js`, `audit/07_html_accessibility.md`.

## V1-79 Data, Statute, Court, Visit, and Help Information

Specialized pages combine project data with methodological explanations, statutory references, court logistics, visitation details, legal-help resources, sealing information, and contact routes. These pages form an informational layer around the current roster.

**Implementation and verification references:** `web/templates/data.html`, `web/templates/statute.html`, `web/templates/court.html`, `web/templates/courts.html`, `web/templates/visit.html`, `web/templates/help.html`.

## V1-80 Maps and Supplemental Public-Safety Views

The public interface presents selected Cincinnati Open Data material in textual panels and an on-demand Leaflet map. The map script is loaded for applicable content and uses generated dispatch data without becoming the sole route to the underlying information.

**Implementation and verification references:** `web/static/map.js`, `web/build.py`, `web/templates/index.html`, `tests/test_outputs.py`.

## V1-81 RSS and Machine-Readable Access

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

RSS links are advertised in the base page and dedicated feeds publish recent all-change, booking, and release activity. Public JSON files and checksum listings support programmatic inspection and independent verification.

**Implementation and verification references:** `web/templates/base.html`, `web/templates/feed.xml`, `web/build.py`, `tests/test_outputs.py`.

## V1-82 Content Language, Source Context, and Provenance

**Shared concept:** [A-21 Provenance](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-21-provenance).

Interface copy consistently identifies JCStream as an independent mirror, names HCSO and municipal sources, states the generation time, distinguishes allegations from convictions, and links methodology and legal notices.

**Implementation and verification references:** `web/templates/base.html`, `web/templates/data.html`, `web/templates/inmate.html`, `web/build.py`.
