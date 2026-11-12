---
name: repo-file-triage-workflow
description: Autonomous agentic execution workflow that inventories all files in AICincy/HCJC, classifies each as inoperable/stale/irrelevant/of-concern/keep, and produces a minimal executable refresh plan without breaking the SHA-256 hash-chained evidence log. Use when the user says organize files, triage repo, refresh repo, clean repo, prune repo, or audit file relevance.
---

# Repo File Triage Workflow

Autonomous agentic execution workflow for AICincy/HCJC that turns a 4000+ file repository into a five-way classified ledger and a safe refresh plan. Leaves only files needed to execute sweep -> build -> Pages.

## AAI interoperability contract

`aai-cognitive-interface` is the mandatory governing runtime. This skill is a subordinate domain module supplying repo triage methods only. It does not override, narrow, suspend, or reinterpret AAI. AAI governs runtime state, authorization boundary, recovery, verification, and artifact completion. Accept AAI's recovered objective, authorized scope, hard constraints, and next executable action as control state.

Accept AAI statuses (`DRAFTED` through `ADVERSARIAL-PASS`, `BLOCKED` codes) without redefinition. Domain triage statuses use `TRIAGE-` prefix to avoid collision.

## Outcome and task boundary

**Outcome:** A classified ledger for every tracked + untracked file, a refresh plan that preserves executability, and a PR that proves no SHA-256 chain break.

**Boundary:** Read-only discovery first. No deletions, moves, or rewrites until the ledger is approved. The only file that must never be mutated by triage is `data/waf_block_log.json` (append-only SHA-256 chain, verified by `scraper/verify_block_log.py`).

**Non-goals:** Rewriting sweep/build logic, retuning thresholds, redesigning templates/CSS, or migrating `config/public-data-manifest.json` paths. Those require separate tasks.

## Inputs and authority

- **Authoritative inputs:** Tip of `main`, live site `https://www.aretheyinjail.com`, `config/public-data-manifest.json`, live workflows in `.github/workflows/`, and `AUDIT-CONTRACT.md` productivity ranking (false ground truth > live publish loop > hygiene). Treat `audit-output/` dated packets and `docs-reference/supporting/audits` duplicates as stale residue until proven otherwise.
- **Evidence discipline:** Every classification row cites a source file, line, or workflow. No claim without an artifact.
- **Authorization:** Ledger generation is pre-authorized. Destructive prune (delete/move) requires explicit user approval after ledger review. Never infer it.

## Five-way rubric

| Label | Meaning | Typical occupants in HCJC |
|---|---|---|
| `keep` | Required to execute or verify the pipeline | `scraper/`, `web/build.py` + `web/shape/` + `web/templates/` + `web/static/`, `config/public-data-manifest.json`, `data/current.json` + `data/changelog.json` + `data/waf_block_log.json` + other manifest sources, `data/surnames.txt`, `.github/workflows/sweep.yml` + `ci.yml` + `pages.yml` + `rebuild.yml`, `scripts/verify_public_data.py`, `requirements.txt` + `pyproject.toml`, `tests/` + `tests/conftest.py`, `backend/` (Node isolated), `LICENSE`, minimal `README.md` + `.gitignore` |
| `stale` | Contradicts tip/live workflows or duplicates superseded guidance | `AGENTS.md`, `CLAUDE.md`, `DEPLOYMENT_*.md`, `handoff.md`, `audit-output/` packets, `docs-reference/supporting/audits/` (36 duplicated memos), dated `pra_requests/` PACKET triples that are not in the publish path |
| `irrelevant` | Not on the sweep -> build -> Pages -> manifest path and not required for verification | Historical `HAMCO/*.json` court-site scrapes (238 files, 1.89 MB), `evidence/` outage HTMLs beyond retention, `archive-manifests/`, `audit/` historical notes superseded by `AUDIT-CONTRACT.md`, generated `docs/` derivable via `python -m web.build` (keep committed `docs/` as live artifact but mark derivable) |
| `of-concern` | Privacy, security, retention, or architectural-boundary risk | Any Python file importing Supabase (violates `tests/test_architectural_compliance.py`), committed `.env` or secret, PII in `docs/` beyond current roster, missing `noindex`/`noarchive`, `data/` files exposed outside manifest contract |
| `inoperable` | Broken execution: failed import, dead code, failing test, missing dep | Files failing `ruff check`, `mypy scraper web`, `pytest -q`, `python -m scraper.verify_block_log`, `python scripts/verify_public_data.py`, or `python -m web.build` |

Full decision tree in [references/classification-rubric.md](references/classification-rubric.md).

## Hard constraints

