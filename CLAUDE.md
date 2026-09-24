# JCStream: working notes for Claude

JCStream is a static public-records mirror of the Hamilton County, Ohio Justice
Center inmate roster. A Python script (`web/build.py`) regenerates `docs/` from
`data/current.json` on a GitHub Actions cron that fires every 15 minutes with a
20-minute skip-gate (`.github/workflows/sweep.yml` cron `*/15 * * * *`; the
sweep no-ops if `current.json` is less than 20 minutes old). Effective cadence
is roughly 20-45 minutes; during incidents the next-run can slip past the hour.
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

  **Option A - CLI** (only when the token carries `actions:write`):
  ```bash
  gh workflow run sweep.yml -r main
  ```
  Equivalent REST call: `POST .../actions/workflows/sweep.yml/dispatches` with
  body `{"ref":"main"}`; expect HTTP 204.

  **Option B - GitHub UI** (no token scope required; owner-initiated):
  <https://github.com/AICincy/HCJC/actions/workflows/sweep.yml> -> "Run workflow"
  -> Branch: `main` -> Run. The job normally starts within ~30s.

  If Option A returns `403 Resource not accessible by integration`, the token
  lacks `actions:write`; fall back to Option B. The 20-minute skip-gate still
  applies either way: the run no-ops if `current.json` is younger than 20
  minutes.

  Do not treat the cron as hourly. `sweep.yml` declares `0 * * * *`, but
  observed gaps on 2026-09-23/24 were 3.5-5.5h (`05:37, 11:01, 16:22, 20:00,
  23:27Z`) -- Actions cron is best-effort. Dispatch is the reliable lever when
  the roster must be fresh now.

  Agent token scope is narrower than its validity. Measured 2026-09-24 after
  PR #504 merged: REST reads, `git fetch`, `git push` of a branch, and PR
  create/edit all worked, while `actions:write` (workflow dispatch) and
  `issues:write` (issue comments) both returned 403. Merging a PR does **not**
  revoke the token, and GitHub deleting the merged branch does not either --
  pushing the branch again recreates it. Diagnose a 403 as missing scope, not a
  dead credential. See `audit/25_pages_stale_artifact_misdiagnosis.md`.
- Tests: `python -m pytest -q` (must stay green; >=464 tests as of 2026-07-09, suite grows).
- `backend/` is the **only** component that talks to Supabase, and the only
  place a Supabase credential is read. It is Node (`@supabase/server`),
  independent of the Python pipeline. Run it with `npm ci && npm start` from
  `backend/`; for local env copy `.env.example` to `.env` and use
  `npm run start:local`. The secret key lives in the repository secret
  `JCSTREAM_SUPABASE_SECRET_KEY`, never in the tree.
- `RULE-STOR-001` in `tests/test_architectural_compliance.py` keeps the Python
  side off every database, `supabase` included, so the boundary stays one-way.
  Two regression tests pin that pattern; do not widen it back.
- **Never run `npx skills add` from the repo root without checking `git status`
  afterwards.** The installer drops copies into agent-tool directories it
  guesses at. On 2026-09-22 it wrote a symlink to `data/skills/supabase-server`,
  and `sweep.yml` / `rebuild.yml` both run `git add -- data/`, so the next
  automated sweep would have pushed that stray path straight to `main`. It also
  created a root-level `agent/` duplicate. Check for and delete strays before
  committing.
- The stylesheet is cache-busted by content hash (`css_version` in build.py); don't
  key it off the data timestamp again.
- The sweep refuses to write a degraded roster (`_sweep_looks_healthy` in
  `scraper/sweep.py`): if >10% of surname fetches error, or the roster collapses
  to <50% of last cycle, it keeps the last-good `data/current.json` and exits 0.
  That's why the public count is stable even when HCSO rate-limits a sweep.
- `_compact_anon_entries` in `scraper/store.py` bounds `data/anon_changelog.json`.
  Rows older than `ANON_COMPACTION_MAX_DAYS` (365) collapse into monthly summaries.
  Each summary carries a `count`. Compaction runs at write time. It is not a
  migration. It is idempotent. Each summary groups rows by these fields:

  | group key |
  | :-- |
  | month |
  | event |
  | tier |
  | category |

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

### Pages deploy stuck in deployment_queued

The "pages build and deployment" run occasionally sits in
`deployment_queued` for many minutes while githubstatus.com says Pages is
operational. This is GitHub-side queueing. Do not chase it: the artifact
is already built, the site keeps serving the previous deploy, and the next
sweep triggers a fresh deploy that supersedes the stuck one.
Only investigate if the live `Generated` timestamp lags main by more than
two sweep cycles.

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

**Do not `git push -f`.** Force-pushing `main` rewrites published history, it
does not make a Pages webhook fire, and the owner has blocked force-pushes on
`main` in branch protection. It is never the remedy for a deploy lag. Same rule
in `runbooks/live-parity-failure.md` §4.3: do not hand-edit `docs/` or
force-push generated output.

First establish *which* kind of lag this is, because they have different fixes:

- **Roster age** - `data/current.json:generated_utc` itself is old. No sweep has
  run. The deploy is fine; there is simply nothing newer to publish. Dispatch
  `sweep.yml` (see "Force a sweep now" above).
- **Stale published artifacts** - the deploy succeeded but shipped an old
  `docs/`. Compare `docs/data/transparency_metrics.json:computed_utc` against
  `data/current.json:generated_utc`; a mismatch means `docs/` was built by older
  code. Regenerate and commit `docs/` (see "Deterministic Build Contract").
- **Genuinely stuck deploy** - rare. Handle below.

A green `pages-build-deployment` is *not* proof the live site advanced: those
jobs reported success for weeks while republishing a frozen `docs/` skeleton
(issues #483, #487, #496).

1. Check https://github.com/AICincy/HCJC/actions
2. Look for `pages-build-deployment` workflow
3. If missing: trigger a sweep rather than assuming a webhook fault:
   - dispatch `sweep.yml` via the **UI** (owner; always available), or
   - `gh workflow run sweep.yml -r main` if the token has `actions:write`, or
   - wait for the cron - but it drifts 3.5-5.5h in practice, so do not plan
     around an hour boundary.
4. If queued: leave it alone. GitHub's Pages queues self-heal and the site keeps
   serving the previous deploy; the next sweep supersedes it. Do **not** cancel
   and force-push.
5. If the run itself failed with `Deployment failed, try again later`: re-run the
   failed job (`gh run rerun <id> --failed`). Transient GitHub-side rejections
   clear on the next successful sweep push that includes a fresh `docs/`.
6. If the build failed: read the logs, fix the source or data, go through a
   normal PR, then let the sweep republish. Never commit a hand-edited `docs/`.
7. Full runbook: `runbooks/live-parity-failure.md`
8. Verify live (from a network that can reach the domain; sandbox egress to
   `www.aretheyinjail.com` fails at TLS and proves nothing either way):
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
  `computed_utc` / `generated_utc` equality against the *committed* `docs/` and
  that `web/build.py` anchors the clock before `_render_build(...)` and clears it
  after. Added because PR #503 merged the fix while the committed `docs/` had
  been generated by pre-fix code, so branch-serve published unanchored artifacts
  with every gate green (`audit/25_pages_stale_artifact_misdiagnosis.md`).

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

- `waf_block_log.json` is an ORC 149.43 evidence
  artifacts. The test suite must never write to them. Verified clean
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
