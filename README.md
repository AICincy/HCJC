# JCStream

[![CI](https://github.com/AICincy/HCJC/actions/workflows/ci.yml/badge.svg)](https://github.com/AICincy/HCJC/actions/workflows/ci.yml)

Static mirror of the Hamilton County (Ohio) Justice Center inmate roster.
Scrapes the public HCSO roster and Cincinnati Open Data feeds, then builds a
fully static, searchable site. No database server, no backend, no tracking.

- **Live site:** https://www.aretheyinjail.com
- **Source:** https://github.com/AICincy/HCJC (MIT)
- **Corrections, sealing, or removal:** https://github.com/AICincy/HCJC/issues - no fee, ever

## Status as of 2026-09-21

- **1,191 people** listed in custody, data current as of **2026-09-21T22:14:44Z**
  (data/current.json, docs/search.json, and docs/inmate/ all agree at 1,191;
  live site verified HTTP 200).
- Deploys from the tip of `main` via GitHub Pages. No commit hash is pinned
  here by design; the live commit is always the current `origin/main` tip.
  CI and the Pages build run green on every push to `main`.
- **137,797-record** append-only SHA-256 hash-chained WAF evidence log
  (docs/data/waf_block_log.json), chain verified in CI. The log lives in
  both `data/` (the sweep's working copy) and `docs/data/` (the published
  mirror); the two are byte-identical and CI asserts they stay that way.
- 702 tests, ruff and mypy clean (verified 2026-09-21).
- Deep-audit wave (2026-09-20): the 2 critical and 3 major findings were
  fixed fail-closed (corrupt evidence/changelog can no longer be silently
  replaced; detail-page blocks are deduped; outage probes use 3 roster IDs
  with a content-size recovery rule; the `-X ours` merge fallback is gone),
  plus all 16 minor findings (stale-ref fetch race, CI WAF presence guard,
  timestamp commit churn, `%y` pivot and offset-timestamp handling, UI label
  and timestamp fixes, canonical tags). See the audit report.
- Dark theme is live with a header toggle (persists via localStorage).
  Felony F1-F5 red-to-amber severity scale unchanged.
- 1,104 booking photos cached for 1,191 inmates; the gap is upstream
  photo-fetch failures during HCSO blocks, not pruning.

## How it works

### Data pipeline

1. **Sweep** (`scraper/sweep.py`): queries the HCSO inmate-search form with
   single-letter surname substrings (A-Z, configured in `data/surnames.txt`),
   dedupes rows, then fetches detail pages for new or stale profiles.
   - 16 worker threads, 0.5 s crawl delay per worker, polite User-Agent.
   - 20-minute skip-gate: a run does no network work if `data/current.json`
     is fresher than 20 minutes.
   - 22-minute orchestrator wall-clock cap; partial results are saved, never
     discarded (workflow timeout is 50 minutes).
   - WAF backoff tracker: exponential backoff starting at 2 s, capped at 30 s;
     Retry-After headers honored up to 30 s.
   - Safety guards reject the run before writing: roster collapse over 50%,
     surname-query failure rate over 10%, name-extraction watchdog breach, or
     photo pruning that would delete over 50% of the cache in one pass.
   - Rebooking rule: if a known inmate's list-row admit date differs from the
     stored booking date, the detail page is force-refetched so the newest
     booking photo wins. Corrupt fresh photo bytes never overwrite a good
     cached photo.
2. **Cincinnati Open Data** (same sweep run): calls for service (rolling
   30 days, 1 h cache), police CFS long-term feed, reported shootings
   (6 h cache), plus a supplemental registry (traffic stops, pedestrian
   stops, citizen complaints, use-of-force incidents). Collapse guards warn
   but never block the roster write.
3. **Dispatch-to-arrest correlation** (`scraper/correlate.py`): runs offline on
   local files, no network. 60-minute matching window, confidence floor 0.45.
   Candidate pairs only; join data is not shown on public profile pages.
4. **Case-law cache** (weekly, separate workflow): pulls Ohio appellate
   opinions via CourtListener for the top 30 ORC sections on the active
   roster. Sundays 06:00 UTC.
5. **Build** (`web/build.py`, Jinja2, sequential): compiles `docs/` -
   searchable index, per-inmate profile pages, stats, bond-disparity,
   safety, court/schedule views, statute directory, RSS/Atom feeds
   (`feed.xml`, `booked.xml`, `released.xml`), `search.json` client index,
   `robots.txt`, `CNAME`, `.well-known/security.txt`, and `SHA256SUMS`.

### Publishing

GitHub Pages publishes `docs/` from `main` on every push (the
"pages build and deployment" workflow). The custom domain is
www.aretheyinjail.com (`docs/CNAME`). Note for local builds: `docs/CNAME`
is only written when the `JCSTREAM_CNAME` env var is set; `web/build.py`
preserves it (and other non-generated files) across the output swap, so a
local build never deletes it.

### Evidence and integrity

- **WAF block log** (`docs/data/waf_block_log.json`): append-only, each row
  SHA-256-linked to the previous one. Verified by
  `scraper/verify_block_log.py` and re-verified in CI on every run. **Never
  edit, rewrite, or truncate this file by hand.** It is legal evidence, not
  a cache.
- **Change history**: `data/changelog.json` capped at 10,000 entries.
  `data/anon_changelog.json` scrubs names and IDs after 7 days and compacts
  entries older than 365 days into monthly summaries.
- **Egress evidence** (`data/egress_evidence.json`): runner IP recorded during
  blocks to show they target cloud execution infrastructure.
- **Freeze alarm**: if the roster goes stale past 6 hours, the sweep workflow
  opens (and dedupes) a GitHub issue automatically.

### Automation

| Workflow | Trigger | What it does |
|---|---|---|
| `sweep.yml` | cron `*/15 * * * *` (best-effort) | Full sweep: HCSO roster, open data, correlate, freeze check, build, commit to main |
| `ci.yml` | push / pull request | ruff, mypy (`scraper`, `web`), pytest, pip-audit, WAF-chain verify, smoke build from empty data, CNAME check |
| `refresh_caselaw.yml` | Sundays 06:00 UTC | Refresh `data/orc_caselaw.json` from CourtListener, commit if changed |
| `ingest_case_data.yml` | issue labeled `case-data` | Parse issue body into `data/courtclerk_cases.json` |
| `clerk_pra_packets.yml` | **manual dispatch only** | Build *draft* ORC 149.43 request letters as workflow artifacts. A human fills in the sender block and sends them. Nothing is sent or committed automatically. |
| `codeql.yml` | Tuesdays | CodeQL security scan |

**About the sweep schedule:** the cron fires every 15 minutes, but GitHub
Actions delivery is best-effort with observed gaps of 2-5 hours
(noted in `sweep.yml` itself). Observed 2026-09-21: runs landed at 06:17,
13:05, 18:39, 22:13 UTC (gaps of roughly 3.5-7 hours). The 20-minute
skip-gate means back-to-back runs never double-scrape. Treat "every 15
minutes" as the *schedule*, not the *delivery*.

## Tech stack

- Python >= 3.13 (CI matrix 3.13/3.14; workflows run 3.14)
- `httpx` (synchronous, thread-pooled - not async), `selectolax` (CSS-selector
  HTML parsing), `pydantic` 2 (record validation), `jinja2` 3 (templates),
  `Pillow` 12 (photo normalization)
- `ruff` (lint/format), `mypy` (type checks on `scraper` and `web`),
  `pytest` (702 tests as of 2026-09-21)

## Local development

```sh
git clone https://github.com/AICincy/HCJC.git
cd HCJC
python3.13 -m venv ~/workspace/.venvs/hcjc
~/workspace/.venvs/hcjc/bin/pip install -r requirements.txt
```

Run the test suite (the `TMPDIR` override matters: `/tmp` is a small tmpfs
on some hosts and pytest temp dirs can exhaust it):

```sh
TMPDIR=~/tmp-pytest ~/workspace/.venvs/hcjc/bin/python -m pytest -q
```

Build the static site (same `TMPDIR` caveat):

```sh
PYTHONPATH=. TMPDIR=~/tmp-pytest ~/workspace/.venvs/hcjc/bin/python web/build.py
```

Lint and type-check:

```sh
~/workspace/.venvs/hcjc/bin/ruff check .
~/workspace/.venvs/hcjc/bin/mypy scraper web
```

Verify the WAF evidence chain:

```sh
PYTHONPATH=. ~/workspace/.venvs/hcjc/bin/python -m scraper.verify_block_log
```

Run a sweep manually (hits the live HCSO site; be polite, keep defaults):

```sh
PYTHONPATH=. ~/workspace/.venvs/hcjc/bin/python -m scraper.sweep --help
```

Hard rules for local work:

- Do not hand-edit `docs/data/waf_block_log.json`. It is append-only
  evidence; breaking the SHA-256 chain invalidates the whole log.
- Do not delete `docs/CNAME`; the build preserves it locally.
- Sweeps commit to `main`, and Pages deploys `main`. Push only with approval.

## Legal and ethical posture

- **Basis (project's stated position):** the source records are kept by a
  public office. A requester's right to inspect and copy those records from
  the public office is governed by R.C. 149.43, which imposes duties on the
  public office or person responsible for public records. It does not license,
  restrict, or otherwise govern reuse of disclosed public-record facts by this
  independent project.
- **Mirror, not archive:** when HCSO drops a record, it drops off this site
  in the next update cycle. There is no public historical archive of
  released individuals (aggregated anonymized statistics are retained).
- **Presumption of innocence:** every profile and the site footer state that
  arrest is not conviction.
- **FCRA:** this site does not furnish consumer reports and is not offered as
  a consumer reporting agency as those terms are defined in 15 U.S.C. 1681a(d)
  and 1681a(f). Do not use the data as a factor in determining a person's
  eligibility for credit, insurance, employment, housing, tenant screening, or
  any other purpose described in 15 U.S.C. 1681b. FCRA coverage is determined
  by those statutory definitions, not by this notice.
- **No fee, ever:** corrections, sealing/expungement removals, and privacy
  requests are free. Open an issue.
- **No-index:** every page carries `<meta name="robots"
  content="noindex, noarchive">` and `robots.txt` disallows all crawling.
  Inmate pages expose only site-level OpenGraph tags, never per-profile
  social preview cards.
- **Document, don't evade:** when firewalls block the pipeline, the block is
  logged as evidence. No proxy rotation, no evasion.

## Key files

| Path | What it is |
|---|---|
| `data/current.json` | Active roster snapshot (1,191 inmates as of 2026-09-21) |
| `data/changelog.json` | Booking/release/change events, capped at 10,000 |
| `data/anon_changelog.json` | Anonymized long-term history (PII scrubbed after 7 days) |
| `docs/data/waf_block_log.json` | Append-only SHA-256-chained block evidence (137,797 records as of 2026-09-21) |
| `docs/data/SHA256SUMS` | Build checksums for data files |
| `docs/search.json` | Compressed client-side search index |
| `docs/inmate/` | Per-profile static pages (1,191 as of 2026-09-21) |
| `docs/photos/` | Normalized booking photos (1,104 as of 2026-09-21) |
| `scraper/sweep.py` | Sweep orchestrator |
| `scraper/client.py` | HCSO HTTP client (16 workers, 0.5 s delay) |
| `scraper/sweep_guards.py` | Health gates and WAF-stub detection |
| `scraper/freeze_alert.py` | 6-hour staleness alarm |
| `web/build.py` | Static site builder |

## Glossary

- **HCSO**: Hamilton County Sheriff's Office, the roster source.
- **ORC**: Ohio Revised Code.
- **PRA**: Public Records Act (ORC 149.43).
- **WAF**: Web Application Firewall; the layer that throttles or blocks
  automated requests from HCSO's side.
- **Skip-gate**: the 20-minute freshness check that lets a sweep run exit
  without scraping when data is already fresh.
- **Freeze alarm**: the 6-hour staleness threshold that files a GitHub issue.
- **Charge tier**: severity ranking (felonies F1-F5, misdemeanors M1-M4, then
  minor misdemeanor MM) used for sorting and color encoding.
- **Hash chain**: each evidence-log row embeds the SHA-256 of the previous
  row, making silent edits or deletions detectable.

## Internals (verified against the code 2026-09-20)

- **Detail-page name parser** (`scraper/parsers.py`): 5-tier fallback order --
  heading tags, `og:title`, container text, labeled cell, `<title>`.
- **Photo extractor** (`scraper/parsers.py`): prefers the photo URL, falls
  back to base64-decoded bytes; validates the JPEG start-of-image marker
  (`FF D8 FF`) because HCSO declares `image/png` but serves JPEG bytes.
- **Sentinel-date handling** (`web/classify.py`): HCSO's no-date sentinel is
  exactly `1/1/70` (Unix epoch 0) and is treated as unknown; `_display_date`
  additionally blanks dates more than 15 years in the past. Far-future dates
  are surfaced, not hidden (C-10). Two-digit years pivot per Python `%y`
  (69-99 to 19XX); dates more than a year in the future are rejected as
  data-entry garbage (C-5).
- **Court calendar** (`web/shape/court.py`): buckets are today / tomorrow /
  this_week / this_month; `_next_court_date` returns the earliest future
  charge date, falling back to the most recent past date (labeled "Last known
  court date" on profile pages, D-1).
- **Bond stats** (`web/shape/bond.py`): spread is the Q3/Q1 interquartile
  ratio; an individual's percentile is the fraction of peer bonds below
  theirs (`below / len(peers)`).
- **Clerk case matching** (`scraper/case_match.py`, `scraper/courtclerk.py`):
  charges carry `common_pleas_case` / `municipal_case` fields; there is no
  case-number-based court-category inference in the current code.
- **Dispatch geocoding** (`web/dispatch.py`): the CPD feed rows arrive with
  `latitude_x` / `longitude_x` columns already populated; the build maps them
  to compact `la`/`lo` keys for the homepage map. No address geocoding is
  performed locally.
- **Egress evidence** (`scraper/egress_ip.py`, gated on
  `JCSTREAM_CAPTURE_EGRESS=1`): on a block, snapshots the runner's egress IP
  and checks it against GitHub's published Actions IP ranges, recording
  `runner_ip_in_actions_range`.
- **Low-volume bypass** (`scraper/sweep_guards.py`): the name-extraction and
  detail-degraded watchdogs are bypassed below minimum sample counts
  (`DETAIL_WATCHDOG_MIN_SAMPLE`, `DETAIL_DEGRADED_MIN_SAMPLE`) so a
  first/tiny run is not failed by its own guards.
