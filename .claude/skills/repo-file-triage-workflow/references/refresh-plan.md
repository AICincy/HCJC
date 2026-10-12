# Refresh Plan Template

Copy this template into the triage PR as `refresh-plan.md`. Fill every table from `triage-ledger.csv`; do not hand-wave counts.

## 1. Objective

Refresh the repository to the minimal executable set that preserves sweep -> build -> Pages and all CI gates, without breaking the `data/waf_block_log.json` SHA-256 chain.

## 2. Keep set (must pass all gates after prune)

| Area | Paths | Gate that proves necessity |
|---|---|---|
| Sweep | `scraper/*.py`, `data/surnames.txt` | `pytest tests/test_sweep.py`, `verify_block_log` |
| Build | `web/build.py`, `web/shape/`, `web/templates/`, `web/static/` | `python -m web.build` determinism |
| Manifest | `config/public-data-manifest.json` + 16 `data/*.json` sources | `scripts/verify_public_data.py` |
| Workflows | `sweep.yml`, `ci.yml`, `pages.yml`, `rebuild.yml` | live publish loop |
| Verify | `scripts/verify_public_data.py`, `scraper/verify_block_log.py` | `ci.yml` |
| Tests | `tests/` + `conftest.py` | `pytest -q` |
| Backend | `backend/` | `tests/test_architectural_compliance.py` |
| Root | `LICENSE`, `.gitignore`, `requirements.txt`, `pyproject.toml`, `AUDIT-CONTRACT.md`, `README.md` (rewritten) | `ruff`/`mypy`/`pip-audit` |

Explicitly list every kept top-level directory and workflow file.

## 3. Delete set (requires approval)

| Paths | Category | Reason code | Evidence | Bytes reclaimed |
|---|---|---|---|---|
| `HAMCO/*.json` (238 files) | irrelevant | `IRR-HAMCO` | not imported by `scraper/` or `web/build.py` | ~1.89 MB |
| `audit-output/` dated packets | stale | `STALE-PACKET` | `AUDIT-CONTRACT.md` archived-stub rule | ~36 MB |
| `docs-reference/supporting/audits/` dups | stale | `STALE-AUDIT-DUP` | duplicate of `audit/` lineage | ~? |
| `pra_requests/*/PACKET.*` triples | stale | `STALE-PACKET` | not in manifest, not read by build | ~45 MB |
| `evidence/` beyond retention | irrelevant | `IRR-EVIDENCE` | `waf_block_log` is the evidence | ~? |
| superseded `audit/` notes | stale | `STALE-DOC` | superseded by `AUDIT-CONTRACT.md` | ~? |

Add rows for every delete candidate. Total the bytes.

## 4. Stale-doc rewrites (not deletes)

| File | Action | Source of truth |
|---|---|---|
| `AGENTS.md` | Rewrite to match `AUDIT-CONTRACT.md` + live workflows at `HEAD` | `sweep.yml` `ci.yml` `AUDIT-CONTRACT.md` |
| `CLAUDE.md` | Rewrite or collapse into `AGENTS.md` + `AUDIT-CONTRACT.md` | same |
| `README.md` | Trim to orientation + `python -m web.build` + `pytest` | `web/build.py` `tests/conftest.py` |
| `DEPLOYMENT_*.md` `handoff.md` | Delete or fold into one `docs-reference/DEPLOYMENT.md` | `pages.yml` branch-serve truth |

Do not leave contradictory guidance across multiple root `.md` files.

## 5. SHA-256 chain preservation

```
# Before
sha256sum data/waf_block_log.json
python -m scraper.verify_block_log  # must print OK

# After prune (must be byte-identical)
sha256sum data/waf_block_log.json
python -m scraper.verify_block_log  # must still print OK
```

Record both hashes in the PR description. Any delta is a hard block.

## 6. Size delta

| Scope | Before | After | Delta |
|---|---|---|---|
| `docs/` (generated, kept) | ~112 MB | ~112 MB | 0 |
| `data/waf_block_log.json` | ~41 MB | ~41 MB | 0 (never touched) |
| Deleted stale/irrelevant | ~? | 0 | -? |
| Total repo (tracked) | ~? | ~? | -? |

## 7. Verification (run before opening PR)

```
python -m ruff check .
python -m mypy scraper web
python -m pytest -q
python -m scraper.verify_block_log
python scripts/verify_public_data.py
JCSTREAM_SITE_BASE_URL="" python -m web.build && git diff --stat docs/
```

All must pass. `git diff --stat docs/` must be empty (determinism) or contain only the expected `docs/CNAME` preservation.

## 8. Rollback

- Branch `triage/refresh` from `main`; never mutate `main` directly.
- If any gate fails post-prune, preserve the diff for diagnosis and restore only the approved paths from `origin/main`; after a prune commit exists, roll it back with a new revert commit. Never use `git reset --hard`.
- Force-push on `main` is never allowed.
