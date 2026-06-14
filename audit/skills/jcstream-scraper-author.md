# Audit — jcstream-scraper-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-scraper-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-scraper-author.md
- **Verdict**: Yellow
- **One-line summary**: Core sweep-guard claims are accurate, but the SKILL.md misses three feeds, two new guards, the orchestrator wall-clock cap, and points the verify command at a test file that does not exist.

## A. Drift
- SKILL.md:11 cites `sweep_guards.py:23-25` — accurate (`scraper/sweep_guards.py:23-25`), but lists `0.50` while the actual constant is `0.5` (`scraper/sweep_guards.py:24`). Trivial.
- SKILL.md:17 cites `sweep_looks_healthy()` at `sweep_guards.py:57-66` — actual span is `sweep_guards.py:46-61` (signature on 46, returns on 61).
- SKILL.md:38 says the fourth Cincinnati feed is "in `cincy_open.py`" — wrong. `scraper/cincy_open.py:1-62` is a generic Socrata helper; the four real feeds are `cfs.py` (`qiik-bpks`), `cfs_pdi.py` (`gexm-h6bt`), `shootings.py` (`sfea-4ksu`), and `incidents.py` (`k59e-2pvf`). The SKILL.md never names `incidents.py`.
- SKILL.md:56 verify command names `tests/test_sweep_guards.py` — that file does not exist; only `tests/test_sweep.py` exists (guard tests live there, e.g. `tests/test_sweep.py:169,178,185`).
- SKILL.md:43 says workflow "commits, pushes" but omits the `actions/upload-pages-artifact@v3` + `deploy-pages@v4` steps (`.github/workflows/sweep.yml:100-105`) and the `github-pages` environment binding (`sweep.yml:38-40`).

## B. Coverage gaps
- `scraper/incidents.py:1-83` — fourth OD feed (`k59e-2pvf`), wired into `sweep.yml:65-67`; not mentioned by name.
- `check_detail_watchdog()` and constants `DETAIL_WATCHDOG_*` (`scraper/sweep_guards.py:30-37,64-101`) — a second-tier guard with hard BLOCK at name-rate < 0.60 over ≥100 attempts; entirely absent from the skill.
- `prune_photos()` + `PHOTO_PRUNE_MAX_FRACTION = 0.5` (`scraper/sweep_guards.py:43,104-129`) — the third guard, not mentioned.
- `SWEEP_WALLCLOCK_HARD_CAP_S = 22 * 60` (`scraper/sweep.py:61`) — orchestrator's wall-clock budget; should be in "Rate-limit etiquette" or "Workflow contract".
- `SnapshotCorruptError` + `load_current_or_raise` (`scraper/store.py:28-36,76-87`) — sweep refuses cycle on corrupt prior; explicitly invariant.
- `scraper/pra_jms_vendor.py:1-110` — third PRA module (JMS-vendor request) and `pra_base.py` (`scraper/pra_base.py:1-67`) consolidating SMTP transport; SKILL.md only names `pra.py` + `pra_capias.py`.
- `scraper/ingest_issue.py` + `.github/workflows/ingest_case_data.yml` — issue-form → `data/courtclerk_cases.json` ingest pipeline, not mentioned.
- `scraper/match.py:1-85` — CFS↔inmate matcher; not mentioned.
- `scraper/client.py` constants `DEFAULT_CONCURRENCY=32`, `DEFAULT_CRAWL_DELAY=0.0`, `RETRY_AFTER_CAP_S=30.0` (`scraper/client.py:26-34`) — the actual rate-limit budget; SKILL.md's "Rate-limit etiquette" prose doesn't cite them.
- `data/changelog.json` rolling window `CHANGELOG_LIMIT = 500` (`scraper/store.py:41`) — sweep-side invariant.

## C. Trigger-phrase quality
- Current description (paraphrased): scraper/, HCSO sweep, four OD feeds (cfs/cfs_pdi/shootings), courtclerk URL helpers, PRA loop, sweep guards, atomic write, 30-min cron. Triggers: "add a new data feed", "fix the HCSO scraper", "tune the sweep guard".
- Issues: triggers do not match common phrasings like "rate-limit", "PRA email", "Socrata", "incidents feed", "courtclerk URL", "photo prune", "detail watchdog", or "sweep wall-clock". A user saying "the cron is timing out" or "add an incidents column" would not auto-fire this skill.
- Proposed rewording: add to triggers — "add an Open Data feed", "Socrata pull", "fix the sweep cron", "tune detail watchdog", "raise/lower roster guard", "PRA email loop", "courtclerk link helper", "photo prune skipped".

## D. Applicability
- Alive — every owned file is present, the sweep cron runs every 30 min (`.github/workflows/sweep.yml:7`), and the PRA loop has a daily workflow (`.github/workflows/pra_daily.yml:7`); not retirable.

## Recommended fixes (priority order)
1. Fix the verify command (`tests/test_sweep_guards.py` → `tests/test_sweep.py`).
2. Name the fourth feed (`incidents.py` / `k59e-2pvf`) and replace the "in `cincy_open.py`" line.
3. Document `check_detail_watchdog`, `prune_photos`, and `SWEEP_WALLCLOCK_HARD_CAP_S` in the guards section.
4. Mention `pra_base.py` + `pra_jms_vendor.py` and the `ingest_issue` workflow in scope.
5. Broaden trigger phrases per section C.
6. Update the workflow paragraph to include the Pages deploy steps and 50-min `timeout-minutes`.
7. Cite `client.py:26-34` rate-limit constants and the corrupt-snapshot refusal at `store.py:76-87`.
