# Classification Rubric

Decision tree for the five-way triage. Apply top-down; first matching rule wins. Every row must cite an evidence pointer (workflow, manifest, test, grep, or `git log`).

## 1. inoperable

File fails a verification gate or is dead code with a broken import graph.

- Fails `ruff check` or `mypy scraper web` (determined by running the tool, not by inspection).
- Imported module does not exist or `python -m py_compile` fails.
- Test imports it and `pytest -q` fails because of it.
- Referenced in a workflow `uses:` / `run:` step that no longer resolves.
- Reason codes: `INOP-LINT`, `INOP-TYPE`, `INOP-IMPORT`, `INOP-TEST`, `INOP-WORKFLOW`.

If the file is not exercised by any gate but is clearly unreachable (no importer, no workflow reference, no manifest entry, not under `docs/` publish), prefer `irrelevant` over `inoperable`. `inoperable` requires demonstrated breakage.

## 2. of-concern

File creates a privacy, security, retention, or architectural-boundary risk. Checked before `stale` so risk is not hidden as staleness.

- Python file under `scraper/` or `web/` imports `supabase` / `@supabase` / `supabase-py` (violates `tests/test_architectural_compliance.py` - only `backend/` may contact Supabase).
- Committed `.env`, `.env.*`, `credentials.json`, private key, or token-like secret (`scripts/verify_public_data.py` / `grep` for `SUPABASE_SERVICE_ROLE` outside `backend/`).
- `data/` file not listed in `config/public-data-manifest.json` but copied into `docs/data/` by `web/build.py` (extra public surface).
- `docs/` page missing `noindex, noarchive` or exposing a historical inmate beyond retention (`data/anon_changelog.json` contract).
- `data/waf_block_log.json` would be mutated by the triage action (any delete/reformat/truncate).
- Reason codes: `CONCERN-DB-BOUNDARY`, `CONCERN-SECRET`, `CONCERN-PRIVACY`, `CONCERN-MANIFEST-LEAK`, `CONCERN-SHA256`.

Mark `of-concern` even if the file also qualifies as `stale` or `irrelevant`. File goes to manual review, never auto-delete.

## 3. stale

File contradicts tip `main`, the live site, or live workflows, or duplicates superseded guidance.

- `AGENTS.md`, `CLAUDE.md`, `handoff.md`, `DEPLOYMENT_*.md` that describe a workflow, cron, or branch-serve model not matching `sweep.yml` / `pages.yml` / `rebuild.yml` at `HEAD`.
- Packets under `audit-output/` and `docs-reference/supporting/audits/` that are dated memos / duplicated copies of the same audit (e.g., 36x `25_pages_stale_artifact_misdiagnosis.md` lineage). `AUDIT-CONTRACT.md` defines these as archived stubs, not live truth.
- `pra_requests/` daily `PACKET.md` / `PACKET.pdf` / `PACKET.docx` triples not referenced by any workflow, manifest, or build step and not needed to reproduce `data/` or `docs/`.
- `docs-reference/` supporting docs that duplicate `docs/` content or describe a pre-branch-serve deploy model.
- Any `.md` whose claim about the live site fails `curl https://www.aretheyinjail.com/ | grep jcstream:generated-utc` or contradicts `AUDIT-CONTRACT.md` live-truth definition.
- Reason codes: `STALE-DOC`, `STALE-DUPLICATE`, `STALE-PACKET`, `STALE-AUDIT-DUP`.

Stale files are candidates for rewrite-into-one or delete after approval. Do not delete until ledger approval.

## 4. irrelevant

File is not on the sweep -> build -> Pages -> manifest path and not required for verification. Safe to drop if the keep set still passes all gates.

- `HAMCO/*.json` - 238 court-site scrape jsons (1.89 MB) used for one-off investigations, not read by `scraper/` or `web/build.py`.
- `evidence/` outage HTMLs beyond the retention window needed for `waf_block_log` evidence.
- `archive-manifests/` historical provenance not read by any workflow.
- `audit/` historical notes superseded by `AUDIT-CONTRACT.md` (when not load-bearing for a cited claim).
- `pra_requests/` scratch / `audit-output/.taskmaster/` legacy state.
- Generated `docs/` derivability note: `docs/` is derivable via `python -m web.build` but is kept as the live branch-serve artifact (so mark `keep (derivable)` not `irrelevant`). Do not mark `docs/` irrelevant without a migration that preserves Pages serving.
- Reason codes: `IRR-HAMCO`, `IRR-EVIDENCE`, `IRR-ARCHIVE`, `IRR-SCRATCH`, `IRR-DERIVABLE`.

## 5. keep

File is required to execute or verify the pipeline. Default only if no higher-priority rule matched.

Keep set (must pass all gates after any prune):

- `scraper/*.py` (including `verify_block_log.py`, `freeze_alert.py`, `store.py`, `sweep.py`, `sweep_guards.py`, `client.py`, `parsers.py`, `models.py`, `classify.py`), `data/surnames.txt`.
- `web/build.py`, `web/pages.py`, `web/outputs.py`, `web/shape/`, `web/templates/`, `web/static/`, `web/dispatch.py`, `web/classify.py`.
- `config/public-data-manifest.json` (all 16 paths) + any `data/*.json` listed as `source` there (`current.json`, `changelog.json`, `anon_changelog.json`, `history.json`, `orc_offenses.json`, `*_recent.json`, `courtclerk_cases.json`, `waf_block_log.json`).
- `data/waf_block_log.json` (SHA-256 chain - never triaged for deletion).
- `.github/workflows/sweep.yml`, `ci.yml`, `pages.yml`, `rebuild.yml` (live publish loop) plus `live-parity.yml` / `staleness-watchdog.yml` if they gate freshness.
- `scripts/verify_public_data.py`, `scripts/summarize_telemetry.py` and any script invoked by a live workflow.
- `requirements.txt`, `pyproject.toml`, `.python-version`, `.gitignore`, `LICENSE`.
- `tests/` + `tests/conftest.py` (evidence isolation) + fixtures needed for `pytest -q`.
- `backend/` (Node isolated, only Supabase consumer).
- Minimal root docs: `README.md` (if rewritten to match live truth), `.gitignore`, `AUDIT-CONTRACT.md` (live truth definition), `SECURITY.md`.
- `.claude/skills/` + `.claude/agents/` that are referenced by active tasks (keep, do not prune skill infrastructure during triage).

Reason codes: `KEEP-SWEEP`, `KEEP-BUILD`, `KEEP-MANIFEST`, `KEEP-WORKFLOW`, `KEEP-VERIFY`, `KEEP-TEST`, `KEEP-BACKEND`, `KEEP-SKILL`.

## Tie-breakers

- Apply the decision tree in its declared top-down order: `inoperable` > `of-concern` > `stale` > `irrelevant` > `keep`. Both `inoperable` and `of-concern` block auto-delete.
- Evidence beats heuristic: a file with a passing workflow reference and a passing `verify_public_data.py` manifest entry is `keep` even if large.
- Size does not imply irrelevance: `waf_block_log.json` (41 MB) and `docs/data/search.json` are large but load-bearing.
