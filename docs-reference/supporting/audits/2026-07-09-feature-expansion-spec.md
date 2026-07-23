# Feature expansion spec: 14 approved items in 4 packs

Date: 2026-07-09. Session: a0e62bc2-30d0-4eb5-8a8b-90af64fb7451 (local Claude Code session).
Status: awaiting owner review. Source: 32-idea brainstorm; owner selected all four offered packs.

This is a queue, not a phased plan. The 14 selected items plus one groundwork
step (C0) make 15 sequence slots. Each item is one logical change, one PR,
shipped and verified before the next starts (CLAUDE.md scope gate). Any item
can be dropped or reordered without affecting the others, except C1 and C2,
which depend on C0.

## Constraints honored by every item

| Constraint | Consequence |
| :-- | :-- |
| No-required-JS contract | Every JS feature ships hidden and is revealed by JS; the page works without it |
| No service worker (web/outputs.py decision: offline roster would mislead) | Nothing offline, no PWA behavior beyond the existing manifest |
| Single light theme | No new theme work; new colors come from existing tokens, AA-checked |
| Token aliasing prohibited | New CSS rules use literal token references, never alias tokens |
| Evidence-log isolation | Any new production writer with a data/-relative default path gets a conftest wrap before merge |
| Visual changes | Screenshot to the owner before the PR merges (headless Chromium flow) |
| Tests | python -m pytest -q green before every commit |

## Build order

| Seq | Item | Pack | Size |
| :-- | :-- | :-- | :-- |
| 1 | A1 sitemap.xml | Quick wins | S |
| 2 | A2 smart 404 page | Quick wins | S |
| 3 | A3 shareable filter URLs | Quick wins | S |
| 4 | A4 CSV export of filtered roster | Quick wins | S |
| 5 | C0 length-of-stay data groundwork | Stats | S/M |
| 6 | B1 per-record court-date .ics | Calendar | S |
| 7 | B2 subscribe-able docket calendar | Calendar | S |
| 8 | C3 age-band histogram | Stats | S |
| 9 | C4 booking rhythm chart | Stats | M |
| 10 | C1 length-of-stay distribution | Stats | M |
| 11 | C2 release-outcome rates | Stats | M |
| 12 | D2 feed freshness board | Transparency | S |
| 13 | D1 availability calendar strip | Transparency | M |
| 14 | D3 changelog ledger page | Transparency | M |
| 15 | D4 weekly digest | Transparency | M/L |

C0 sits at seq 5 so that if release-event duration stamping is needed, data
accrues while the calendar pack builds. C1 and C2 land late to maximize the
accrual window.

## Pack A: quick wins

### A1 sitemap.xml

New writer in web/outputs.py emitting docs/sitemap.xml: the static pages
(/, /stats/, /statute/, /court/, /courts/, /data/, /help/, /visit/,
/transparency/, /bond-disparity/) plus every /inmate/&lt;id&gt;/ page, lastmod =
generated_utc. Absolute URLs via the existing site-origin helper in
web/build.py. robots.txt gains a Sitemap: line. No template or CSS changes.
Tests: build into tmp, assert the file parses as XML, contains the inmate
URLs, and robots.txt references it.

### A2 smart 404 page

