# JCStream: working notes for Claude

JCStream is a static public-records mirror of the Hamilton County, Ohio Justice
Center inmate roster. A Python script (`web/build.py`) regenerates `docs/` from
`data/current.json` on a GitHub Actions cron that fires every 15 minutes with a
20-minute skip-gate (`.github/workflows/sweep.yml` cron `*/15 * * * *`; the
sweep no-ops if `current.json` is less than 20 minutes old). Effective cadence
is roughly 20-45 minutes; during incidents the next-run can slip past the hour.
The sweep also runs the HCSO scraper
(`scraper/`) and pulls four Cincinnati Open Data feeds.
Live at https://www.aretheyinjail.com (GitHub Pages, custom domain; build uses
`JCSTREAM_SITE_BASE_URL=""` + a `CNAME` file written from `JCSTREAM_CNAME`).

## Project specialists

`.claude/skills/` and `.claude/agents/` ship ten paired specialists for the
recurring domains in this repo: templates, CSS, build helpers, ORC data,
scraping, tests, design ports, legal copy, accessibility, and sweep
debugging. They auto-discover in any Claude Code session; ask for one by
name (e.g. "have the jcstream-template-author …") or by describing the
task ("update the FCRA disclaimer" routes to `legal-copy-author`). See
`.claude/skills/README.md` for the index and the handoff topology.

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

- Push target / dev branch: the per-task branch assigned by the agent harness
  (e.g. `claude/<slug>-<id>`). Push there only; I cannot push to `main`, that's
  on the owner.
- `data/surnames.txt` is A-Z single letters on purpose (HCSO's last-name search is a
  substring match, so 26 letters cover the whole roster with dedup). Don't revert.
- Build locally: `JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build`
- Tests: `python -m pytest -q` (must stay green; ≥193 tests as of this writing, suite grows).
- The stylesheet is cache-busted by content hash (`css_version` in build.py); don't
  key it off the data timestamp again.
- The sweep refuses to write a degraded roster (`_sweep_looks_healthy` in
  `scraper/sweep.py`): if >10% of surname fetches error, or the roster collapses
  to <50% of last cycle, it keeps the last-good `data/current.json` and exits 0.
  That's why the public count is stable even when HCSO rate-limits a sweep.

### Runbook: roster frozen / "no new inmates" (HCSO WAF block)

Signature: `data/current.json` (and `data/changelog.json`) stop changing while
the sweep keeps committing the open-data feeds + `docs/` every cycle. Both
freeze at the same `generated_utc`. The degraded-roster guard is firing every
run and keeping last-good data. This is the guard working, not a bug.

1. Confirm: `git log -15 --format="%cI %s" origin/main -- data/current.json` —
   if `current.json` hasn't changed in hours but `sweep` commits keep landing,
   it's frozen.
2. Diagnose from the Actions sweep log (grep, in order):
   - `ROSTER FROZEN` — the freeze alarm (`roster_stale_hours` >=
     `ROSTER_STALE_ALARM_HOURS`, 6h); also emitted as a `::error::` annotation
     by the "Roster freeze alarm" step in `sweep.yml`.
   - `list sweep looks degraded (prev=… seen=… N/M surname fetches failed)` —
     the guard fire. `N/M > 2/26` ⇒ WAF raising on fetches; `seen < 50% of prev`
     ⇒ WAF serving empty-but-parseable pages.
   - `WAF-block-shaped response for id=…` / `429 …` ⇒ WAF active.
3. Cause is almost always HCSO's WAF blocking the GitHub Actions egress IP.
   Code can't fix that. Options: wait for the block to rotate (cloud WAFs
   commonly 24-72h); run from a different egress (self-hosted runner / proxy);
   or contact HCSO for allowlisting.
4. NEVER lower `SWEEP_MAX_FAILED_FRACTION` (0.10) or `SWEEP_MIN_ROSTER_FRACTION`
   (0.5) to force the sweep through — that publishes a partial roster as if
   complete, which is worse than stale data. Tuning `crawl_delay` / `concurrency`
   in `client.py` only helps if errors are borderline (≈3/26), not a hard block.

### Optional features (owner-side setup, not something I can do from here)

- **Giscus comments** on inmate pages (`web/templates/inmate.html` renders the
  policy block always, and the Giscus widget when `giscus.repo_id` is set):
  1. Repo → Settings → General → Features → enable **Discussions**.
  2. Create a Discussions **category** to hold the threads (e.g. "Announcements"
     or a new "Records" one). Note its name.
  3. Install the **Giscus GitHub App** (<https://github.com/apps/giscus>) and
     grant it access to `AICincy/JCStream`.
  4. Go to <https://giscus.app>, enter `AICincy/JCStream`, pick the category;
     it prints `data-repo-id` and `data-category-id`.
  5. Repo → Settings → Secrets and variables → Actions → **Variables**: add
     `JCSTREAM_GISCUS_REPO_ID`, `JCSTREAM_GISCUS_CATEGORY_ID` (and optionally
     `JCSTREAM_GISCUS_REPO`, `JCSTREAM_GISCUS_CATEGORY` to override the defaults).
  6. Next sweep rebuilds with the widget live. To turn it off, clear the vars.

- **PRA email loop**: capias / mugshot-fallback public-records requests
  (`scraper/pra.py`, `scraper/pra_capias.py`, `.github/workflows/pra_daily.yml`):
  it dry-runs (logs only) until SMTP is configured. Repo → Settings → Secrets and
  variables → Actions → **Secrets**: `JCSTREAM_PRA_SMTP_HOST`, `JCSTREAM_PRA_SMTP_PORT`,
  `JCSTREAM_PRA_SMTP_USER`, `JCSTREAM_PRA_SMTP_PASS`, `JCSTREAM_PRA_FROM_EMAIL`
  (and optionally per-loop recipient overrides `JCSTREAM_PRA_TO_PHOTOS_EMAIL`
  for `scraper/pra.py` and `JCSTREAM_PRA_TO_CAPIAS_EMAIL` for `scraper/pra_capias.py`;
  both default to `HCAdmin@hamilton-co.org`).
  With `JCSTREAM_PRA_SMTP_HOST` + `JCSTREAM_PRA_FROM_EMAIL` present it sends for real.

