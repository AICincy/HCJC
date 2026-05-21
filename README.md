# JCStream

[![roster updates: PAUSED](https://img.shields.io/badge/roster_updates-PAUSED-critical?style=for-the-badge)](#hcso-access-interruption-current)
[![cause: HCSO WAF block](https://img.shields.io/badge/cause-HCSO_WAF_block-red?style=for-the-badge)](audit/14_hcso_waf.md)
[![since: 2026-05-19](https://img.shields.io/badge/since-2026--05--19-red?style=for-the-badge)](data/waf_block_log.json)
[![evidence: logged](https://img.shields.io/badge/evidence-LOGGED-8B0000?style=for-the-badge)](data/waf_block_log.json)

> [!CAUTION]
> **Roster updates are PAUSED (since 2026-05-19).** The Hamilton County
> Sheriff's Office is blocking JCStream's automated access to its public inmate
> roster (HTTP 403). The counts and records shown are from the **last successful
> update and are not current.** JCStream documents this denial as Ohio Public
> Records Act (ORC § 149.43) evidence and does not evade it. Details:
> [HCSO access interruption](#hcso-access-interruption-current) and
> [`audit/14_hcso_waf.md`](audit/14_hcso_waf.md).

<img src="web/static/img/sheriff-waf.png" align="right" width="180" alt="Illustration of the Hamilton County Sheriff with a speech bubble: 'Sorry about that, we're allegedly blocking access to keep inmates safe from county residents who believe public records should be accessible to the public.'">

A near-real-time public-records mirror of the Hamilton County (Ohio) Justice Center
inmate roster, generated entirely from publicly-published Hamilton County Sheriff's
Office data under Ohio Revised Code § 149.43.

JCStream is a static site rebuilt every ~30 minutes by GitHub Actions. It
republishes only what `hcso.org` itself publishes for each currently-in-custody
person: name, inmate / booking number, booking date, sex, race, projected release
date, and the charge / bond / court-date table.

JCStream **mirrors** the public HCSO roster. When HCSO removes a person from their
public roster (release, sealing, transfer, error correction, etc.) JCStream removes
that record on its next run. There is no historical archive of released
individuals.

## Status

| Phase | Scope | State |
|---|---|---|
| P0 | Repo scaffold, scraper skeleton, static-site renderer, GH Actions cron | in progress |
| P1 | Surname-sweep + detail parser + booking-photo extraction + diff/prune | in progress |
| P2 | (Fallback) Public Records Act email loop to HCSO Media Relations | stubbed |
| P2.5 | Cincinnati Open Data feeds: CFS (`qiik-bpks`), PDI CFS/CAD (`gexm-h6bt`), Crime Incidents (`k59e-2pvf`), Reported Shootings (`sfea-4ksu`) + probabilistic match to inmates | done |
| P2.6 | courtclerk.org deep-link hyperlinks (zero scraping) on every inmate roster row + per-charge case summary link | done |
| P2.7 | ORC offense title enrichment (static lookup table; no scraping of `codes.ohio.gov`) | done |
| P2.8 | Public Records Act email loop to Clerk of Courts for daily new-capias roster (SMTP-enabled when secrets are set) | done |
| P2.9 | Manual case-data submission path: GitHub Issue template + ingest workflow | done |
| P3 | RSS feed, transparency dashboard, takedown form | partial (RSS done) |

### HCSO access interruption (current)

Since 2026-05-19, HCSO's WAF has blocked automated retrieval of the public
roster from the GitHub Actions runner IP (HTTP 403, and at times an HTTP 200
page with the results stripped out). The sweep's degraded-roster guard
(`sweep_looks_healthy` in `scraper/sweep_guards.py`) refuses to overwrite the
last-good roster with a partial or empty one, so the site stays stable but
stale; the homepage shows an interruption notice and the
[data page](https://www.aretheyinjail.com/data/#access) documents it.

JCStream's posture is to **document the denial, not evade it**:

- Every blocked cycle and every recovery is appended to
  [`data/waf_block_log.json`](data/waf_block_log.json): an append-only,
  hash-chained log capturing the HTTP status, response headers, a body sample,
  and the SHA-256 of the body. Run `python -m scraper.verify_block_log` to
  verify the chain (exit 0 intact, 1 broken).
- On a blocked cycle the runner egress IP is snapshotted against GitHub's
  published Actions ranges (`data/egress_evidence.json`), documenting that the
  blocked source is a GitHub IP.
- The `JCSTREAM_HTTP_PROXY` egress-proxy capability stays in the code but is
  deliberately unset; the persisting, documented block is the point.

The full diagnosis, the evidence-file schema, and the legal-record drafts (the
ORC § 149.43(B) request, an operator affidavit, a § 149.43(C) mandamus
petition, an off-platform capture runbook, and a counsel cover memo) live in
[`audit/14_hcso_waf.md`](audit/14_hcso_waf.md) through `audit/19`.

### courtclerk.org access policy

The Hamilton County Clerk of Courts publishes a `robots.txt` that disallows
`/data/`, plus a Cloudflare WAF that returns HTTP 999 to identified bots.
JCStream's position is:

1. **Hyperlinks are not scraping.** Every roster row deep-links to
   `courtclerk.org` with name+DOB pre-filled, and every charge with a
   case# links to the case summary. The visitor's browser does the work
   and passes any bot check themselves. JCStream never touches the host.
2. **PRA email loop (`scraper/pra_capias.py`) is the legal path** to
   bulk capias data. The Clerk's `robots.txt` governs automated web
   access only; ORC § 149.43 obligations apply regardless. Configure
   the SMTP secrets listed below and the daily workflow sends real
   electronically-transmitted requests.
3. **Manual case-data submission** at
   `.github/ISSUE_TEMPLATE/case-data.yml`. After a visitor passes the
   Clerk's bot check in their browser, they can paste the case JSON
   into a GitHub issue and an ingest workflow writes it into `data/`.

### SMTP secrets (only needed to enable the PRA email loops)

| Secret | Purpose |
|---|---|
| `JCSTREAM_PRA_SMTP_HOST` | SMTP relay hostname (e.g. `smtp.gmail.com`) |
| `JCSTREAM_PRA_SMTP_PORT` | Port (587 STARTTLS or 465 implicit TLS) |
| `JCSTREAM_PRA_SMTP_USER` | SMTP auth username (your sending email) |
| `JCSTREAM_PRA_SMTP_PASS` | SMTP auth password / app password |
| `JCSTREAM_PRA_FROM_EMAIL` | The `From:` address shown on requests |
| `JCSTREAM_PRA_TO_CAPIAS_EMAIL` | Override recipient for Clerk-routed capias requests (default: `HCAdmin@hamilton-co.org`) |
| `JCSTREAM_PRA_TO_PHOTOS_EMAIL` | Override recipient for HCSO booking-photo requests (default: `HCAdmin@hamilton-co.org`) |

### Verified public-records contacts

| Agency | Channel | Contact |
|---|---|---|
| Hamilton County (central records officer) | email | `HCAdmin@hamilton-co.org` |
| Hamilton County Clerk of Courts | web form | https://www.courtclerk.org/records-search/request-records/ |
| Hamilton County Clerk of Courts | phone | 513-946-5656 |
| Hamilton County Sheriff's Office | web form | https://www.hcso.org/public-records-requests/ |
| Hamilton County Sheriff's Office | phone | 513-946-6400 |

The Clerk and HCSO do not publish PRA email addresses. The county's central
records officer at `HCAdmin@hamilton-co.org` (statutorily designated public
records contact) is the only verified email channel and routes requests to
the appropriate department. JCStream's PRA workflow emails that address;
the user is responsible for setting up the SMTP secrets above.

### GitHub Pages setup (one-time)

The sweep workflow publishes the built site two ways so either Pages
configuration works:

1. **Recommended:** Settings → Pages → **Source: "GitHub Actions"**. The
   workflow's `deploy-pages@v4` step takes over and serves
   `web/_dist/` directly.
2. **Fallback:** Settings → Pages → **Source: "Deploy from a branch"** →
   Branch: `gh-pages` → `/ (root)`. The workflow force-pushes the built
   site to the `gh-pages` branch each run.

The `web/_dist/.nojekyll` marker is auto-created so GitHub does not try to
Jekyll-process the built HTML.

> **Note on booking photos:** HCSO embeds each current inmate's booking photo
> inline as base64 in the same `/inmate-detail/` HTML we already scrape — no
> additional requests, no auth, no separate URL. JCStream extracts that image,
> downscales it to ~250×312 (the user-facing display size on hcso.org itself),
> and stores it as a JPEG. The P2 PRA email loop is kept as a fallback only —
> it activates if HCSO ever removes the inline photo.

## Ethics & legal posture

- **Arrest is not conviction.** Every record carries that disclaimer.
- **We mirror, we don't archive.** Once a person is off the HCSO public roster
  they're off ours. Sealed / expunged orders (ORC § 2953.32) get honored on the
  next sweep automatically.
- **No commercial use, no removal fees.** Code is MIT, data is CC-BY-NC 4.0.
- **No CAPTCHA / WAF bypass.** We scrape only the unprotected public endpoints
  on `hcso.org`. We do not touch `courtclerk.org` (CAPTCHA-protected).
- **When blocked, we document rather than evade.** HCSO's WAF currently blocks
  our automated retrieval (see Current status). We preserve the last-good
  roster, record the denial as evidence, and leave the dormant
  `JCSTREAM_HTTP_PROXY` capability unset.
- **We obey `robots.txt`**: `User-agent: *  Crawl-delay: 10`.
- **We identify ourselves** in the `User-Agent` header.

This is a public-records transparency project. It is not legal advice, an arrest
database, or a "mugshot site."

## Architecture

```
GitHub Actions cron (*/30)
        │
        ▼
  scraper.sweep   ──▶  GET hcso.org/.../inmate-search/?last=<X>
        │                  (top-N surnames; respects Crawl-delay 10s)
        │                  parses rows → {inmate#, names, admit date}
        ▼
  scraper.detail  ──▶  GET hcso.org/.../inmate-detail/?id=<inmate#>
        │                  for each NEW inmate#
        │                  parses bio + charge table
        ▼
  data/current.json  +  data/changelog.json   (committed to repo)
        │
        ▼
  site.build  ──▶  site/_dist/  (static HTML + RSS)
        │
        ▼
  git commit + push  →  GitHub Pages auto-deploy
```

## Repo layout

```
.
├── scraper/
│   ├── client.py         HCSO HTTP client; rate limit; UA
│   ├── parsers.py        list + detail HTML parsers
│   ├── models.py         pydantic data types
│   ├── store.py          JSON read/write, diff, prune
│   ├── photos.py         downscale booking photos
│   ├── cfs.py            Cincinnati Open Data calls-for-service pull
│   ├── match.py          probabilistic CFS->inmate matcher
│   ├── sweep.py          orchestrator (entry point: python -m scraper.sweep)
│   └── pra.py            P2 stub: Public Records Act email loop
├── web/
│   ├── build.py          static site renderer (Jinja2)
│   ├── templates/
│   └── static/
├── data/
│   ├── current.json      authoritative current-roster snapshot
│   ├── changelog.json    last N change events (for the home page)
│   └── surnames.txt      US Census top surnames; one per line
├── tests/
└── .github/workflows/sweep.yml
```

## Running locally

```bash
python -m pip install -r requirements.txt
python -m scraper.sweep --surnames data/surnames.txt --max-surnames 5  # dry-run
python -m web.build
```

## Public Records Act statutory authority

Hamilton County Sheriff's booking records and adult booking photos are public
records under **ORC § 149.43**. The agency has a duty to produce them on request
within a reasonable time, with statutory damages of $100/day (capped at $1,000)
plus attorney fees under § 149.43(C)(2) for delayed response to a properly-served
written or electronic request.

In practice, HCSO already publishes both the structured booking data and the
booking photo on the public `/inmate-detail/` page (the photo is base64-embedded
in-page rather than at a separate URL). JCStream consumes that public page only.
The P2 PRA emailer is retained as a fallback in case HCSO ever stops embedding
the photo.

## License

- **Code:** MIT — see `LICENSE`.
- **Data (`data/`):** Creative Commons Attribution-NonCommercial 4.0
  (CC-BY-NC 4.0). Original records belong to the public; this mirror's
  arrangement of them does not authorize commercial republication.

## Contact / takedown

For corrections, sealing/expungement notifications, or any other concern, open an
issue against this repo. There is never a fee.
