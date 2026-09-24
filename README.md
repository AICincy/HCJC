# JCStream

[![CI](https://github.com/AICincy/HCJC/actions/workflows/ci.yml/badge.svg)](https://github.com/AICincy/HCJC/actions/workflows/ci.yml)

JCStream is a static public-records mirror of the Hamilton County, Ohio Justice Center inmate roster.

The repository has three main layers:

- scraper/ retrieves the HCSO roster and selected Cincinnati Open Data feeds, normalizes the records, and writes JSON source data under data/.
- web/ builds a static site from those JSON files. The request path is static: no application database is required to serve the public site.
- backend/ is a separate Node service that uses Supabase for authentication scaffolding. It is not used to render the public site.

The public site is searchable, publishes per-inmate pages while records remain on the source roster, exposes machine-readable JSON, and publishes aggregate history and operational evidence.

Live site: https://www.aretheyinjail.com

Source: https://github.com/AICincy/HCJC

Corrections, sealing, or removal requests: https://github.com/AICincy/HCJC/issues

License: MIT

## Architecture

### Scraper

The primary sweep entry point is:

    python -m scraper.sweep

It reads the surname list from data/surnames.txt, queries the HCSO inmate-search endpoint, deduplicates list rows, fetches detail pages for new or stale inmates, caches booking photos, and persists data/current.json plus change logs.

The HCSO client uses 16 worker threads, a 0.5 second per-worker crawl delay, one retry, and exponential WAF backoff capped at 30 seconds. The sweep also has health guards that keep the last-good roster when list or detail retrieval is materially degraded.

The sweep has a 20-minute freshness skip-gate and a 22-minute detail-phase wall-clock cap. The GitHub Actions workflow is scheduled hourly with cron 0 * * * *; GitHub Actions delivery is best-effort and can be much less frequent in practice.

The anonymized event feed is data/anon_changelog.json. It keeps identifying fields for seven days, then strips them and eventually compacts old rows into monthly summaries.

### Static build

The site builder is web/build.py and writes to docs/ by default.

A build produces the static site, per-inmate pages, search index, feeds, court/reference pages, transparency data, and published JSON under docs/data/.

The build is deterministic for committed inputs. It uses an output-directory swap and preserves CNAME plus the repository's explicitly preserved review file across that swap.

A local build changes tracked generated files, so use an alternate output directory when inspecting a build without intending to update docs/.

### Backend

The backend lives under backend/ and contains:

    GET /health

    GET /me

/health is unauthenticated. /me requires a verified user JWT through @supabase/server.

The backend does not define application tables or public-site rendering routes.

## Prerequisites

### Python

Python 3.13 or newer.

The CI matrix currently runs Python 3.13 and 3.14. The pinned project dependencies are:

    httpx==0.28.1
    selectolax==0.4.11
    pydantic==2.13.5
    jinja2==3.1.6
    defusedxml==0.7.1
    Pillow==12.3.0

Development tools are pinned separately:

    pytest==9.1.1
    ruff==0.16.7
    mypy==2.3.1

### Node.js

The backend declares Node >=20. Current CI uses Node 22. Use Node 22 locally to match CI and the current @supabase/server support baseline.

Required system tools for common workflows are:

- Git
- npm
- curl for shell-based HTTP checks and some operational scripts
- gh for scripts or runbooks that interact with GitHub through the CLI

No database is required for the public-site build.

## Installation and setup

### Python environment

From the repository root:

    git clone https://github.com/AICincy/HCJC.git
    cd HCJC
    python3.13 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    .venv/bin/pip install ruff==0.16.7 mypy==2.3.1

An editable development install is also supported:

    .venv/bin/pip install -e ".[dev]"

### Backend environment

    cd backend
    npm ci
    cp .env.example .env

The backend reads these variables:

    SUPABASE_URL
    SUPABASE_PUBLISHABLE_KEY
    SUPABASE_JWKS_URL
    SUPABASE_SECRET_KEY

The secret key is sensitive and must not be committed or logged. The variable name is documented in backend/.env.example; configure it through the deployment environment used for the backend.

Start the local backend with:

    npm run start:local

The default listener is http://0.0.0.0:8787. HOST and PORT can be set for local runs.

## Environment variables

The source tree reads the following deployment/runtime variables.

### Site build

    JCSTREAM_SITE_BASE_URL
    JCSTREAM_SITE_URL
    JCSTREAM_CNAME
    JCSTREAM_GISCUS_REPO
    JCSTREAM_GISCUS_REPO_ID
    JCSTREAM_GISCUS_CATEGORY
    JCSTREAM_GISCUS_CATEGORY_ID
    HCJC_TAB_FEEDS_DIR

JCSTREAM_CNAME controls the generated docs/CNAME value. The default tab-feed location is outside the repository under a sibling firecrawl-zips directory; set HCJC_TAB_FEEDS_DIR when those build inputs are stored elsewhere.

### Scraper

    JCSTREAM_USER_AGENT
    JCSTREAM_CRAWL_DELAY
    JCSTREAM_HTTP_PROXY
    JCSTREAM_CAPTURE_EGRESS

JCSTREAM_CAPTURE_EGRESS=1 enables the optional egress-IP evidence snapshot when the sweep records a block. JCSTREAM_HTTP_PROXY is an explicit proxy configuration; the project does not rotate proxies automatically to evade source-side blocks.

JCSTREAM_FORCE_SWEEP exists in scraper/sweep_skip.py, but the current scraper/sweep.py entry point implements its own freshness gate and does not consult that helper. Do not rely on JCSTREAM_FORCE_SWEEP to bypass the production sweep gate.

### GitHub automation

    GITHUB_TOKEN
    GITHUB_REPOSITORY

These are used by automation such as the freeze/staleness alert paths. ISSUE_BODY, ISSUE_NUMBER, ISSUE_SUBMITTER, and ISSUE_URL are consumed by the issue-ingestion workflow when GitHub supplies them.

## Usage

### Inspect sweep options

    .venv/bin/python -m scraper.sweep --help

Supported flags:

    --surnames PATH
    --max-surnames N
    --refresh-known
    --dry-run
    -v / --verbose

The default surname source is data/surnames.txt.

The current dry-run mode skips current.json/changelog persistence, but detail fetching can still write booking photos, and block evidence can still be appended. Treat it as an operational test mode, not a filesystem-free simulation.

### Run a limited sweep

A limited sweep still contacts the live HCSO service:

    .venv/bin/python -m scraper.sweep --max-surnames 3

Use the full surname file for a normal sweep:

    .venv/bin/python -m scraper.sweep

### Open Data feeds

List configured feeds:

    .venv/bin/python -m scraper.open_data_feeds --list

The main feed refresh commands are also available directly:

    .venv/bin/python -m scraper.cfs --help
    .venv/bin/python -m scraper.cfs_pdi --help
    .venv/bin/python -m scraper.shootings --help

The current defaults are 30 days of data for the CFS feeds, 30 days for reported shootings, one hour for the CFS cache, and six hours for the shootings cache.

### Static site build

For a local build without replacing the committed docs/ directory:

    .venv/bin/python -m web.build --out /tmp/hcjc-site

For the repository's normal generated output:

    JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME=www.aretheyinjail.com .venv/bin/python -m web.build

Be aware that web.build also updates data/history.json as part of the build.

If court-reference tab feeds are unavailable, the builder fails closed for those inputs and can render the affected sections empty while the overall build still exits successfully. Set HCJC_TAB_FEEDS_DIR to the directory containing the required feeds when they are available.

### Verify published JSON

The public-data verifier expects the repository root as source context and the generated site as the root being checked:

    .venv/bin/python scripts/verify_public_data.py --root /tmp/hcjc-site --source-root .

### Verify the WAF evidence chain

    .venv/bin/python -m scraper.verify_block_log

Do not hand-edit data/waf_block_log.json. It is a hash-chained evidence file.

### Summarize operational telemetry

    .venv/bin/python scripts/summarize_telemetry.py

### ORC enrichment

Normalize and inspect the current ORC catalog with:

    .venv/bin/python -m scraper.update_orc_offenses

The source catalog is data/orc_offenses.json. scraper/orc.py normalizes subsection-style inputs such as 2925.11A to the base section 2925.11 before lookup.

### Dispatch correlation

    .venv/bin/python -m scraper.correlate

This job is offline and writes its correlation output under the gitignored private/ tree.

### Court-law cache

scripts/refresh_caselaw.py is run by the scheduled GitHub Actions workflow. It refreshes the ORC case-law cache from CourtListener for the top active sections; it is not part of the normal sweep.

## Testing and validation

### Full test suite

    .venv/bin/python -m pytest -q

### Lint

    .venv/bin/ruff check .

### Type checking

The CI type-check target is:

    .venv/bin/mypy scraper web

Running bare mypy also checks scripts and tests and is therefore a broader check than the CI gate.

### Dependency audit

    .venv/bin/pip-audit -r requirements.txt

pip-audit is a CI tool; install it locally when you want to reproduce that gate.

### Syntax checks

Backend:

    cd backend
    npm ci
    node --check src/index.js

### Backend smoke test

The CI smoke contract is:

    SUPABASE_URL=https://ci-smoke.invalid.supabase.co     SUPABASE_PUBLISHABLE_KEY=ci-smoke-publishable-key     SUPABASE_JWKS_URL=https://ci-smoke.invalid.supabase.co/auth/v1/.well-known/jwks.json     npm run start:local

Then verify /health returns {"ok":true}. The smoke test does not require a real Supabase project.

### Test the repository build contract

The committed docs/ tree is generated output. Before replacing it, build to a temporary output and compare the generated tree with the checked-in tree.

### Test the remediation

The current anonymized-changelog remediation is documented separately:

    python deploy_fix.py -v

The deployment flow never pushes to GitHub. See README_DEPLOY.md for its safety gates and rollback behavior.

## Workflows

The primary GitHub Actions workflows are:

| Workflow | Trigger | Purpose |
|---|---|---|
| sweep.yml | hourly schedule plus manual dispatch | scrape, refresh feeds, correlate, build, commit generated data/docs, monitor source availability |
| ci.yml | push to main, excluding data/docs-only changes | main-branch verification: ruff, mypy, pytest, dependency audit, evidence verification, smoke/build checks |
| lint.yml | side-branch pushes and pull requests | fast ruff + pytest feedback |
| staleness-watchdog.yml | scheduled | independent freshness/freeze/deploy-staleness checks |
| pages.yml | secondary verified-artifact path | builds and deploys a Pages artifact; current live settings use branch serving |
| rebuild.yml | manual dispatch | rebuilds generated data/docs |
| refresh_caselaw.yml | scheduled | refreshes ORC case law |
| archive-evidence.yml | monthly | creates independently downloadable evidence archives |
| ingest_case_data.yml | issue workflow | ingests human-submitted court data |
| clerk_pra_packets.yml | manual dispatch | produces draft public-record request letters |
| codeql.yml | scheduled | security scanning |

The repository's current live Pages configuration serves the committed docs/ tree from the branch. pages.yml is a secondary verified-artifact deployment path, not the current source of truth for the live site.

## Data and privacy model

The source-of-truth files are under data/.

    data/current.json
    data/changelog.json
    data/anon_changelog.json
    data/takedowns.json
    data/orc_offenses.json
    data/history.json
    data/waf_block_log.json

current.json contains the active roster. changelog.json contains the recent rolling event history. anon_changelog.json keeps aggregate event information after seven days while removing identifying fields. takedowns.json is enforced at write boundaries so sealed records are not reintroduced by a scrape or changelog write.

The public site does not archive released individuals as profile pages. Long-term aggregate history is retained separately.

## Repository constraints

- Run sweep and build commands from the repository root unless a command explicitly documents another working directory.
- Do not hand-edit the WAF evidence log.
- Do not use proxy rotation or other mechanisms intended to evade source-side blocking.
- Do not use git add -A in automation that owns only a subset of generated files.
- Do not commit credentials or backend .env files.
- Treat data/ and docs/ changes as generated artifacts unless the task explicitly requires editing their source inputs.

## Legal and operational posture

The project mirrors public records and publishes a statement that an arrest is not a conviction. It is not intended to be a consumer reporting agency or a consumer report under the project's stated policy. Corrections, sealing, and removal requests are handled through the GitHub issue tracker.

When HCSO blocks or degrades automated access, the system records evidence and keeps the last-good roster. It does not rotate through egress addresses to evade the source-side control.

## Key paths

| Path | Purpose |
|---|---|
| scraper/sweep.py | primary HCSO sweep orchestrator |
| scraper/client.py | HCSO HTTP client, concurrency and retry policy |
| scraper/sweep_guards.py | list/detail health guards |
| scraper/orc.py | ORC normalization and lookup |
| scraper/store.py | JSON persistence, changelog, anonymization, takedown enforcement |
| web/build.py | deterministic static-site builder |
| web/classify.py | charge classification and display helpers |
| scripts/verify_public_data.py | published JSON contract verifier |
| scripts/summarize_telemetry.py | operational health summary |
| data/surnames.txt | A-Z surname inputs |
| config/public-data-manifest.json | public JSON compatibility and privacy contract |
| backend/src/index.js | Supabase-backed Node service |
| SECURITY.md | vulnerability reporting policy |

## Operational remediation

The repository now includes a specific deployment flow for the anonymized-changelog tagging defect.

See README_DEPLOY.md for the operator runbook and DEPLOYMENT_SPEC.md for the recovery contract.
