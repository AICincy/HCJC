# JCStream — working notes for Claude

JCStream is a static public-records mirror of the Hamilton County, Ohio Justice
Center inmate roster. A Python script (`web/build.py`) regenerates `docs/` from
`data/current.json` on a nominally-30-minute GitHub Actions cron
(`.github/workflows/sweep.yml`). In practice the cron drifts — observed
intervals on a normal day run 30-60 minutes (GitHub Actions schedules `cron:`
jobs on best-effort; high-load periods stretch the gap), and during incidents
the next-run can slip past the hour. The sweep also runs the HCSO scraper
(`scraper/`) and pulls four Cincinnati Open Data feeds.
Live at https://www.aretheyinjail.com (GitHub Pages, custom domain — build uses
`JCSTREAM_SITE_BASE_URL=""` + a `CNAME` file written from `JCSTREAM_CNAME`).

## Project specialists

`.claude/skills/` and `.claude/agents/` ship ten paired specialists for the
recurring domains in this repo — templates, CSS, build helpers, ORC data,
scraping, tests, design ports, legal copy, accessibility, and sweep
debugging. They auto-discover in any Claude Code session; ask for one by
name (e.g. "have the jcstream-template-author …") or by describing the
task ("update the FCRA disclaimer" routes to `legal-copy-author`). See
`.claude/skills/README.md` for the index and the handoff topology.

## Hard constraints (violations are accessibility failures, not style issues)

The owner has AuDHD. These rules are medical accessibility accommodations.
Violating them imposes cognitive cost the owner cannot afford. Read the memory
system (`memory/` directory) for full context including the May 2026 post-mortem.

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
  with *truthful* recommendations — say which I'd actually do and why, and
  which are marginal/skip — so the owner can accept items **individually,
  all, or none**. Don't just summarize and stop; don't keep building past
  the obvious-in-scope work without surfacing the menu first.
  "Implement all suggestions" means: do everything in the last menu I
  offered — so there must always be one.

### General
- Keep replies short. Don't re-litigate settled things. Don't nag about
  branches/PRs — this is a from-scratch solo repo; `main`/PR ceremony is moot.

## Repo facts

- Push target / dev branch: `claude/export-skill-agent-zip-gspVE` (my git access is
  locked to this branch — I cannot push to `main` or create branches; that's on the owner).
- `data/surnames.txt` is A–Z single letters on purpose (HCSO's last-name search is a
  substring match, so 26 letters cover the whole roster with dedup). Don't revert.
- Build locally: `JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build`
- Tests: `python -m pytest -q` (must stay green; ≥173 tests as of this writing, suite grows).
- The stylesheet is cache-busted by content hash (`css_version` in build.py) — don't
  key it off the data timestamp again.
- The sweep refuses to write a degraded roster (`_sweep_looks_healthy` in
  `scraper/sweep.py`): if >10% of surname fetches error, or the roster collapses
  to <50% of last cycle, it keeps the last-good `data/current.json` and exits 0.
  That's why the public count is stable even when HCSO rate-limits a sweep.

### Optional features — owner-side setup, not something I can do from here

- **Giscus comments** on inmate pages (`web/templates/inmate.html` renders the
  policy block always, and the Giscus widget when `giscus.repo_id` is set):
  1. Repo → Settings → General → Features → enable **Discussions**.
  2. Create a Discussions **category** to hold the threads (e.g. "Announcements"
     or a new "Records" one) — note its name.
  3. Install the **Giscus GitHub App** (<https://github.com/apps/giscus>) and
     grant it access to `AICincy/JCStream`.
  4. Go to <https://giscus.app>, enter `AICincy/JCStream`, pick the category —
     it prints `data-repo-id` and `data-category-id`.
  5. Repo → Settings → Secrets and variables → Actions → **Variables**: add
     `JCSTREAM_GISCUS_REPO_ID`, `JCSTREAM_GISCUS_CATEGORY_ID` (and optionally
     `JCSTREAM_GISCUS_REPO`, `JCSTREAM_GISCUS_CATEGORY` to override the defaults).
  6. Next sweep rebuilds with the widget live. To turn it off, clear the vars.

- **PRA email loop** — capias / mugshot-fallback public-records requests
  (`scraper/pra.py`, `scraper/pra_capias.py`, `.github/workflows/pra_daily.yml`):
  it dry-runs (logs only) until SMTP is configured. Repo → Settings → Secrets and
  variables → Actions → **Secrets**: `JCSTREAM_PRA_SMTP_HOST`, `JCSTREAM_PRA_SMTP_PORT`,
  `JCSTREAM_PRA_SMTP_USER`, `JCSTREAM_PRA_SMTP_PASS`, `JCSTREAM_PRA_FROM_EMAIL`
  (and optionally per-loop recipient overrides `JCSTREAM_PRA_TO_PHOTOS_EMAIL`
  for `scraper/pra.py` and `JCSTREAM_PRA_TO_CAPIAS_EMAIL` for `scraper/pra_capias.py`;
  both default to `HCAdmin@hamilton-co.org`).
  With `JCSTREAM_PRA_SMTP_HOST` + `JCSTREAM_PRA_FROM_EMAIL` present it sends for real.

- **Sentry error monitoring** for the sweep (`scraper/sweep.py`,
  `.github/workflows/sweep.yml`): error-only, no tracing, no PII. Surfaces
  the silent-staleness paths from `audit/05_sweep_reliability.md` as alerts
  so the operator hears about a degraded-roster fallback the same minute it
  happens (instead of "the site looks stale and the workflow exited 0").
  1. Create a Sentry project (Python platform) and copy its DSN.
  2. Repo → Settings → Secrets and variables → Actions → **Secrets**: add
     `JCSTREAM_SENTRY_DSN` with the DSN as the value.
  3. The next sweep picks it up. With the secret unset, `_init_sentry()`
     short-circuits to a no-op and the sweep behaves exactly as before.
  - Events emitted (all from `scraper/sweep.py`):
    `sweep.degraded.roster_floor` (roster collapsed below 50% of prior),
    `sweep.degraded.surname_errors` (>10% of letter fetches errored),
    `sweep.detail_watchdog_tripped` (detail-page parse rates degraded —
    `blocked="true"` for the hard floor that keeps the last-good roster,
    `blocked="false"` for the WARN-only soft floors),
    `sweep.photo_prune.skipped` (would-be prune over 50% of photos),
    plus `capture_exception` for any unhandled error in the sweep loop.
    Per-surname workers tag `sweep.surname_letter` so an exception in
    one letter is triage-able.
  - When to expect to hear from it: a single alert in a 30-min window is
    usually HCSO rate-limiting and resolves on the next cycle. Two or three
    cycles in a row of `sweep.degraded.*` means HCSO is actually down or
    has restructured the list page. Any `detail_watchdog_tripped` with
    `blocked="true"` means HCSO redesigned the detail page — check
    `scraper/parsers.py`. See `audit/13_sentry_instrumentation.md` for the
    full catalog and threshold cross-reference.
  - To turn it off: delete the `JCSTREAM_SENTRY_DSN` secret. No code change.
