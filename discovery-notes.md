# Discovery Notes (read-only)

- Root: `C:/Users/jared/.copilot/repos/copilot-worktrees/HCJC/aicincy-fluffy-meme`
- Tracked files: 4542  Physical files: 4545  Ignored-only: 3
- Manifest: 34 paths, 16 sources (config/public-data-manifest.json)
- Workflow refs approximated: 15 tokens
- data/waf_block_log.json: 41803150 bytes, sha256=3b5cf6607d3e43b3...

## Size ranking (top-level)

| Directory | Bytes | Approx MB |
|---|---|---|
| `docs` | 117508769 | 112.07 |
| `data` | 68163884 | 65.01 |
| `pra_requests` | 47508490 | 45.31 |
| `audit-output` | 38230556 | 36.46 |
| `audit` | 11537795 | 11.00 |
| `evidence` | 8002600 | 7.63 |
| `HAMCO` | 1984410 | 1.89 |
| `web` | 1845480 | 1.76 |
| `docs-reference` | 764385 | 0.73 |
| `tests` | 497689 | 0.47 |
| `scraper` | 363346 | 0.35 |
| `.claude` | 357577 | 0.34 |
| `(root)` | 144398 | 0.14 |
| `scripts` | 78080 | 0.07 |
| `.github` | 49804 | 0.05 |
| `design` | 13526 | 0.01 |
| `backend` | 12270 | 0.01 |
| `runbooks` | 5683 | 0.01 |
| `config` | 2571 | 0.00 |
| `archive-manifests` | 1792 | 0.00 |

## Publish-loop checks (manual verification required)

- `sweep.yml` builds into `docs/` (default --out) and commits both `data/` + `docs/` - verify via `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs`.
- `pages.yml` is secondary artifact path; branch-serve `build_type=legacy` Source `main /docs` is live.
- `ci.yml` gates `ruff`, `mypy scraper web`, `pytest`, `verify_block_log`, `verify_public_data`, `web.build` determinism.

## Ignored-only residue (present on disk, not tracked)

- `scraper/__pycache__/__init__.cpython-315.pyc`
- `scraper/__pycache__/store.cpython-315.pyc`
- `scraper/__pycache__/verify_block_log.cpython-315.pyc`