- Never hand-edit, truncate, reformat, or replace `data/waf_block_log.json`. Append only via `scraper/store.py:append_block_evidence`. Chain verified by `python -m scraper.verify_block_log`. Corruption fails closed.
- Never mutate `data/current.json` or `data/changelog.json` except through `scraper/sweep.py` atomic tmp+rename path. Preserve `docs/CNAME` when present.
- Preserve `config/public-data-manifest.json` paths. Removals or renames require a versioned migration.
- Keep database clients and Supabase credentials inside `backend/` only. No Python pipeline file may import `supabase`.
- Preserve evidence isolation: tests must not write real `waf_block_log.json` (see `tests/conftest.py` wrap of `store.append_block_evidence`).
- Deterministic build contract holds: `python -m web.build` with `JCSTREAM_SITE_BASE_URL=""` must produce byte-identical `docs/` for identical `data/` inputs. `docs/data/transparency_metrics.json:computed_utc == data/current.json:generated_utc`.

## Workflow

### Phase 1 — Discovery (read-only)

1. Run `scripts/inventory.py` to enumerate every file (tracked + untracked, excluding `.git/`). Captures size, mtime, manifest membership, workflow reference, and SHA-256 for `waf_block_log.json` chain head.
2. Map live publish loop: verify `.github/workflows/sweep.yml` builds into `docs/` (default `--out`) and commits both `data/` + `docs/` per `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs`. Confirm `pages.yml` is secondary artifact path only.
3. Snapshot CI gates: `pyproject.toml` / `requirements.txt` pins, `ci.yml` matrix (3.13+3.14), `ruff`/`mypy scraper web`/`pytest`/`verify_block_log` scope.

Protocol in [references/inventory-protocol.md](references/inventory-protocol.md).

### Phase 2 — Classification

Run the rubric row-by-row. Each file gets one label, a reason code, and an evidence pointer (workflow, manifest, test, or grep). Delegation rule per task instructions: do not delegate single-continuous traces or small lookups. Delegate only work needing substantial separate context (e.g., parallel subagents for `scraper/` vs `web/` vs `docs-reference/` vs `pra_requests/` deep reads) with bounded objectives.

Confidence is not a substitute for evidence. If evidence is missing, mark `of-concern` and flag for manual review.

### Phase 3 — Verification (no mutation)

Run the smallest covering commands before any prune proposal:

```text
python -m ruff check .
python -m mypy scraper web
python -m pytest -q
python -m scraper.verify_block_log
python scripts/verify_public_data.py
python -m web.build  # then diff docs/ for determinism
```

Record pass/fail per gate. A failing gate moves affected files to `inoperable` or `of-concern`, never to `keep`.

### Phase 4 — Refresh plan

Produce `triage-ledger.csv` (one row per file) + `refresh-plan.md` (keep set, delete set, stale doc rewrites, and rollback procedure). The keep set must still satisfy every gate above with `docs/` regenerated from `data/`. Include size impact (HCJC tip: `docs/` ~112 MB, `waf_block_log.json` ~41 MB, `pra_requests/` ~45 MB, `audit-output/` ~36 MB are the dominant costs).

Plan template in [references/refresh-plan.md](references/refresh-plan.md).

### Phase 5 — Execution (gated)

Only after user approves the ledger:

1. Create branch `triage/refresh` from `main`.
2. Apply deletions/moves per plan. Never batch unrelated changes.
3. Re-run all gates + `web.build` determinism check. Commit `data/` + `docs/` together if `data/` changed.
4. Open PR with ledger + plan + gate evidence. Do not force-push `main`.

## Output contract

- `triage-ledger.csv` — columns: `path,bytes,category,reason_code,evidence,action,notes` (see [assets/ledger-schema.json](assets/ledger-schema.json)).
- `refresh-plan.md` — keep/delete/stale-rewrite tables, size delta, rollback, and SHA-256 chain head before/after (`sha256sum data/waf_block_log.json`).
- PR description cites `AUDIT-CONTRACT.md` live truth and the exact verification commands run.

## Stop conditions

- Stop and request approval if `waf_block_log.json` chain would be touched, if a manifest path would be removed, or if `tests/test_architectural_compliance.py` would be violated.
- Stop if discovery finds >10% of files lack evidence pointers — re-run inventory before classifying.
- Hard block on `BLOCKED` per AAI (missing authorization, evidence, or provider state).

## Validation

After modifying this skill, run:

```text
python <aai>/scripts/aai_runtime_gate.py package .claude/skills/repo-file-triage-workflow
```

`<aai>` is the `aai-cognitive-interface` skill wherever the host loads it. AAI
is not vendored in this repository. It comes from the operator's claude.ai
account (in Claude Code, synced under `~/.claude/skills/synced/`). Use the
host's Python 3 interpreter. Also run the skill-creator `quick_validate.py`
when the host provides it. If AAI is not loaded, report that and do not claim
STATIC-PASS.

Both must report STATIC-PASS. Runtime verification requires a ledger + plan + passing gates on a real inventory run.
