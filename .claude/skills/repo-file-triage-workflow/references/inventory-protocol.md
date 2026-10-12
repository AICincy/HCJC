# Inventory Protocol

Read-only discovery steps that precede classification. No writes until Phase 2 completes.

## 1. Enumerate

```
# Tracked + untracked (excluding .git/)
git ls-files --cached --others --exclude-standard -z | tr '\0' '\n' | sort > /tmp/tracked.txt
# Physical fallback for ignored-but-present surfaces (docs/ is tracked, data/ is tracked)
Get-ChildItem -Recurse -File -Exclude .git | sort FullName
```

Or run `scripts/inventory.py` which does both and emits `path, bytes, mtime, manifest_member, workflow_ref, sha256_head`.

Prefer `git ls-files` for the ledger source of truth; use the physical walk only to detect ignored-but-present residue (e.g., stray `private/` or `.tmp`).

## 2. Annotate

For each path, capture:

- `bytes` - file size (for size delta in refresh plan).
- `manifest_member` - whether the path is listed in `config/public-data-manifest.json` as `path` or `source`.
- `workflow_ref` - whether any `.github/workflows/*.yml` `uses:` or `run:` references the path (grep workflows).
- `build_ref` - whether `web/build.py` / `web/pages.py` / `web/outputs.py` / `web/shape/` imports or reads the path.
- `test_ref` - whether any `tests/test_*.py` imports or fixtures the path.
- `sha256_head` - for `data/waf_block_log.json` only: `sha256sum` of the file and chain head hash (last record's `sha256` field). Used to prove no mutation.

## 3. Map live publish loop

Verify these invariants before classifying:

1. `sweep.yml` builds into `docs/` (default `--out`, not `/tmp`) and commits both `data/` + `docs/` (`git diff --name-only` includes both on a sweep run).
2. `pages.yml` is secondary artifact path only; branch-serve (`build_type=legacy`, Source `main /docs`) is live.
3. `ci.yml` still gates `ruff`, `mypy scraper web`, `pytest`, `verify_block_log`, `verify_public_data`, `web.build` determinism.

Record the commit SHA of `HEAD` for each workflow file. If any workflow contradicts `AUDIT-CONTRACT.md` live-truth ranking, flag it `of-concern` not `stale`.

## 4. Snapshot size ranking

Group by top-level directory to inform the refresh plan's size delta. Expected tip ordering: `docs` > `data` > `pra_requests` > `audit-output` > `HAMCO` > `evidence` > `audit` > `backend` > `web` > `scraper` > `tests`.

## 5. Stale-doc cross-check

For each root `.md` (`AGENTS.md`, `CLAUDE.md`, `README.md`, `DEPLOYMENT_*.md`, `handoff.md`), compare claims against:

- `HEAD` workflows (cron expression, timeout, branch-serve vs Actions deploy).
- Live site `curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc`.
- `AUDIT-CONTRACT.md` live-truth definition.

Mismatch without a newer `DECISIONS.md` entry is `stale`.

## 6. Deliverable

`scripts/inventory.py` writes `triage-ledger.csv` (one row per file, category initially empty or heuristically filled) and a `discovery-notes.md` with the publish-loop verification and size ranking. Classification fills the category in Phase 2.
