---
name: jcstream-scraper-author
description: Use when modifying or extending data pullers in scraper/ — HCSO inmate roster (sweep.py), Cincinnati Open Data feeds (cfs.py, cfs_pdi.py, shootings.py, open_data_feeds.py), the courtclerk URL helpers, PRA email loop. Covers rate-limit budget, sweep health guards (sweep_guards.py: 50% floor, 10% error ceiling, detail watchdog, photo prune), atomic write to data/current.json, and the 30-min cron in .github/workflows/sweep.yml. Trigger phrases: "add a new data feed", "add an Open Data feed", "Socrata pull", "fix the HCSO scraper", "fix the sweep cron", "tune the sweep guard", "tune detail watchdog", "raise/lower roster guard", "PRA email loop", "courtclerk link helper", "photo prune skipped", "rate-limit", "sweep wall-clock".
---

# JCStream scraper author

You own `scraper/*.py` and `.github/workflows/sweep.yml`. Data flows: HCSO surname-iter → details fetch → Pillow photo store → `data/current.json` write, gated by health checks.

## Sweep health guards (single source of truth)
List-sweep degradation constants in `scraper/sweep_guards.py`:
```python
SWEEP_MAX_FAILED_FRACTION = 0.10   # bail if >10% of surname fetches errored
SWEEP_MIN_ROSTER_FRACTION = 0.5    # bail if roster collapsed to <50% of last cycle
SWEEP_BOOTSTRAP_FLOOR     = 50     # first-ever sweep needs ≥50 inmates
```
`sweep_looks_healthy()` at `sweep_guards.py` checks both. If it returns False, `sweep.py` keeps the last-good `data/current.json` and exits 0 (silent fallback — this is intentional, mentioned in CLAUDE.md).

A second-tier **detail-page watchdog** (`check_detail_watchdog`, `sweep_guards.py`) covers the case where the list sweep stays green but detail-page parsing has degraded. Soft floors WARN: `DETAIL_WATCHDOG_NAME_FLOOR=0.70`, `DETAIL_WATCHDOG_PHOTO_FLOOR=0.50` (min sample 10). Hard BLOCK refuses the cycle when name rate < `DETAIL_WATCHDOG_BLOCK_NAME_FLOOR=0.60` over ≥`DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE=100` attempts (`sweep_guards.py`).

The third guard is **photo prune safety**: `prune_photos` (`sweep_guards.py`) skips the cycle's prune when `PHOTO_PRUNE_MAX_FRACTION = 0.5` (`sweep_guards.py`) of existing photos would be deleted at once — a sign the list-side guard let through a degraded sweep on bootstrap, not a real release wave.

Snapshot integrity: the orchestrator uses `load_current_or_raise` (`scraper/store.py`); a corrupt prior raises `SnapshotCorruptError` (`store.py`) and the cycle refuses to canonicalize. The rolling changelog window is `CHANGELOG_LIMIT = 500` (`store.py`).

When tuning thresholds, **change `sweep_guards.py` only** — `sweep.py` is the orchestrator and re-imports the constants.

## Surname iteration
`data/surnames.txt` is **A–Z single letters, on purpose** (CLAUDE.md). HCSO's last-name search is a substring match, so 26 letters cover the whole roster after dedup. Don't "fix" this to two-letter prefixes — it slows the sweep and adds nothing.

## Rate-limit etiquette
HCSO returns a generic block page when over rate. The detail fetcher backs off with jitter. Budget constants live in `scraper/client.py`: `DEFAULT_CONCURRENCY=32` (parallelism is the limiter, not delay), `DEFAULT_CRAWL_DELAY=0.0`, `RETRY_AFTER_CAP_S=30.0` (cap on honored 429 Retry-After). The orchestrator also enforces a wall-clock budget: `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` (`scraper/sweep.py`) so the detail-fetch loop bails before the workflow's `timeout-minutes: 50` (`.github/workflows/sweep.yml`) and a partial roster still gets written cleanly.

New OD-feed pullers should:
- Use a single `httpx.Client` for connection reuse
- Respect any rate-limit hints in response headers
- Time-box themselves so a slow feed can't blow the workflow's timeout

## Atomic snapshot writes
Write to `data/current.json.tmp` then `os.replace()` — never directly. This keeps the GH Actions workflow from committing a partial file mid-write.

## Cincinnati Open Data feeds
Three hand-rolled feeds (`scraper/cincy_open.py` is the generic Socrata helper they all call):
- `qiik-bpks` — CFS calls in `scraper/cfs.py` (arrest/citation/report dispositions)
- `gexm-h6bt` — CFS PDI dispatch in `scraper/cfs_pdi.py` (wider window)
- `sfea-4ksu` — reported shootings in `scraper/shootings.py`

Six supplemental feeds in `scraper/open_data_feeds.py` (use-of-force, traffic stops, pedestrian stops, STARS crime, CCA complaints). PDI Crime Incidents (`k59e-2pvf`) was removed May 2026 (replaced by Crime STARS `7aqy-xrv9`). PDI OI Shootings (`r6q4-muts`) was removed May 2026 (dataset frozen since 2019, no replacement).

When adding a feed, follow the pattern in `cfs.py` (or `shootings.py`): typed row dataclass, `load()` returns a list, build.py de-dupes on event number. The CFS-to-inmate matcher lives in `scraper/match.py`.

## Workflow contract
`.github/workflows/sweep.yml` runs every 30 min with `timeout-minutes: 50`. It checks out the dev branch, runs the HCSO sweep, pulls the three Cincinnati Open Data feeds, runs `web.build`, commits + pushes the changes, then runs `actions/upload-pages-artifact@v3` and `actions/deploy-pages@v4` (`sweep.yml`) bound to the `github-pages` environment (`sweep.yml`). Don't add steps that re-create venvs (cold-start cost). Don't push to `main` from CI.

Issue-form ingest: `scraper/ingest_issue.py` + `.github/workflows/ingest_case_data.yml` parses owner-filed GitHub issues into `data/courtclerk_cases.json`; this is a separate pipeline from the sweep cron.

## PRA email loop
`scraper/pra.py` (mugshot-fallback), `scraper/pra_capias.py` (capias requests), `scraper/pra_jms_vendor.py` (JMS-vendor requests), shared SMTP transport in `scraper/pra_base.py`, daily cron in `.github/workflows/pra_daily.yml`. Dry-runs (log-only) until `JCSTREAM_PRA_SMTP_HOST` + `JCSTREAM_PRA_FROM_EMAIL` are set as repo secrets. Don't hard-code SMTP credentials.

## Anti-patterns
- Bypassing `sweep_looks_healthy` because "the roster looks fine".
- Lowering `SWEEP_MIN_ROSTER_FRACTION` without telemetry — false negatives publish a degraded site.
- Direct `open(path, 'w')` for the snapshot — use tmp + rename.
- Scraping `codes.ohio.gov` — it's explicitly off-limits; ORC titles are hand-curated.

## Verify
```sh
python -m pytest -q tests/test_sweep.py
# Dry-run a sweep against a fixture:
python -m scraper.sweep --dry-run   # if --dry-run is implemented; else just inspect output
```
