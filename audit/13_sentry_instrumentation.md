# sentry - Sweep Telemetry Instrumentation

## Audit metadata
- Scope: scraper sweep only (no build, no tests, no other CLI entry).
- Files touched: `requirements.txt`, `scraper/sweep.py`, `.github/workflows/sweep.yml`.
- Mode: error monitoring only. No performance tracing, no profiling, no session replay.

## Purpose

Audit `audit/05_sweep_reliability.md` flagged several "silent staleness" paths
in the sweep: `_sweep_looks_healthy` rejecting a cycle, the detail watchdog
firing, the photo prune skipping. Each path is correct behavior — the sweep
keeps the last-good roster rather than canonicalizing degraded data — but
none of them are visible to the operator. The site looks stale and nobody
knows why because the workflow still exits 0.

This instrumentation closes the loop. Sentry receives a structured event
each time one of those silent-protection paths fires, so a Slack/email
alert lands the same minute the sweep decides not to write.

## How to enable

The instrumentation reads its DSN from `JCSTREAM_SENTRY_DSN`. There are two
moving pieces:

1. **Sentry side.** Create a project in Sentry (Python platform). Copy the
   DSN — it looks like `https://<key>@o<org>.ingest.sentry.io/<project>`.
2. **GitHub side.** Repo Settings -> Secrets and variables -> Actions ->
   **Secrets** -> New repository secret:
   - Name: `JCSTREAM_SENTRY_DSN`
   - Value: paste the DSN.

The next scheduled sweep run will pick it up. `scraper.sweep._init_sentry()`
reads the env var at CLI entry; an unset/empty value short-circuits to a
no-op, so local dev and any Actions run without the secret keep working
identically to before.

## How to disable

Delete the `JCSTREAM_SENTRY_DSN` secret. The SDK init falls through
silently on the next run; all capture points become no-ops because the SDK
hub was never initialized. No code change required.

## Events captured

All events are emitted from `scraper/sweep.py`. The `sweep_guards.py`
module stays pure — guard thresholds remain unchanged and unit-testable
offline.

### `sweep.degraded.roster_floor` (level: warning)

- **Fires when:** the list sweep finished but `len(seen_ids) <
  SWEEP_MIN_ROSTER_FRACTION * len(previous)` AND `len(previous) >=
  SWEEP_BOOTSTRAP_FLOOR`.
- **Cross-reference:** `scraper/sweep_guards.py`
  (`SWEEP_MIN_ROSTER_FRACTION = 0.5`, `SWEEP_BOOTSTRAP_FLOOR = 50`).
- **What it means:** HCSO returned successful responses for the surname
  searches but the union of inmate ids collapsed to under half of what we
  saw last cycle. Real jail churn does not do this in a 30-minute window;
  this is almost always HCSO rate-limiting or paginating differently.
- **Action:** the sweep keeps the last-good `data/current.json`. No
  operator action is required unless multiple cycles in a row alert.
- **Tags:** `prev_count`, `seen_count`, `roster_fraction`.

### `sweep.degraded.surname_errors` (level: warning)

- **Fires when:** `n_failed / n_surnames > SWEEP_MAX_FAILED_FRACTION` AND
  `len(previous) >= SWEEP_BOOTSTRAP_FLOOR`.
- **Cross-reference:** `scraper/sweep_guards.py`
  (`SWEEP_MAX_FAILED_FRACTION = 0.10`).
- **What it means:** more than 10% of the per-surname list-page fetches
  raised an exception (timeout, 5xx, TLS hiccup). At 26 surnames a single
  failure is 3.8%, two is 7.7%, three is 11.5% — the threshold triggers
  on three-or-more letters failing in one cycle.
- **Action:** the sweep keeps the last-good roster. Check whether HCSO
  itself is up at `https://www.hcso.org/justice-center-services/inmate-search/`.
- **Tags:** `prev_count`, `seen_count`, `n_failed`, `n_surnames`,
  `failed_fraction`.

### `sweep.detail_watchdog_tripped` (level: warning)

- **Fires when:** the detail-page watchdog either hard-blocks
  (`blocked="true"`) or trips its WARN-only floors (`blocked="false"`)
  with at least `DETAIL_WATCHDOG_MIN_SAMPLE` attempts.
- **Cross-reference:** `scraper/sweep_guards.py`
  (`DETAIL_WATCHDOG_MIN_SAMPLE = 10`, `DETAIL_WATCHDOG_NAME_FLOOR = 0.70`,
  `DETAIL_WATCHDOG_PHOTO_FLOOR = 0.50`, `DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE = 100`,
  `DETAIL_WATCHDOG_BLOCK_NAME_FLOOR = 0.60`).
