# JCStream: working notes for Claude

JCStream is a static public-records mirror of the Hamilton County, Ohio Justice
Center inmate roster. A Python script (`web/build.py`) regenerates `docs/` from
`data/current.json` on a GitHub Actions cron scheduled twice per hour at :07
and :37 UTC with a 20-minute skip-gate (`.github/workflows/sweep.yml` cron
`7,37 * * * *`). Effective cadence is roughly 30 minutes when both starts are
delivered; during incidents, GitHub Actions can still delay or drop runs.
The sweep also runs the HCSO scraper
(`scraper/`) and pulls the Cincinnati Open Data feeds (nine as of 2026-07:
three dedicated parsers plus the six-feed registry in `open_data_feeds.py`).
Live at https://www.aretheyinjail.com (GitHub Pages, custom domain; build uses
`JCSTREAM_SITE_BASE_URL=""` and the Pages custom-domain setting).

## Project specialists

`.claude/skills/` and `.claude/agents/` ship ten paired specialists for the
recurring domains in this repo: templates, CSS, build helpers, ORC data,
scraping, tests, design ports, legal copy, accessibility, and sweep
debugging. They auto-discover in any Claude Code session; ask for one by
name (e.g. "have the jcstream-template-author …") or by describing the
task ("update the FCRA disclaimer" routes to `legal-copy-author`). See
`.claude/skills/README.md` for the index and the handoff topology.

## Chain of Custody: Session IDs

Court-evidence Claude Code session IDs. Filings under ORC 149.43 cite these
sessions as the record of Claude-assisted work on this repository. Preserve
verbatim. Do not abbreviate. Do not redact. Do not reformat.

| Session ID | Date range [VERIFY] |
| :-- | :-- |
| session_01Hbc6p9EspF6RH9ajNNb8tB | [VERIFY] |
| session_01MNnYgZMY5uFz9cHie3w6TY | [VERIFY] |
| session_019fDevbfpgmnjJP7A343T95 | [VERIFY] |
| session_01NGMSLESEepbgV8aSn4reVG | [VERIFY] |
| session_019qfYLXARs48orCHaQdM8cA | 2026-07-02 [VERIFY] |
| session_01DCTmLdgUma5GYA1JBrywGp | 2026-07-03 [VERIFY] |
| db5bf8bb-9850-49f0-8f3d-1c6abfa5a05e (local Claude Code session) | 2026-07-05 (confirmed from filed transcript) |