New template 404.html extending base.html; GitHub Pages serves /404.html for
any missing path natively. Content: record pages are removed when a person is
released or the record is sealed (legal-copy conventions apply, presumed
innocent framing), the standard roster search box (main.js already loads
site-wide and wires #search-box to search.json), and links to the roster,
changelog, and data page. Emitted by build like the other pages. Tests: build
emits docs/404.html containing the search box and the explanation copy.

### A3 shareable filter URLs

main.js apply() gains a write-back step: history.replaceState with a
querystring built from the active filters (search, chap, tier, recent),
omitting empties. The read side already exists (URLSearchParams pre-apply);
reset already clears the querystring. Uses the existing debounce so typing
does not spam history. No template changes. No-JS impact: none, URLs are an
enhancement. Verification: manual, via the local screenshot/eval flow
(repo has no JS test infra; keep the diff small).

### A4 CSV export of filtered roster

A button in the filter bar (ships hidden, revealed by JS, same pattern as
#view-toggle). On click, iterate cards not .is-filtered-out and download a
client-side Blob CSV named jcstream-roster-&lt;date&gt;.csv. Columns: name, booking
number, booked date, tier, degree, custody days, charges, record URL; sourced
from existing data-* attributes and card text. The data page's Published
Files section documents the columns in the same PR. Tests: build test for the
template hook; CSV behavior verified manually via the eval flow.

## Pack B: court calendar

### B1 per-record court-date .ics

New build-side module web/ics.py: make_ics(events) producing RFC 5545 output
(VEVENT per court date; UID from booking number + case + date; DTSTART with
TZID America/New_York; SUMMARY, LOCATION courtroom when present, DESCRIPTION
with case, charge, and record URL; correct comma/semicolon/newline escaping;
75-octet line folding). Build emits docs/inmate/&lt;id&gt;/court.ics for records
with upcoming events; inmate.html links it as "Add to calendar" next to the
court-date display. Tests: unit tests for escaping, folding, and timezone;
build test that a fixture record emits a parseable file.

### B2 subscribe-able docket calendar

Same writer emits docs/court-calendar.ics: every upcoming court event across
the roster for the next 30 days, sorted. court.html links it with a webcal
note: the feed regenerates each sweep and events disappear when people are
released. Tests: build test over fixtures, including the 30-day cutoff.

## Pack C: stats insights

### C0 length-of-stay data groundwork

Decision logic, resolved by inspecting data at build start:
1. If data/changelog.json retention holds matched booked and released event
   pairs (by inmate number) across a useful window, compute durations at
   build time from it. No scraper change.
2. Otherwise, stamp custody_days on released events at write time in
   scraper/store.py (the booking date is on the record being released) and
   add the same field to anon_changelog rows. Compaction group keys are
   unchanged; monthly summaries carry a mean of the field. Store writers are
   already conftest-wrapped; no new default-path writer is introduced.
Tests: store test for the stamped field; compaction idempotence with the new
field present and absent.

### C1 length-of-stay distribution

Build helper computing median, p75, p90 and a banded histogram of
booked-to-released durations by tier, from the C0 source. stats.html gains a
section using the existing statbar pattern. Honest empty state: "insufficient
data, window fills as releases accrue" until enough durations exist. Tests:
helper unit tests over synthetic durations; empty-state path covered.

### C2 release-outcome rates

Same C0 data: percent of releases within 24h, 72h, and 7 days, by offense
category (the existing 7-bucket rollup). Table plus bars on stats.html,
adjacent to C1. Tests: helper unit tests, boundary cases at exactly 24h/72h.

### C3 age-band histogram

Build helper bucketing current-roster ages from DOB (18 to 24, 25 to 34,
35 to 44, 45 to 54, 55 to 64, 65 plus; unknown DOBs excluded and counted in a
note). The 1/1/1970 sentinel exclusion already exists and is respected.
Renders next to the sex and race tables on stats.html. Tests: helper unit
tests including sentinel and missing-DOB exclusion.

### C4 booking rhythm chart

Weekday distribution of bookings from changelog booked events (booking date
is reliable). Hour-of-day is included only if the HCSO detail data carries a
booking time; verified during implementation, and if absent the chart ships
weekday-only with no placeholder. stats.html bar row. Tests: helper unit
tests over synthetic events.

## Pack D: transparency

### D1 availability calendar strip

Build helper folding waf_block_log.json periods and roster freshness into a
per-day status for the last 90 days: ok, stale, or blocked. Rendered on
transparency.html under the metrics table as a CSS-grid strip of day cells,
each with a title attribute carrying date and status; no JS. Colors reuse the
existing status-pill palette, AA-checked. Tests: helper unit tests over
synthetic ledgers (open period, recovered period, gap days, empty ledger).

### D2 feed freshness board

Build-time table on the data page Feeds section: feed name, row count, last
fetched (from each feed file's own generated stamp), and a staleness badge
relative to each feed's expected cadence. Tests: helper unit tests with
fixture feed files, including a missing file and a stale stamp.

### D3 changelog ledger page

New page /changelog/: day-grouped booked and released events within
changelog.json retention, named, in a compact row layout reusing existing
list styles; months older than retention link to the anonymized event log on
the data page. Takedown filtering is already applied at the source
(fail-closed in store and build). Tests: build test with fixture changelog,
including a takedown-filtered row that must not render.

### D4 weekly digest

New page family /digest/ (index) and /digest/&lt;iso-week&gt;/: net roster change,
top charges, court volume, access interruptions, and notable stat deltas for
each week within data retention. Weeks older than event retention render only
what history.json carries (counts). Largest item; sequenced last. Tests:
build test for one synthetic week plus the retention-degraded path.

## Explicitly out of scope

Items from the brainstorm the owner did not select: search operators,
did-you-mean, keyboard layer, watchlist, since-last-visit diff, faceted
counts, photos-off toggle, copy-citation button, QR dossier, case-stage
strip, charge co-occurrence, per-statute RSS, OpenSearch descriptor, count
badge, glossary, Spanish mirror, bond math widget, map time filter. Any of
these can be added later by number from the brainstorm table.
