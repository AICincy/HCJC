# Roadmap

A living list. "Done" means shipped to the live site; "Ideas / parked" includes things that
were considered and **deliberately rejected** — keeping the reasoning so we don't relitigate.

## Done

- **Core pipeline** — HCSO scraper (parallel A–Z sweep, inline base64 photo extraction +
  downscale), `data/current.json` + `data/changelog.json`, the static site builder, the
  30-minute GitHub Actions cron, `docs/` committed and served by Pages.
- **Custom domain** — www.aretheyinjail.com (root-relative build + `CNAME` file + Enforce HTTPS).
- **Roster UX** — bookings grouped by month (`<details>`, first 3 open), compact cards with a
  corner FELONY/MISDEMEANOR ×N badge, a hover tooltip listing the charges, a vivid colour-coded
  primary-offense headline, "Crimes of <Month>" summary chips, tier/offense filters, a type-ahead
  search box (`search.json`), an "Earlier bookings" fold.
- **Inmate detail pages** — JSON-LD, legal header, bio `<dl>`, (small, floated) booking photo,
  full charges table with `codes.ohio.gov` links and a "tier is a label, not a finding" note,
  statute-frequency context, related inmates, candidate dispatch calls, comment-policy block
  (+ Giscus widget when configured).
- **Cincinnati Open Data** — CPD/CFD CFS (`qiik-bpks`), PDI Police CFS/CAD (`gexm-h6bt`), CPD
  Reported Shootings (`sfea-4ksu`), PDI Crime Incidents (`k59e-2pvf`); a probabilistic
  booking↔dispatch matcher (surfaced as "candidates", not identity); a homepage **map** of
  recent arrest/citation/report dispatches + reported shootings (Leaflet loaded lazily from a
  CDN with SRI + graceful fallback; points grid-clustered, no extra runtime dep).
- **ORC enrichment** — hand-curated `data/orc_offenses.json`; fine-grained offense categories
  (so murder ≠ simple assault) with severity-tracking colours; tier classification by degree
  suffix > ORC default > court venue.
- **Stats** — `/stats/` point-in-time aggregates; roster-size sparkline + last-N-days
  booked/released churn; daily `history.json`.
- **Feeds & indexes** — `feed.xml` + `booked.xml` (recent-booking-date filtered) + `released.xml`;
  `search.json`, `dispatches.json`, `history.json`; absolute-URL feeds with `atom:self`.
- **Legal language** — presumption of innocence + ORC § 149.43 authority + FCRA "not a consumer
  reporting agency" + non-affiliation on the homepage banner, inmate pages, and footer; a full
  "Legal notices" section on `/data/` (authority, removal & sealing, FCRA, purpose, no-fee,
  non-affiliation); ORC § 2953.32 noted "as amended"; rewritten charges-table and comment-policy
  notices. See **[[Legal]]**.
- **Hygiene / perf** — `SHA256SUMS` manifest; print stylesheet; content-hash CSS cache-busting;
  the **sweep health guard**; a single shared tier-badge tooltip + `content-visibility:auto` on
  cards (≈14 % off the homepage HTML); deferred map load; site-level OpenGraph card; `robots.txt`
  + `.well-known/security.txt` + `humans.txt`.
- **Crowdsourced corrections** — GitHub issue forms for data errors and for "case data"
  (`ingest_issue.py` → `data/courtclerk_cases.json`).
- **Scaffolds (awaiting owner-side setup)** — Giscus comments; the PRA email loop. See **[[Operations]]**.

## In flight / next

- Watch that the sweep health guard holds in practice (roster count stays stable; no spurious
  release wave).
- Whatever the owner picks next.

## Ideas / parked (with reasons)

- **Web3 / IPFS / Arweave / ENS / tokens** — *rejected.* Permanent/immutable storage directly
  conflicts with the no-archive ethic (records must be removable when HCSO removes them or a
  court orders sealing). The only thing adopted from that whole space was a `SHA256SUMS` manifest.
- **Scraping courtclerk.org / codes.ohio.gov** — *rejected.* Their `robots.txt` disallows it;
  we link, and curate the ORC lookup by hand.
- **Indexable / SEO'd pages, rich social previews per person** — *rejected.* The site is
  `noindex` and the social card is site-level only; we don't amplify individuals beyond what
  HCSO already publishes.
- **OG share image (a generated PNG card)** — parked; the text-only `summary` card is the right
  amount.
- **A `/recent/` page** — parked; the split RSS feeds + the homepage "Recent activity" widget +
  the per-month sections cover it.
- **`content-visibility:auto` everywhere / lazy-rendered collapsed months via `<template>`** —
  partially done (it's on the cards); going further would mean a JS-dependency for older-month
  expansion, which we avoid.
- **Service worker / PWA** — *rejected.* A stale cached jail roster would be misleading; the
  web manifest is `display: browser` deliberately.