Authoritative storage location: `audit/sessions/` in this repository
(designated 2026-07-02; ledger and filing procedure in
`audit/sessions/README.md`). The local session transcript (db5bf8bb) was
filed 2026-07-23. The six claude.ai session transcripts are **not yet
filed**; until they are, they exist only in the owner's claude.ai session
history, and a court submission citing those IDs must say so. Note: the
claude.ai account data export does NOT contain claude.ai/code session
transcripts (verified against both accounts' exports 2026-07-23); each must
be exported from inside the session UI. The 2026-06-16 code review flagged
the undocumented location as a Critical finding. See
`audit/code-review-2026-06-16/00-summary.md`.

Retrieval procedure:

1. Sign in to the account that owns the session.
2. Open https://claude.ai/code/<session_id>.
3. Export the transcript.
4. File it in `audit/sessions/` as `<session_id>.md`.
5. Replace the date-range [VERIFY] tags here and in the
   `audit/sessions/README.md` ledger with the confirmed dates.

## Hard constraints (violations are accessibility failures, not style issues)

The owner has AuDHD. These rules are medical accessibility accommodations.
Violating them imposes cognitive cost the owner cannot afford.

### Scope gate
- Before writing any code, state what you think the task is in one sentence.
  Wait for confirmation. Do not infer multi-step projects from ambiguity.
- Do not create multi-phase plans. One task, one fix, confirm before the next.
- Do not modify CSS, templates, or website design without explicit per-session
  authorization. The default work is scraper/pipeline maintenance.
- Match the scope of the fix to the scope of the problem. A one-line bug gets
  a one-line fix. Do not refactor surroundings, add error handling for
  impossible cases, or "improve" adjacent code.

### Communication rules
- Do not ask clarifying questions unless ambiguity risks material error
  (wrong file, wrong jurisdiction, wrong recipient). If the task can be
  inferred from context, execute. State the assumption inline.
- When wrong: one sentence acknowledging, one sentence correcting, re-execute.
  No extended apology. No multi-sentence self-criticism.
- No filler phrases. No softening register. No "you may want to," "if that
  doesn't work," "perhaps consider." Start with the content.
- No em dashes or en dashes. Tables for 3+ items. One idea per sentence.
  Active voice. Dense layouts.

### Execution rules
- Use direct tools (Read, Write, Edit) instead of writing shell scripts for
  the owner to run. The direct tool is the default. If it fails, report the
  error and try the indirect path.
- You have full filesystem, git, and network access. Do not claim otherwise.
  If an operation fails, report the failure. Do not preemptively refuse.
- If a tool can do the action, do it. Do not say "left to you" / "you can
  run X" / "delete the branch yourself" / "go push this commit" when you
  have Bash, Edit, Write, and MCP tools. Punting actions back to the owner
  is the same cognitive cost as not having tools at all. The only
  exceptions are the irreversibly-destructive ones already flagged
  elsewhere (force-push, branch delete that loses work, etc.); for those,
  confirm and then execute, do not delegate.
- Run `python -m pytest -q` before committing. If tests fail, fix them.
  Do not commit with failing tests.
- Verify the live site (`curl` it) before claiming anything about how it
  looks. Do not guess. Ask for a screenshot when the owner says "broken".
- Do not trust compaction summaries over source files. When referencing any
  file's content, re-read the file. Do not rely on your own prior summary.

### Menu system
- **Don't make the owner think of the options.** Whenever a chunk of work
  wraps up (and any time work *could* continue), END THE TURN with the
  AskUserQuestion tool (multiSelect): a *comprehensive* menu of next steps
  with *truthful* recommendations. Say which I'd actually do and why, and
  which are marginal/skip, so the owner can accept items **individually,
  all, or none**. Don't just summarize and stop; don't keep building past
  the obvious-in-scope work without surfacing the menu first.
  "Implement all suggestions" means: do everything in the last menu I
  offered, so there must always be one.
- **Never offer "stop here" / "do nothing" / "reject the work" / "close the
  branch" as a menu option, and never tag any option as "recommended:
  stop".** Stopping is always implicitly available; surfacing it as an
  explicit choice biases toward inaction and reads as you trying to wind
  the session down. If the honest answer is "this is finished," say so in
  text; do not put it on a button. Menu options should all be forward
  motion.

### General
- Keep replies short. Don't re-litigate settled things. Don't nag about
  branches/PRs. This is a from-scratch solo repo; `main`/PR ceremony is moot.

## Repo facts

- Push target / dev branch: a per-task `claude/<slug>` branch. Claude runs
  the PR process end to end (owner directive, 2026-07-23): branch, push,
  open the PR, merge it via the REST API, delete the branch. The owner does
  not merge. Direct pushes to `main` stay off-limits; land everything
  through a PR merge.
- `data/surnames.txt` is A-Z single letters on purpose (HCSO's last-name search is a
  substring match, so 26 letters cover the whole roster with dedup). Don't revert.
- Build locally: `JCSTREAM_SITE_BASE_URL="" python -m web.build`
- Force a sweep now instead of waiting for the cron: dispatch `sweep.yml`.
  
  **Option A** (if token has `actions:write` scope):
  ```bash
  gh workflow run sweep.yml -r main
  ```
  
  **Option B** (via GitHub UI, no token required; recommended):
  1. Go to https://github.com/AICincy/HCJC/actions/workflows/sweep.yml
  2. Click "Run workflow" → Branch: main → Run
  3. Watch the job start within 30s
  
  The 20-minute skip-gate still applies: the run no-ops if `current.json` is 
  younger than 20 minutes. If Option A returns 403 (Forbidden), your token
  lacks `actions:write` scope; use Option B (UI) instead.

  A 403 means missing **scope**, not a dead credential. Measured 2026-09-24
  after PR #504 merged and GitHub deleted the branch: the same bot token still
  performed REST reads, `git fetch`, `git push` (recreating the branch), and PR
  create/edit. Merging a PR does not revoke it. What it cannot do is dispatch
  workflows (`actions:write`) or comment on issues (`issues:write`) -- both 403.
  See the capability matrix in `audit/25_pages_stale_artifact_misdiagnosis.md`.

  Verified: UI dispatch always works (owner-initiated); CLI dispatch is
  conditional on token scope (verified 2026-09-24).

- Tests: `python -m pytest -q` (must stay green; >=464 tests as of 2026-07-09, suite grows).

**Session lifecycle note**: an agent token's *scope* is narrower than its
*lifetime*. After a merge it can still read, fetch, push branches and open PRs;
it cannot dispatch workflows or comment on issues (both 403). So hand dispatch
and issue comments to the owner, and do not diagnose a 403 as a revoked
credential -- verified 2026-09-24, `audit/25_pages_stale_artifact_misdiagnosis.md`.

Do NOT force-push main to trigger a Pages deployment. It rewrites published
history, it does not make a webhook fire, and force-pushes on `main` are blocked
in branch protection. Same rule in `runbooks/live-parity-failure.md` §4.3: never
hand-edit `docs/` or force-push generated output. Use UI dispatch, and do not
assume the cron is hourly -- it drifts 3.5-5.5h in practice.

- `backend/` is the **only** component that talks to Supabase, and the only
  place a Supabase credential is read. It is Node (`@supabase/server`),
  independent of the Python pipeline. Run it with `npm ci && npm start` from
  `backend/`. The `.env` for local dev is `.env.example` renamed (no secrets
  committed); `NODE_ENV=production` on deploy. No Python process talks to
  Supabase.

### Runbook: roster frozen / "no new inmates" (HCSO WAF block)

Signature: `data/current.json` (and `data/changelog.json`) stop changing while
the sweep keeps committing the open-data feeds + `docs/` every cycle. Both
freeze at the same `generated_utc`. The degraded-roster guard is firing every
run and keeping last-good data. This is the guard working, not a bug.

1. Confirm: `git log -15 --format="%cI %s" origin/main -- data/current.json` -
   if `current.json` hasn't changed in hours but `sweep` commits keep landing,
   it's frozen.
   You'll usually hear about it first from the auto-opened GitHub issue
   ("Roster frozen: HCSO sweep is not updating current.json", from
   `scraper.freeze_alert`) once the freeze passes `ROSTER_STALE_ALARM_HOURS`.
2. Diagnose from the Actions sweep log (grep, in order):
   - `ROSTER FROZEN` / the `::error::` "Roster frozen" annotation - the freeze
     alarm (`roster_stale_hours` >= `ROSTER_STALE_ALARM_HOURS`, 6h), emitted by
     the "Roster freeze alarm" step (`scraper.freeze_alert`) in `sweep.yml`.
   - `list sweep looks degraded (prev=... seen=... N/M surname fetches failed)` -
     the guard fire. `N/M > 2/26` => WAF raising on fetches; `seen < 50% of prev`
     => WAF serving empty-but-parseable pages.
   - `WAF-block-shaped response for id=...` / `429 ...` => WAF active.
3. Cause is almost always HCSO's WAF blocking the GitHub Actions egress IP.
   Code can't fix that. **Posture (2026-05-20): document the block, do not
   evade it.** A clean, persisting, documented denial supports the ORC 149.43
   mandamus record; evading it would weaken that. Each blocked cycle + each
   recovery is recorded in `data/waf_block_log.json` (see `audit/14_hcso_waf.md`),
   and the site surfaces an interruption notice. Options, in order:
   - **Do nothing but wait** for the block to rotate (cloud WAFs commonly
     24-72h); the evidence log keeps growing, which is the point.
   - The `JCSTREAM_HTTP_PROXY` repo secret routes HCSO fetches through an egress
     proxy (HTTP/HTTPS/SOCKS), unset = direct, scoped to HCSO. It is kept
     available but is **deliberately left unset** while the mandamus record is
     built. Use it only on an explicit decision to prioritize data over the
     denial record.
   - Run from a
     self-hosted runner, or contact HCSO for allowlisting.
4. NEVER lower `SWEEP_MAX_FAILED_FRACTION` (0.10) or `SWEEP_MIN_ROSTER_FRACTION`
   (0.5) to force the sweep through - that publishes a partial roster as if
   complete, which is worse than stale data. Tuning `crawl_delay` / `concurrency`
   in `client.py` only helps if errors are borderline (~3/26), not a hard block.

## Design and implementation decisions

### Sweep (scraper/)

#### Dedup, photo caching, and rebooking (C-0)

- The sweep writes `data/current.json` (roster snapshot) and `data/changelog.json` (events) alongside append-only evidence.
- `current.json` is deduplicated (list-row + detail-page combos yielding one inmate per booking).
- Photographic evidence (booking photos) is cached locally: a corrupt or truncated image during WAF throttle is never overwritten by a good one that arrives later. `scraper/parsers.py:photofrom_detail` validates JPEG headers (HCSO labels as PNG but serves JPEG). Cache miss means the slot is empty; we do not fall back to a placeholder.
- **Rebooking rule** (C-1): if an inmate already has a `booking_date` and today's fresh list row shows a different `admit_date`, the detail page is force-refetched. This wins a more recent photo when the person cycles through multiple bookings same-day. If the fresh photo is corrupt, the cached one is preserved.

#### Safety gates (C-2)

- **Collapse guard**: roster size collapses > 50% → abort, keep the last good snapshot.
- **Surname-query guard**: if A-Z letter-search failure rate exceeds 10%, abort.
- **Name-extraction watchdog** (C-3): if detail-page name parsing degrades (see below) → warn, may not block.
- **Photo-pruning guard**: if cache cleanup would delete > 50% of photos, abort. (Corrupt or expired data is marked for deletion; this guard prevents a bad purge from wiping the whole cache.)
- Low-volume bypass (C-4): watchdogs are disabled below `DETAIL_WATCHDOG_MIN_SAMPLE` and `DETAIL_DEGRADED_MIN_SAMPLE` so a first tiny run doesn't fail its own guards.

#### Name parsing: the five-tier fallback (C-5)

Detail-page HTML from HCSO is not structured; names appear in many places. Parser tries these in order, stopping at first hit:
1. Inmate-detail heading `<h1>` or `<h2>`.
2. OpenGraph `og:title` meta tag.
3. Container text (body of a `<div>` on the detail page, heuristic match).
4. Labeled cell text (table cell next to a label like "Name:").
5. Page `<title>` tag (worst-case fallback).

Degradation is tracked per tier (C-6): if tier-N hits exceed tier-N-1 hits unexpectedly, the watchdog fires. Exact thresholds in `sweep_guards.py`.

#### Dispatch-to-arrest correlation (C-7)

Runs offline on local files (no network, no HCSO load). Matches Cincinnati 911 dispatch records (CPD "calls for service") to HCSO arrests using:
- Last name, first name, DOB fuzzy match.
- 60-minute call-to-arrest window.
- Confidence floor 0.45 (tuned conservatively).
- Candidate pairs only; join data is never published on profiles.

#### WAF backoff and block logging (C-8)

- HCSO's WAF throttles HTTP requests from cloud infra.
- Sweep honors `Retry-After` headers (up to 30 s).
- Exponential backoff: 2 s start, 30 s cap.
- Every block is logged to `data/waf_block_log.json` (append-only SHA-256 chain).
- No proxy rotation or evasion (document, don't evade).
- Egress IP recorded on block (evidence of cloud execution; see `scraper/egress_ip.py`).

#### Cincinnati Open Data feeds (C-9)

Swept as part of the same pipeline (same run):
- Calls for service (rolling 30 days, 1 h cache).
- Police long-term incident feed (longer rolling window).
- Reported shootings (6 h cache).
- Supplemental registry (traffic stops, pedestrian stops, citizen complaints, use-of-force).

Collapse guards warn but do not block the roster write; a single broken feed doesn't fail the whole pipeline.

#### Append-only WAF evidence log (C-10)

`data/waf_block_log.json` is legal evidence of WAF blocks encountered during sweeps. Each row is SHA-256-linked to the previous one. Never edit by hand. The chain is verified on every CI run. If the chain breaks, the entire log is treated as suspect and an alert fires. Session identifiers are preserved (audit trail). Published copy lives at `/data/waf_block_log.json` on the live site.

### Web (web/)

#### Build mode: deterministic, reproducible, offline

Build (`web/build.py`) is deterministic. Given the same `data/` inputs, consecutive runs produce byte-identical `docs/` output. No randomness. No external API calls. All reference data is precomputed (`data/orc_caselaw.json`, `data/courtclerk_cases.json`).

Build steps:
1. Validate `data/current.json`, `data/changelog.json`, etc. (Pydantic schemas).
2. Shape data (transform for presentation).
3. Render Jinja2 templates into static HTML.
4. Minify and publish `docs/`.
5. Write `docs/data/` (JSON, search index, feeds).
6. Generate `docs/SHA256SUMS` (for verification).

#### Per-inmate detail pages

`docs/inmate/<id>/index.html` rendered from `web/templates/inmate.html` + per-inmate context.
Context includes:
- Booking snapshot (name, charges, custody days).
- Bond info (amount, percentile vs peers, stats).
- Court calendar (next scheduled appearance, past dates).
- Dispatch correlation (if a match exists, candidate pair only).
- Recent events (booked/released in last 24 h).
- Mugshot (if available).
- Presumption-of-innocence notice.
- Free correction/removal workflow.
- Accessibility: full keyboard nav, semantic HTML, ARIA roles, dark theme.

#### Classification and charge tiers (C-11)

`scraper/classify.py` maps ORC sections to tiers: Felony F1–F5, Misdemeanor M1–M4, Minor Misdemeanor MM, Unknown.
Collapsed tiers: 2905 → 2903, 2914/2915 → 2913 BEFORE template class names are built. Selectors targeting raw chapters 2905/2914/2915 are dead code.

#### Sentinel dates (C-12)

HCSO uses `1/1/70` (Unix epoch 0) as a no-date sentinel; treated as unknown. Dates > 15 years in the past are blanked on profile pages (privacy). Two-digit years pivot per Python `%y` (69–99 map to 1969–1999, 00–68 to 2000–2068); dates > 1 year in the future are rejected as garbage (data-entry error).

#### Court calendar view (C-13)

Buckets: today / tomorrow / this_week / this_month. `_next_court_date` returns the earliest future charge date, falling back to most recent past date (labeled "Last known court date" on profiles).

#### Bond statistics (C-14)

Bond spread (Q3/Q1 interquartile ratio) computed per charge tier. Individual percentile is `below / len(peers)` (fraction of same-tier bonds strictly below theirs). Outliers are surfaced, not hidden.

#### Privacy and publication (C-15)

- No public historical archive of released individuals; they drop off-site on next update.
- Anonymized long-term history: `data/anon_changelog.json` scrubs names/IDs after 7 days, compacts entries > 1 year into monthly summaries.
- No per-person social preview cards; site-level OpenGraph only.
- `noindex, noarchive` on every page.
- No tracking, no ads, no third-party scripts.
- Free corrections, sealing/expungement removals, and privacy requests (open an issue).
- FCRA disclaimer: this site does not furnish consumer reports as defined in 15 U.S.C. 1681a(d)–(f). Do not use for credit, insurance, employment, housing, tenant screening, or any 1681b purpose.

### Deployment and CI

#### Pages deployment flow

Pages is configured as Settings > Pages > Source = **"Deploy from a branch"**
(`build_type=legacy`), branch `main`, path `/docs`. GitHub therefore serves the
`docs/` tree **exactly as committed** -- it does not clone the repo and run
`web/build.py`. Nothing is built at deploy time.

1. `sweep.yml` scrapes HCSO, runs `python -m web.build` **into `docs/`**, and
   commits `data/` + `docs/` to main.
2. The push triggers GitHub's built-in `pages-build-deployment`, which publishes
   the committed `docs/` tree (typically < 2 min; observed 28-36s).
3. `pages.yml` additionally builds a verified artifact and deploys it through the
   `github-pages` environment. It is a secondary path: it only serves the site if
   an admin flips Pages Source to "GitHub Actions". Do not flip `build_type` from
   an agent -- the settings API needs admin, and the 2026-07-04 experiment left
   the site unable to publish when the Actions deploy failed GitHub-side.
4. The custom-domain CNAME points `www.aretheyinjail.com` at the Pages host.

**The consequence that matters:** because GitHub publishes committed `docs/`,
a workflow that builds into `/tmp` and commits only `data/` produces a *green*
`pages-build-deployment` that republishes a frozen `docs/` skeleton while main's
roster moves on. That is the root cause of the recurring "Site deploy is stale"
alerts (issues #483, #487, #496) -- not a failed or stuck webhook. `sweep.yml`
and `rebuild.yml` must build into `docs/` (the default `--out`) and commit both
paths; `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs`
enforces it.

Pages deployment usually completes in < 5 min. Outliers (> 90 min) trigger an
alert; see below.

### Pages deploy: branch-serving is the live path (as of 2026-09-24)

Pages currently serves `docs/` via Settings > Pages > Source = "Deploy from a
branch" (`build_type=legacy`). Every push to main triggers GitHub's built-in
`pages-build-deployment`; the committed `docs/` tree is the live site.

`sweep.yml` and `rebuild.yml` MUST build into `docs/` (default out) and commit
both `data/` and `docs/`. A `/tmp`-only build that commits only `data/` leaves
the live site frozen on the last committed `docs/` skeleton while main's
roster stays current. That is the real root cause behind the recurring
"Site deploy is stale" alerts (issues #483, #487, #496), not a failed
`pages-build-deployment` job. Those jobs often report success while publishing
the stale skeleton.

`pages.yml` still builds a verified artifact and can deploy when the Pages
source is "GitHub Actions". Do not flip `build_type` from this agent: the
Pages settings API requires admin, and the 2026-07-04 experiment left the site
unable to publish when Actions deploy failed GitHub-side. Keep branch-serve
working; treat `pages.yml` as a secondary path until an admin confirms the
source flip and a green Actions deploy.

If a `pages-build-deployment` run itself fails with
`##[error]Deployment failed, try again later`, re-run the failed job
(`rerun_failed_jobs`). Transient GitHub-side rejections self-heal on the next
successful sweep push that includes a fresh `docs/`.

### Pages deploy stuck in deployment_queued

The "pages build and deployment" run occasionally sits in
`deployment_queued` for many minutes while githubstatus.com says Pages is
operational. This is GitHub-side queueing. Do not chase it: the artifact
is already built, the site keeps serving the previous deploy, and the next
sweep triggers a fresh deploy that supersedes the stuck one.
Only investigate if the live `Generated` timestamp lags main by more than
two sweep cycles.

#### If Deployment Lags > 90 min

**Note**: Do NOT use `git push -f` (force-push). It rewrites history and 
doesn't fix the GitHub Pages webhook issue. Instead, trigger the next sweep 
or check GitHub status as shown below.

1. Check https://github.com/AICincy/HCJC/actions
2. Look for `pages-build-deployment` workflow
3. First establish *which* lag this is -- they have different fixes:
   - **Roster age**: `data/current.json:generated_utc` is itself old. No sweep has
     run; the deploy is fine and there is nothing newer to publish. Dispatch a sweep.
   - **Stale published artifacts**: the deploy succeeded but shipped an old `docs/`.
     Compare `docs/data/transparency_metrics.json:computed_utc` with
     `data/current.json:generated_utc`; a mismatch means `docs/` was built by older
     code. Regenerate and commit `docs/` (see "Deterministic Build Contract").
   - **Genuinely stuck deploy**: rare. Continue below.

   Then trigger a sweep:
   - **Dispatch manually via UI** (owner; reliable):
     https://github.com/AICincy/HCJC/actions/workflows/sweep.yml → "Run workflow"
   - **OR via CLI** (if the token has `actions:write`):
     ```bash
     gh workflow run sweep.yml -r main
     ```
   - Waiting for the cron is the *last* resort, not a one-hour wait: `sweep.yml`
     declares `0 * * * *` but observed gaps on 2026-09-23/24 were 3.5-5.5h
     (starts `05:37, 11:01, 16:22, 20:00, 23:27Z`). Actions cron is best-effort.

4. If stuck > 120s: Build likely timed out or queued
   - Do NOT cancel + force-push (loses history)
   - Wait 10+ min (queues self-heal)
   - If still stuck: Check runbook below

5. If failed: Check logs → fix issue → commit via normal PR → wait for sweep

6. Full runbook: `runbooks/live-parity-failure.md`

7. Verify live:
   ```bash
   curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc
   curl -s https://www.aretheyinjail.com/ | grep -i "last updated"
   gh run list --workflow pages --limit 3
   ```

### Live-Parity HTML Freshness SLA (added 2026-09-24, audit 5dc39f0)

Every rendered HTML page carries a machine-readable roster vintage:

```html
<meta name="jcstream:generated-utc" content="2026-09-23T23:35:42Z">
```

And a human footer:

```html
Last updated: <time datetime="2026-09-23T23:35:42Z">Sep 23, 2026, 7:35 PM ET</time>
```

The value is `data/current.json:generated_utc`, never wall-clock during template rendering. Transparency metrics and timeline are also anchored to this vintage for deterministic builds (Option B, issue #502).

#### Deployment Freshness Check
```bash
python -m scraper.deploy_alert
# Output: "deploy fresh <X> min" or "deploy stale <X> min"
# X < 5 min: ✅ OK
# 5-90 min: ⚠️ Warning (monitor closely)
# > 90 min: 🔴 Alarm (incident response required)
```

#### Scheduled Validations

**Daily**: Automated monitoring (planned for next sprint)
```bash
# (via .github/workflows/deployment-monitor.yml)
# Runs every 6 hours; alerts on Slack/PagerDuty if lag > 30 min
```

**Manual Spot-Checks**: 3 pages, 3 times per week
```bash
for url in "https://www.aretheyinjail.com/" \
           "https://www.aretheyinjail.com/inmates/" \
           "https://www.aretheyinjail.com/reports/"; do
  curl -s "$url" | grep "jcstream:generated-utc" | head -1
done
# All should show timestamps < 1 hour old
```

**Weekly**: Monday 04:40 UTC scheduled parity gate
- Runs `live-parity.yml` workflow (2 jobs: JSON contract + HTML freshness)
- Probes https://www.aretheyinjail.com/ representative pages:
  index.html, data/index.html, help/index.html, stats/index.html, transparency/index.html
- Validates strict UTC Z timestamps, microsecond precision, rejects malformed/offset/missing/future/epoch
- Fails closed on 404/500/TLS/timeout, redirects, candidate-regression
- Threshold: lag <= 26h pass, >26h fail
- See: `runbooks/live-parity-failure.md` if it fails
- Gate: `live-parity.yml` scheduled `40 4 * * 1` (Monday 04:40 UTC)

#### If Deployment Lags > 90 min

1. Check https://github.com/AICincy/HCJC/actions
2. Look for `pages-build-deployment` workflow
3. If missing: Webhook misconfigured → re-run `sweep.yml`:
   ```bash
   gh workflow run sweep.yml -r main
   ```
4. If stuck: Build timed out → cancel it, re-run
5. If failed: Check logs → fix issue, commit, re-run sweep
6. Full runbook: `runbooks/live-parity-failure.md`
7. Verify live:
   ```bash
   curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc
   curl -s https://www.aretheyinjail.com/ | grep -i "last updated"
   gh run list --workflow pages --limit 3
   ```

#### Deterministic Build Contract

- `docs/data/transparency_metrics.json:computed_utc` == `data/current.json:generated_utc` (anchored, not wall-clock)
- `freshness_hours` == `generated_utc - last_healthy_sweep_utc` (0 when healthy)
- Timeline `now_x` and `days_in_custody` anchored to `generated_utc` via `set_build_now_from_utc`
- Consecutive builds with identical inputs produce byte-identical `docs/` (verified: `diff -qr /tmp/docs-run-1 docs` empty)
- See issue #502 for Option B rationale.
- Enforced by `tests/test_build_determinism.py`, which asserts the
  `computed_utc` / `generated_utc` equality against the **committed** `docs/`, and
  that `web/build.py` anchors the clock before `_render_build(...)` and clears it
  after. Added because PR #503 merged the fix while the committed `docs/` had been
  generated by pre-fix code, so branch-serve published unanchored artifacts with
  every gate green (`audit/25_pages_stale_artifact_misdiagnosis.md`).

#### Deterministic Build Contract

- `docs/data/transparency_metrics.json:computed_utc` == `data/current.json:generated_utc` (anchored, not wall-clock)
- `freshness_hours` == `generated_utc - last_healthy_sweep_utc` (0 when healthy)
- Timeline `now_x` and `days_in_custody` anchored to `generated_utc` via `set_build_now_from_utc`
- Consecutive builds with identical inputs produce byte-identical `docs/` (verified: `diff -qr /tmp/docs-run-1 docs` empty)
- See issue #502 for Option B rationale.
- Enforced by `tests/test_build_determinism.py`, which asserts the
  `computed_utc` / `generated_utc` equality against the **committed** `docs/`, and
  that `web/build.py` anchors the clock before `_render_build(...)` and clears it
  after. Added because PR #503 merged the fix while the committed `docs/` had been
  generated by pre-fix code, so branch-serve published unanchored artifacts with
  every gate green (`audit/25_pages_stale_artifact_misdiagnosis.md`).

### Optional features (owner-side setup, not something I can do from here)

- **Giscus comments** on inmate pages (`web/templates/inmate.html` renders the
  policy block always, and the Giscus widget when `giscus.repo_id` is set):
  1. Repo -> Settings -> General -> Features -> enable **Discussions**.
  2. Create a Discussions **category** to hold the threads (e.g. "Announcements"
     or a new "Records" one). Note its name.
  3. Install the **Giscus GitHub App** (<https://github.com/apps/giscus>) and
     grant it access to `AICincy/JCStream`.
  4. Go to <https://giscus.app>, enter `AICincy/JCStream`, pick the category;
     it prints `data-repo-id` and `data-category-id`.
  5. Repo -> Settings -> Secrets and variables -> Actions -> **Variables**: add
     `JCSTREAM_GISCUS_REPO_ID`, `JCSTREAM_GISCUS_CATEGORY_ID` (and optionally
     `JCSTREAM_GISCUS_REPO`, `JCSTREAM_GISCUS_CATEGORY` to override the defaults).
  6. Next sweep rebuilds with the widget live. To turn it off, clear the vars.

## Git workflow

### Merge discipline

- One logical change per PR. Claude merges its own PRs via the REST API
  once verification passes (owner directive, 2026-07-23); the owner does
  not merge. Never queue commits on a PR after merging it.
- BEFORE pushing additional commits to a PR branch, check whether the PR
  already merged (the GitHub PR tools; `gh pr view <n> --json state` where
  gh is available). A merged-while-pushing race (PR #360) silently dropped
  three commits from main; PR #361 was the recovery.
- After every merge the remote branch is deleted. `--force-with-lease`
  then fails with "stale info". Fix:
  `git update-ref -d refs/remotes/origin/<branch>` then plain push.
  Always restart the branch from origin/main, same branch name.

### Build artifacts

- `git checkout -- docs/ data/` does NOT remove newly created untracked
  files. After any local build, check `git status` for `??` entries
  before `git add -A`. A 237k-line generated JSON was once committed
  this way and had to be amended out.

## Testing

### Evidence-log isolation (conftest.py)

- `waf_block_log.json` is an ORC 149.43 evidence artifact. The test suite must never write to it. Verified clean
  2026-07-02 at 447 passing tests.
- Isolation pattern: wrap `store.append_block_evidence` in conftest.
  Do NOT patch `store.WAF_BLOCK_LOG_PATH`; module paths bind at def
  time and patching desyncs the chdir-isolated
  `test_roster_stale_context` (this broke once and shipped).
- Any NEW production writer with a `data/`-relative default path
  requires a matching conftest wrap before merge.

## Frontend / CSS conventions

### Class and token rules

- classify.py collapses cls 2905->2903 and 2914/2915->2913 BEFORE template
  class names are built. Selectors targeting raw chapters 2905/2914/2915
  are dead code. Review bots flag their absence as a bug; it is not.
  The token comment in style.css explains this; rebut on-thread.
- Token aliasing is prohibited. The print `:root` overrides `--accent`
  and `--surface` independently, so `--warn: var(--accent)` style
  aliasing recolors print output. See the note at the top of the token
  block.
- main.js constructs class names dynamically (`'sr-' + tier` yields
  sr-felony/sr-misdemeanor/sr-x). Grep for the prefix AND the
  construction site before deleting any "unused" class. A purge round
  once deleted these wrongly.
- Card category hook is `data-chap="<slug>"` emitted by _card.html from
  `_chap_slug` (web/shape/inmates.py). Cards carry no per-category
  class. Verify the slug list against `_chap_slug` before writing any
  `[data-chap=...]` selector.
- Card data-* contract (2026-07-09), all from `_card_data_attrs` unless noted:

  | attr | value | note |
  | :-- | :-- | :-- |
  | data-tier | felony / misdemeanor / unknown | description+venue based |
  | data-degree | F1..MM or UNK | ORC-resolved like the tier strip; deliberately MORE precise than the corner badge |
  | data-custody | days int or "" | "" sorts last |
  | data-recent | "booked" or absent | changelog 24h window; template reads the `recent_booked_ids` env global |
  | data-search | lowercased name+charges+ORC+#id | name sort key uses its prefix |

- The tier select mixes kinds (felony/misdemeanor -> data-tier) and degrees
  (F1..MM -> data-degree); `DEG_VALUES` in main.js routes them. Do not
  "simplify" the select to one attribute.
- `#sort-bin` is a server-rendered empty `section.month`. JS sort modes
  reparent every card into it; "newest first" restores original parents.
  Its `class="month"` is load-bearing (`.month > .cards` grid padding and
  `body.is-table` row rules are scoped to `.month`).
- `mark.hl` is the search-match highlight. Its background is a literal hex
  (#F2E29B) on purpose; see the token-aliasing rule above.
- `recent_booked_ids` / `recent_released_24h` env globals are registered in
  `build()` (not `_register_template_helpers`) because they derive from
  changelog events, with empty defaults registered in the helpers for
  env-only renders.

### Runbook: local screenshot flow

- `cd docs && python3 -m http.server 8899 --bind 127.0.0.1 &`, then
  playwright with `executable_path='/opt/pw-browsers/chromium'`.
- `pip install playwright` only; do NOT run `playwright install`.
- Never render over file:// (root-absolute /static links load
  unstyled). Always serve over HTTP.
- Dark is the default theme (`data-theme="dark"`, persisted in
  `localStorage` as `jcstream-theme`). Light is available from the header
  toggle. No-JS falls back to light. Screenshot the default dark theme
  plus one light-theme frame at mobile width when a visual change ships.
- Any user-visible visual change requires screenshots sent to the owner
  BEFORE the PR merges.

## Review process

### Gemini bot reviews

- **Retired (owner, 2026-07-23).** The Gemini bot is no longer active and
  its review is no longer part of the PR process. The rules below are
  historical; do not wait for or poll for Gemini comments on new PRs.
- Reviews every PR, usually 1-2 comments. Track record: sometimes right
  (cap carry-forward, breakpoint documentation, checklist wording),
  sometimes wrong (cls collapse selectors, `git clean` over the
  untracked-file check, `git fetch --prune` over `git update-ref`).
  Verify every comment against source before applying.
- Reply on-thread to EVERY Gemini comment (owner rule, 2026-07-03),
  accept or decline. Note where an accepted fix landed, or the reason for
  declining.
- The owner merges doc PRs within a minute, faster than the review lands,
  so a nit usually arrives after merge. Carry each accepted nit as a
  follow-up on a branch restarted from origin/main; do not reopen the
  merged PR. Trivial formatting-only nits may be batched into the next
  follow-up rather than spawning a PR each.