- **What it means:** the per-inmate detail pages are parsing badly. The
  WARN tier (under 70% named or under 50% with-photo at >=10 attempts) is
  informational. The BLOCK tier (under 60% named at >=100 attempts) flips
  `roster_ok` to False and the sweep keeps the last-good snapshot.
- **Action:** WARN tier is usually transient. BLOCK tier means HCSO has
  almost certainly redesigned the detail page; check
  `scraper/parsers.py:_parse_detail_page` against a live page.
- **Tags:** `blocked` ("true" or "false"), `attempts`, `named`,
  `with_photo`, plus `name_rate` and `photo_rate` on the WARN tier.

### `sweep.photo_prune.skipped` (level: info)

- **Fires when:** the photo prune would have deleted more than
  `PHOTO_PRUNE_MAX_FRACTION` of existing photos in one cycle.
- **Cross-reference:** `scraper/sweep_guards.py`
  (`PHOTO_PRUNE_MAX_FRACTION = 0.5`).
- **What it means:** the sweep was about to delete >50% of photos in one
  pass. A real release wave does not do that; it's usually a degraded
  sweep that slipped past the list-side guard on bootstrap.
- **Action:** info-level — usually no action. If it persists for multiple
  cycles, inspect `data/photos/` and `data/current.json` for drift.
- **Tags:** `doomed`, `existing`, `fraction`.

### Unhandled exceptions (`capture_exception`)

- **Fires when:** any exception escapes the main sweep `try`-block
  (anything except `KeyboardInterrupt`, which is caught explicitly so the
  partial-write path keeps working).
- **What it means:** an actual bug or unexpected runtime condition; the
  workflow will exit non-zero and the Actions run goes red.
- **Tags:** `sweep.surname_letter` is attached if the exception bubbled
  out of a per-surname worker (see below).

### `sweep.surname_letter` tag

- **Set in:** `_sweep_list.fetch_one`, once per worker invocation.
- **Why:** when an exception in the per-surname worker is captured later
  (e.g. an unexpected typed error after a refactor that removes the
  defensive `except Exception` block), the alert payload includes which
  letter triggered the failure. The letter is enough to triage without
  leaking any PII — `data/surnames.txt` is single A-Z letters by design.

## What is NOT captured (deliberately)

- **No PII:** no inmate names, booking numbers, photo bytes, or charges
  ever reach a Sentry payload. `send_default_pii=False` is set on init,
  and every tag value above is either an aggregate count or the single
  uppercase ASCII letter from `data/surnames.txt`.
- **No traces / spans:** `traces_sample_rate=0.0`. Sentry's performance
  product is off. We want alerts, not telemetry.
- **No build pipeline:** `web/build.py` does not import sentry-sdk. The
  build is deterministic and runs the second after a successful sweep; if
  it fails the Actions run goes red on its own.
- **No test suite:** `scraper.sweep._init_sentry()` is called from
  `main()`, which the pytest suite never reaches. Tests stay offline.
- **No other CLI entries:** `cfs.py`, `incidents.py`, `shootings.py`,
  `cfs_pdi.py`, `pra.py`, `pra_capias.py` are not instrumented. Sweep is
  the only path that needs operator attention on degradation.

## Guard thresholds (unchanged)

This audit explicitly does NOT modify any sweep guard thresholds. Every
threshold listed below lives in `scraper/sweep_guards.py` and is the
same value before and after this audit:

| Constant | Value | Owner |
| --- | --- | --- |
| `SWEEP_MAX_FAILED_FRACTION` | 0.10 | list-sweep guard |
| `SWEEP_MIN_ROSTER_FRACTION` | 0.5 | list-sweep guard |
| `SWEEP_BOOTSTRAP_FLOOR` | 50 | list-sweep guard |
| `DETAIL_WATCHDOG_MIN_SAMPLE` | 10 | detail watchdog WARN tier |
| `DETAIL_WATCHDOG_NAME_FLOOR` | 0.70 | detail watchdog WARN tier |
| `DETAIL_WATCHDOG_PHOTO_FLOOR` | 0.50 | detail watchdog WARN tier |
| `DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE` | 100 | detail watchdog BLOCK tier |
| `DETAIL_WATCHDOG_BLOCK_NAME_FLOOR` | 0.60 | detail watchdog BLOCK tier |
| `PHOTO_PRUNE_MAX_FRACTION` | 0.5 | photo prune safety |

The thresholds were deliberately tuned in `audit/05_sweep_reliability.md`
against HCSO's real behavior. Sentry observes them; it does not move them.

## Test posture

- The pytest suite stays at 173 tests, fully offline.
- `_init_sentry()` is reachable only from `scraper.sweep.main()`, which
  tests never call. They import individual symbols
  (`sweep.run`, `sweep._fetch_one`, `sweep._read_surnames`,
  `sweep.PHOTOS_DIR`, etc.) directly.
