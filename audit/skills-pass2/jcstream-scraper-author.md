# Audit Pass 2 — jcstream-scraper-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: Every pass-1 recommendation is implemented with accurate citations; only nits remain.

## Pass-1 recommendation status
1. Fix verify command (`tests/test_sweep_guards.py` → `tests/test_sweep.py`): **Done** — `SKILL.md:66` now runs `tests/test_sweep.py` (file exists; pass-1 line 13).
2. Name the fourth feed (`incidents.py` / `k59e-2pvf`): **Done** — `SKILL.md:46` lists `k59e-2pvf — PDI Crime Incidents in scraper/incidents.py`; description also enumerates `incidents.py` at `SKILL.md:3`.
3. Document `check_detail_watchdog`, `prune_photos`, `SWEEP_WALLCLOCK_HARD_CAP_S`: **Done** — watchdog at `SKILL.md:19` (constants verified at `sweep_guards.py:30-37`), photo prune at `SKILL.md:21` (matches `sweep_guards.py:43,104-129`), wall-clock at `SKILL.md:31` (matches `scraper/sweep.py:61`).
4. Mention `pra_base.py` + `pra_jms_vendor.py` and `ingest_issue` workflow: **Done** — PRA modules at `SKILL.md:56`; issue-ingest pipeline at `SKILL.md:53`.
5. Broaden trigger phrases: **Done** — `SKILL.md:3` adds "add an Open Data feed", "Socrata pull", "fix the sweep cron", "tune detail watchdog", "raise/lower roster guard", "PRA email loop", "courtclerk link helper", "photo prune skipped", "incidents feed", "rate-limit", "sweep wall-clock".
6. Update workflow paragraph (Pages deploy + 50-min timeout): **Done** — `SKILL.md:51` cites `upload-pages-artifact@v3`, `deploy-pages@v4`, `github-pages` env binding, and `timeout-minutes: 50` (verified at `.github/workflows/sweep.yml:35,38-40,100-105`).
7. Cite `client.py:26-34` rate-limit constants and corrupt-snapshot refusal: **Done** — rate-limit constants at `SKILL.md:31` (verified at `scraper/client.py:26-34`); `load_current_or_raise` + `SnapshotCorruptError` + `CHANGELOG_LIMIT` at `SKILL.md:23` (verified at `scraper/store.py:28-36,41,76-87`).

## New issues found in pass 2
- Minor: `SKILL.md:11` still labels the constant block "`sweep_guards.py:23-25`" — the actual list-sweep constants span `sweep_guards.py:23-25` (correct), but `SWEEP_MIN_ROSTER_FRACTION = 0.5` is reproduced as `0.5` (`SKILL.md:14`) — now matches source (`sweep_guards.py:24`). Pass-1 nit is closed.
- Minor: `scraper/match.py` mentioned at `SKILL.md:48` but only as a one-liner; acceptable for a scope hint.
- The paired agent `.claude/agents/jcstream-scraper-author.md:14` still says "a fifth" Open Data feed, which is fine but won't auto-update if a fifth is added; not a regression.

## Pass-2 lens checks
- **Drift**: Clean. All cited line ranges verified against `scraper/sweep_guards.py:23-25,30-37,43,46-61,64-101,104-129`, `scraper/sweep.py:61`, `scraper/client.py:26-34`, `scraper/store.py:28-36,41,76-87`, and `.github/workflows/sweep.yml:35,38-40,100-105`.
- **Coverage**: Clean. All pass-1 gaps (incidents feed, detail watchdog, photo prune, wall-clock cap, snapshot-corrupt refusal, changelog limit, `pra_base`/`pra_jms_vendor`, `ingest_issue`, `match.py`, rate-limit constants) are now named in `SKILL.md:19-23,31,46,48,53,56`.
- **Triggers**: Clean. Description (`SKILL.md:3`) covers all phrasings flagged in pass-1 section C.
- **Applicability**: Alive — every owned file referenced (`scraper/sweep.py`, `sweep_guards.py`, four OD pullers, `client.py`, `store.py`, three PRA modules, `match.py`, `ingest_issue.py`) is present; sweep cron remains 30-min (`.github/workflows/sweep.yml:7`).
