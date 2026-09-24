# Repository guide for agents

## Scope and working approach

These instructions apply throughout this repository. JCStream (HCJC) mirrors
the Hamilton County, Ohio Justice Center roster and Cincinnati public-data
feeds into a static website.

- Inspect `git status` before editing; preserve unrelated work and keep changes
  limited to the requested task. Change CSS, templates, or design only when the
  task authorizes that work.
- Read `README.md` for orientation, `CLAUDE.md` for existing project guidance,
  and relevant entries in `DECISIONS.md`. Some historical operational notes are
  superseded: verify behavior against current code and workflows. In particular,
  `.github/workflows/pages.yml` now builds and deploys a Pages artifact; older
  branch-serving instructions do not describe the current workflow.
- Execute clear, authorized work without repeated confirmation. Ask only when
  missing requirements would materially change the result. Report what changed,
  what was verified, and any actual blocker concisely.
- Do not infer permission to push, deploy, dispatch live workflows, send records
  requests, or change repository settings from a local code-editing request.
  Preserve existing authorization when the user has already supplied it.

## Source map and architectural boundaries

| Location | Responsibility |
| --- | --- |
| `scraper/` | Synchronous HTTP clients, parsing, validated records, sweep guards, data storage, public feeds, and evidence logging |
| `web/build.py`, `web/pages.py`, `web/outputs.py` | Static-site orchestration, rendering, and publication |
| `web/shape/` | Transformations preparing data for presentation |
| `web/templates/`, `web/static/` | Jinja2 templates and source CSS, JavaScript, fonts, and images |
| `data/` | Canonical pipeline snapshots, reference data, and append-only evidence |
| `docs/` | Generated public site; edit its source inputs instead of generated pages |
| `config/public-data-manifest.json` | Public JSON paths, canonical sources, publication modes, and privacy contract |
| `backend/` | Independent Node service; the only component that accesses Supabase |
| `tests/` | Pytest suite and offline fixtures |
| `.github/workflows/`, `scripts/` | CI, scheduled ingestion, deployment, and integrity checks |
| `audit/`, `evidence/`, `archive-manifests/` | Audit records, evidence, and archival provenance |
| `design/`, `docs-reference/` | Design guidance and supporting reference documents |

The public site reads JSON and has no database on its request path. Keep database
clients and Supabase credentials out of the Python pipeline and published assets.
`tests/test_architectural_compliance.py` enforces this boundary. Never commit
secrets or local environment files.

## Development and verification

Use Python 3.13 or newer; CI tests 3.13 and 3.14. From the repository root, in a
virtual environment:

```text
python -m pip install -r requirements.txt
python -m pip install ruff==0.16.7 mypy==2.3.1
python -m ruff check .
python -m mypy scraper web
python -m pytest -q
python -m scraper.verify_block_log
```

Treat `pyproject.toml` and CI as the authority for tool versions. Keep runtime
dependency pins in `requirements.txt` and `pyproject.toml` synchronized. Follow
the existing Python style and Ruff configuration (Python 3.13 target, advisory
120-character line length); avoid unrelated formatting churn. A bare `mypy`
checks a broader scope than the explicit CI command above.

Run focused tests while developing and the full pytest suite before committing.
For Python code changes, also run Ruff and the CI mypy scope. Tests are offline:
use fixtures and mocked transports, and preserve the isolation in
`tests/conftest.py` so tests cannot write real evidence, roster, or history data.
Add regression coverage for changed behavior. Documentation-only edits need
content, reference, and whitespace review; do not report unrun tests as passing.

Build and verify the site with:

```text
python -m web.build
python scripts/verify_public_data.py
```

For production-equivalent output, set `JCSTREAM_SITE_BASE_URL` to an empty string
and `JCSTREAM_CNAME` to `www.aretheyinjail.com` in the current shell before the
build. Use PowerShell environment syntax on Windows, not Bash assignment
prefixes. The build can update `data/history.json` as well as `docs/`; inspect
the resulting diff and do not commit unrelated generated changes. Preserve
`docs/CNAME` when present. The publication validator checks generated data
against the manifest and canonical sources.

For backend work, use Node >=20 (CI uses 22). Run `npm ci`,
`node --check src/index.js`, and `npm audit --audit-level=high` from `backend/`.
Use `npm start`, or `npm run start:local` with a local `.env` based on
`.env.example`. There is no npm test script. The CI smoke test in
`.github/workflows/ci.yml` checks `/health` returns 200 and unauthenticated `/me`
returns 401 on port 8787 with dummy Supabase configuration. Preserve route auth.

## Data, evidence, and publication invariants

- Never hand-edit, truncate, reformat, or replace `data/waf_block_log.json`.
  It is append-only SHA-256-chained evidence. Preserve original audit records
  and session identifiers. A passing chain verifier alone does not establish
  log presence or non-shrinkage; CI checks those separately.
- Preserve fail-closed handling of corrupt evidence and changelogs. Do not
  silently replace unreadable records with empty data.
- Keep the last good roster when sweep health checks fail. Do not relax collapse,
  failed-query, or photo-pruning guards to force publication. The A-Z entries in
  `data/surnames.txt` are intentional substring queries, not incomplete surnames.
- Record WAF blocks and honor backoff. Do not introduce proxy rotation or other
  evasion. Live sweeps are operational actions, not routine test commands.
- Preserve public JSON paths in `config/public-data-manifest.json`; removals or
  renames require a versioned migration. Generated copies belong in the build
  artifact, not additional manually maintained sources.
- Keep the current-roster mirror and privacy model: no public historical archive
  of released individuals, no public dispatch-to-arrest candidate joins, no
  tracking, and no per-person social preview cards. Preserve noindex/noarchive,
  presumption-of-innocence notices, and free correction/removal workflows.
- Preserve anonymization and retention rules. Do not expose private outputs,
  credentials, or additional identifying data through the build.
- Do not put tooling or agent-installation artifacts under `data/`: automation
  stages that directory. Inspect the worktree after dependency or skill installs.

## Handoff

Review the final diff and run `git diff --check`. Summarize the actual change and
checks performed, including failures or skipped checks. Distinguish local build
results from live deployment evidence; do not copy dated roster counts, test
totals, or historical green-build claims into a current status report.