- The capture helpers (`_sentry_capture_message`,
  `_sentry_capture_exception`, `_sentry_set_tag`) each guard their
  `sentry_sdk` import inside a `try/except ImportError`. Tests that
  happen to trip an instrumentation point will silently no-op.
- Local dev (`python -m scraper.sweep --dry-run` from a contributor's
  laptop without `JCSTREAM_SENTRY_DSN`) behaves identically to before.

## Rollback

Three reversible steps, each independent:

1. **Operator wants telemetry off but keeps the code:** delete the
   `JCSTREAM_SENTRY_DSN` secret. No code change.
2. **Operator wants the instrumentation gone but keeps the dep:** remove
   the `_init_sentry()` / `_sentry_capture_*` / `_sentry_set_tag` calls
   from `scraper/sweep.py`. Tests stay green.
3. **Operator wants the dep removed entirely:** revert `requirements.txt`
   and remove the `JCSTREAM_SENTRY_DSN` env var from `sweep.yml`. Tests
   stay green.

## Confidence and limitations

- The `sweep.photo_prune.skipped` event recomputes the skip condition
  from outside `prune_photos`. The check reads the same filesystem that
  `prune_photos` is about to read, but they are not atomic — a process
  racing to add/remove `data/photos/*.jpg` between the two reads could
  in principle desync. In practice the sweep is the only writer to that
  directory and runs serially under the workflow's concurrency group.
- `JCSTREAM_SENTRY_DSN` is a secret, not a variable. GH Actions does not
  expose secret values in workflow logs even when echoed, but the env
  var would still be readable inside the `python -m scraper.sweep`
  process. That is fine for our threat model (the runner is trusted).
- We do not pin the Sentry transport (default HTTPS) or set a custom
  before_send hook. If Sentry's hosted SaaS were ever to outage during
  a sweep, capture_* calls fall through to the SDK's local buffer and
  the sweep keeps running.

## Owner-side activation (one-time)

The code wiring is complete but the DSN secret must be set by the repo
owner. The Sentry MCP token in this session does not have project-create
permission on the `aicincy` org (HTTP 403 "Your organization has disabled
this feature for members"). The owner has admin-level access to the
dashboard and should do the following.

### Step 1: create the Sentry project

1. Sign in to https://aicincy.sentry.io.
2. Open Projects -> Create Project. Direct URL:
   https://aicincy.sentry.io/projects/new/
3. Pick platform = **Python**, team = **aicincy**, name = **jcstream-sweep**.
   The slug becomes `jcstream-sweep`.
4. Skip the SDK install walk-through; the SDK and instrumentation are
   already in this repo.
5. Copy the DSN from the "Configure Python SDK" page. It looks like
   `https://<key>@o<org-id>.ingest.us.sentry.io/<project-id>`.

### Step 2: set the GitHub Actions secret

1. Open Repo -> Settings -> Secrets and variables -> Actions -> Secrets.
   Direct URL: https://github.com/AICincy/JCStream/settings/secrets/actions
2. Click **New repository secret**.
3. Name: `JCSTREAM_SENTRY_DSN`. Value: paste the DSN from Step 1.5.
4. Click **Add secret**.

### Step 3: smoke-test the wire

1. Open Actions -> sweep -> **Run workflow** (the workflow_dispatch
   trigger that already exists at sweep.yml).
2. Watch the sweep complete. Two outcomes are possible:
   - **Clean sweep**: no Sentry event captured. This is the normal case
     and indicates the wire is working; the SDK is initialised and the
     thresholds simply did not trip. Verify init by looking for the
     first-line `sentry.init` debug log near the top of the workflow
     output (only emitted at DEBUG; absence is not a problem).
   - **Degraded sweep**: a `sweep.degraded.*` event appears in the
     Sentry project's Issues view. If the source roster was unhealthy
     at the moment you ran the workflow, this is expected and proves
     the wire is end-to-end functional.

### Step 4 (optional): create alert rules

In the Sentry project, define Alert Rules that match:
- `event.message:sweep.degraded.roster_floor` -> page (Slack/email).
- `event.message:sweep.degraded.surname_errors` -> page if it fires
  twice within two consecutive sweep cycles. A single bad cycle is
  routine; sustained errors indicate an HCSO source-system change.
- `event.message:sweep.detail_watchdog_tripped` -> page if `blocked=true`.
- Unhandled `event.type:error` -> page immediately.

### To turn off

Delete the `JCSTREAM_SENTRY_DSN` secret. No code change required;
`_init_sentry()` reads the env var on every workflow invocation.

End of report.
