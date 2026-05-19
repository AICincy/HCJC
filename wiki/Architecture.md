# Architecture

JCStream is deliberately boring: a Python script turns a JSON snapshot into a folder
of HTML, and GitHub Pages serves the folder. No runtime backend, no database.

```
GitHub Actions cron (*/30)         .github/workflows/sweep.yml
   │
   ├─ scraper.sweep ───────────────▶ data/current.json   (the roster)
   │                                 data/changelog.json (booked/released/updated events)
   │                                 data/photos/<id>.jpg (downscaled booking photos)
   │
   ├─ scraper.cfs / cfs_pdi /───────▶ data/cfs_recent.json, data/cfs_pdi_recent.json
   │  shootings / incidents          data/shootings_recent.json, data/incidents_recent.json
   │
   ├─ web.build ───────────────────▶ docs/  (index.html, inmate/<id>/, stats/, data/,
   │                                          feed.xml + booked.xml + released.xml,
   │                                          search.json, dispatches.json, history.json,
   │                                          robots.txt, .well-known/security.txt, humans.txt,
   │                                          CNAME, .nojekyll, static/, photos/)
   │
   └─ git commit data/ docs/  ──────▶ branch  ──▶  GitHub Pages  ──▶  www.aretheyinjail.com
```

## The scraper (`scraper/`)

- **`sweep.py`** — the orchestrator. For each surname in `data/surnames.txt` (which is
  just **A–Z, 26 single letters** — HCSO's last-name search is a substring match, so 26
  letters cover the whole roster, deduped), it GETs the list page, parses rows, fetches
  the detail page for anyone new (or for everyone with `--refresh-known`), extracts and
  downscales the inline base64 booking photo, then diffs against the previous snapshot to
  produce `booked` / `released` / `updated` events. Runs ~32 workers in parallel.
  - **Sweep health guard:** `_sweep_looks_healthy(prev, seen, n_surnames, n_failed)` — if
    >10 % of surname fetches errored, or the roster collapsed below half of last cycle, the
    sweep keeps the last-good `current.json` and exits cleanly instead of writing a partial
    roster (which would churn the changelog with a spurious wave of releases then re-bookings).
- **`parsers.py`** — selectolax-based HTML parsing of the list and detail pages.
- **`photos.py`** — Pillow; re-encodes HCSO's inline image to a 250×312 JPEG.
- **`cfs.py` / `cfs_pdi.py` / `shootings.py` / `incidents.py`** — pull the four Cincinnati
  Open Data (Socrata) feeds. See **[[Data]]**.
- **`match.py`** — probabilistic time-window match between an inmate's booking and nearby CPD
  arrest/citation dispatch calls. It is **not** identity matching — it's surfaced on inmate
  pages as "candidate dispatch calls".
- **`orc.py`** — static lookup of common Ohio Revised Code criminal sections → `{title, degree}`,
  from `data/orc_offenses.json` (codes.ohio.gov's robots.txt forbids scraping, so this is hand-curated).
- **`courtclerk.py`** — URL builders only (courtclerk.org's robots.txt disallows `/data/`, so we
  link, never scrape).
- **`pra.py` / `pra_capias.py`** — optional SMTP public-records-request senders (dry-run until configured).
- **`ingest_issue.py`** — parses the crowdsourced "case data" GitHub issue form → `data/courtclerk_cases.json`.
- **`store.py`** — load/save `current.json` and `changelog.json`; `diff()` produces the change events.
- **`models.py`** — pydantic models (`Inmate`, `Charge` (nested), `ChangeEvent`, `Snapshot`, `ListRow`).
- **`client.py`** — the HCSO HTTP client (httpx; respects a polite User-Agent; 0 s crawl-delay per robots.txt).

## The site builder (`web/build.py`, `web/classify.py`, `web/shape.py`)

`build(out_dir)` (in `web/build.py`) loads `data/current.json` + `data/changelog.json` + the cfs
feeds, attaches dispatch candidates, builds a Jinja2 environment with a pile of template globals
imported from `web/classify.py` (offense categorisation, tier classification, regex helpers,
bond/date parsing) and `web/shape.py` (per-inmate display, the card data attributes, the per-card
tooltip payload, bond/age/court-date / snapshot-shape helpers), then renders:

- `index.html` — the roster: a legal banner, the headline count + sparkline, recent-activity
  cards, the dispatch map (`dispatches.json`, plotted with Leaflet loaded lazily from a CDN),
  the filter/search bar, then bookings grouped by month (`<details>` per month, first 3 open),
  plus the shootings/CPD-dispatch lists, and a collapsible "About JCStream" block.
- `inmate/<id>/index.html` — the detail page: JSON-LD, the legal header, a bio `<dl>`, the
  (small, floated) booking photo, the full charges table with `codes.ohio.gov` links and a
  "tier is a statutory label, not a judicial finding" footnote, statute-frequency context,
  related inmates, candidate dispatch calls, and the comment-policy block (+ Giscus widget if configured).
- `stats/index.html` — point-in-time aggregates of the current roster, plus a roster-size
  sparkline and last-N-days booked/released churn from `history.json`.
- `data/index.html` — the data & methodology page, including the full **[[Legal]]** notices.
- `feed.xml` / `booked.xml` / `released.xml` — RSS 2.0 (all changes / new bookings / releases).
- `search.json`, `dispatches.json`, `history.json` — see **[[Data]]**.
- `manifest.webmanifest` (display: browser, no PWA), `robots.txt`, `.well-known/security.txt`,
  `humans.txt`, `CNAME` (from `JCSTREAM_CNAME`), `data/SHA256SUMS`, `.nojekyll`.

## Hosting

GitHub Pages, Source = "Deploy from a branch → /docs". The build runs with
`JCSTREAM_SITE_BASE_URL=""` (so links are root-relative) and writes a `CNAME` file from
`JCSTREAM_CNAME=www.aretheyinjail.com`. Pushing `docs/` makes the change live within a
minute or two — no Actions deploy step is on the critical path. `JCSTREAM_SITE_URL` (or, by
default, `https://<JCSTREAM_CNAME>`) is the absolute origin used in the RSS feeds, the OG
tags and `security.txt`.
