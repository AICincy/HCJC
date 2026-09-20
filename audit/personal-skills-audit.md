# JCStream personal/harness skills audit

**Run date**: 2026-05-14
**Verdict matrix**:

| # | Skill | Applicability | Recommendation |
|---|---|---|---|
| 1 | `init` | None | Keep but rarely use |
| 2 | `review` | Low | Keep but rarely use |
| 3 | `security-review` | Medium | Keep enabled |
| 4 | `simplify` | Low | Keep but rarely use |
| 5 | `update-config` | Low | Keep enabled |
| 6 | `keybindings-help` | None | N/A (keep enabled at user level; irrelevant to this project) |
| 7 | `fewer-permission-prompts` | High | Keep enabled |
| 8 | `loop` | Medium | Keep enabled |
| 9 | `session-start-hook` | High | Keep enabled |
| 10 | `claude-api` | None | Keep enabled (harmless; will not auto-fire) |

Per-skill reports under `audits/personal-skills/`.

================================================================================
## Subagent 1/10 — audit of `init`
**Source report**: `audits/personal-skills/init.md`
================================================================================

# Audit — `init` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: None
- **Recommendation**: Keep but rarely use

## What it does
Initializes a new CLAUDE.md file with codebase documentation.

## Fit for JCStream
JCStream already has a mature, hand-tuned CLAUDE.md (73 lines) that documents the
project's purpose, the 30-min sweep cron, the ten paired specialists in
`.claude/skills/`, the owner's working preferences (AskUserQuestion menu rule,
short replies), repo facts (locked dev branch, A–Z surnames, build command, 140
tests, css_version hash, sweep health guard), and owner-side setup for Giscus and
the PRA email loop. There is nothing for `init` to seed — the file is past the
initialization stage and contains tribal knowledge a generic scan cannot recover.

## Realistic triggers in this project
- None from the maintainer. A brand-new contributor could conceivably type
  "/init" or "set up CLAUDE.md", but the owner of this solo repo would not.

## Risk
Medium-to-high if it ever auto-fires: the skill name implies *create*, and a
naive run could overwrite the existing CLAUDE.md with a generic codebase summary,
losing the owner's working preferences and the specialist roster.

## Recommendation rationale
The skill is harmless when dormant and would be useful in a fresh repo, so there
is no need to disable it globally. For JCStream specifically it has no remaining
job — CLAUDE.md is already authored and maintained by hand. If invoked, Claude
should refuse to overwrite and instead diff-propose additions, or route the
request to ordinary `Edit` on the existing file. Treat `init` as a one-time
bootstrap skill that has already served its purpose here.

================================================================================
## Subagent 2/10 — audit of `review`
**Source report**: `audits/personal-skills/review.md`
================================================================================

# Audit — `review` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Low
- **Recommendation**: Keep but rarely use

## What it does
Reviews a pull request — a generic single-pass code review on PR diffs.

## Fit for JCStream
PR review does happen here: commit `7580af8dd` reads "site: address PR review —
move inline styles to CSS, fix sentinel dates, aria-current", and PRs #26, #28,
and #29 were merged recently. But CLAUDE.md and the owner explicitly designate
`/ultrareview` (a multi-agent cloud review) as the preferred path, and the ten
paired `jcstream-*` specialists already cover domain-specific scrutiny
(a11y-auditor, sweep-debugger, legal-copy-author) more sharply than a generic
pass. The repo is also a solo, locked-branch project — PRs are auto-generated
from `claude/*` worktrees, not opened by outside contributors needing a gate.

## Realistic triggers in this project
- "Review this PR" / "review PR #N" — but the owner would route to `/ultrareview`.
- "Look at the diff before I merge" — but specialists are usually a better fit.
- Pre-merge sanity pass when `/ultrareview` is unavailable or overkill — rare.

## Risk
Low — `review` is read-only by design, but invoking it could shadow or
duplicate `/ultrareview`'s output and waste a turn that should have routed to a
domain specialist.

## Recommendation rationale
Keep enabled as a harmless fallback, but prefer `/ultrareview` for full PR
review and the `jcstream-*` specialists for domain checks (templates, CSS,
scraper, ORC, legal copy, a11y). The skill has no unique job in JCStream: the
specialist roster plus the cloud reviewer already cover the review surface, and
the locked-branch solo workflow means most PRs ship without external review at
all. If the owner ever wants a quick generic second look without spinning up
`/ultrareview`, `review` is fine — otherwise skip it.

================================================================================
## Subagent 3/10 — audit of `security-review`
**Source report**: `audits/personal-skills/security-review.md`
================================================================================

# Audit — `security-review` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Medium
- **Recommendation**: Keep enabled

## What it does
Completes a security review of the pending changes on the current branch.

## Fit for JCStream
JCStream's attack surface is narrow but non-trivial. There's no public auth or user input, but the scraper ingests untrusted HTML from HCSO into Jinja (autoescape is on via `select_autoescape(["html","xml"])` in `web/build.py`), parses untrusted image bytes via Pillow (`scraper/photos.py`), sends outbound SMTP with env-driven addressing (`scraper/pra.py`, `pra_base.py`), and runs in GitHub Actions with `contents: write` plus PRA SMTP secrets. A targeted security pass on diffs touching these areas would find real issues; a pass on template/CSS-only diffs would be noise.

## Realistic triggers in this project
- New scraper field rendered into a template (verify autoescape is not bypassed with `|safe`/`Markup`)
- Changes to `scraper/photos.py` or any path passing bytes to `PIL.Image.open` (decompression-bomb / malformed-image handling)
- Edits to `scraper/pra*.py` or `pra_base.send_smtp` (header injection, recipient-from-env, TLS posture, secret logging)
- Changes to `.github/workflows/sweep.yml` or `pra_daily.yml` (permissions scope, secret echoing, third-party action pinning)
- New outbound HTTP target in `scraper/client.py` or open-data feeds (SSRF surface, URL construction)
- Anything writing to `docs/` from external input (path traversal)

## Risk
Read-only review skill; no risk to invoke.

## Recommendation rationale
The scraper-to-static-site pipeline still has the classic untrusted-input concerns — HTML into templates, image bytes into Pillow, env-driven SMTP, and Actions secrets — so `security-review` is genuinely useful when diffs touch `scraper/`, `web/build.py`, or `.github/workflows/`. It's overkill for template/CSS/copy edits; the owner should invoke it selectively on the triggers above rather than every change.

================================================================================
## Subagent 4/10 — audit of `simplify`
**Source report**: `audits/personal-skills/simplify.md`
================================================================================

# Audit — `simplify` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Low
- **Recommendation**: Keep but rarely use

## What it does
Reviews recently-changed code for reuse, quality, and efficiency, then applies fixes for the issues it finds.

## Fit for JCStream
JCStream's hot files are densely commented with intent: `web/build.py` explains why CSS is hashed by content (not data timestamp), why both CFS feeds are merged and deduped, and why `base_url` and `site_url` are distinct; `scraper/sweep.py` annotates the 22-minute wall-clock cap, the bootstrap-vs-corrupt distinction, and the `roster_ok` flag's role in suppressing synthetic "released" events. The code is small (~3k LOC), hand-tuned, and the owner's CLAUDE.md explicitly warns against re-litigating settled decisions — so most "simplifications" a generic skill would propose are already considered and rejected.

## Realistic triggers in this project
- "clean this up" / "tidy this function" — rare; owner usually asks for specific edits.
- "is this code OK?" — possible on a fresh helper just added to `web/build.py`.
- "review my last commit" — overlaps with the built-in `/review` skill, which is the better route.
- "any dead code here?" — plausible after a feature removal.

## Risk
High churn risk: it could collapse the deliberate dedup loop in `build.py`, inline the `_sweep_looks_healthy` back-compat alias, or strip "redundant" comments that are actually load-bearing operational notes.

## Recommendation rationale
Keep enabled because it's a personal/harness skill and disabling isn't really on the table — but it's a poor fit for this repo. The codebase rewards reading comments, not refactoring; the project-specific specialists (`jcstream-build-helper-author`, `jcstream-scraper-author`) already cover quality concerns with domain context `simplify` lacks. Reach for `/review` instead when the owner asks for a code check.

================================================================================
## Subagent 5/10 — audit of `update-config`
**Source report**: `audits/personal-skills/update-config.md`
================================================================================

# Audit — `update-config` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Low
- **Recommendation**: Keep enabled

## What it does
Edits `.claude/settings.json` / `settings.local.json` to manage harness permissions, env vars, and lifecycle hooks (SessionStart, Stop, PreToolUse, etc.) on the user's request.

## Fit for JCStream
JCStream has **no** `.claude/settings.json` or `.claude/settings.local.json` — `find` against the repo returns zero matches. `.claude/` contains only `skills/` and `agents/` (the ten paired specialists noted in CLAUDE.md). There are no custom permissions, no env vars, and no hooks to maintain today, so the skill has nothing live to operate on.

## Realistic triggers in this project
- "Allow `pytest` / `python -m web.build` without prompting" (auto-allowlist common dev commands)
- "Set up a SessionStart hook so tests/lint are runnable in web sessions" (overlaps `session-start-hook`, which is the better first stop)
- "When sweep.yml changes, remind me to run the tests" (Stop / PostToolUse hook)
- "Set `JCSTREAM_SITE_BASE_URL=''` as a session env var for local builds"
- "Move my Bash permissions to user-level so they apply across repos"
- The companion `fewer-permission-prompts` skill scans transcripts and writes an allowlist — that flow lands in `update-config` territory.

## Risk
None — read-then-write on a single settings file, only when the owner explicitly asks; no destructive defaults.

## Recommendation rationale
Even though JCStream ships no settings.json today, this is a perfectly generic harness skill — the moment the owner wants a Stop hook, a pytest allowlist, or wants to act on `fewer-permission-prompts` output, this is the right tool. It has zero cost when idle (description-gated, no auto-runs) and the trigger phrases are specific enough that it won't misfire on JCStream's domain prompts. Keep it enabled.

================================================================================
## Subagent 6/10 — audit of `keybindings-help`
**Source report**: `audits/personal-skills/keybindings-help.md`
================================================================================

# Audit — `keybindings-help` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: None
- **Recommendation**: N/A (keep enabled at user level; irrelevant to this project)

## What it does
Customizes Claude Code keyboard shortcuts by editing the user-level config at `~/.claude/keybindings.json`.

## Fit for JCStream
This is a per-user harness preference, not a project concern. JCStream ships no keybinding config, has no terminal UI of its own, and nothing in the repo (templates, scraper, build pipeline, GitHub Actions) interacts with Claude Code shortcuts. The skill's target file lives outside the repo entirely.

## Realistic triggers in this project
- None. No JCStream-shaped prompt ("update inmate page", "fix sweep guard", "tune ORC tier", "rephrase FCRA disclaimer", etc.) would route here.
- The only way this fires in a JCStream session is if the owner asks an off-topic harness question like "rebind ctrl+s" while this repo happens to be cwd.

## Risk
None — the skill only touches `~/.claude/keybindings.json`, which is outside the repo, so it cannot corrupt project files, tests, or the live site.

## Recommendation rationale
Leave it enabled at the user level since it's harmless and occasionally useful for the owner's overall Claude Code workflow, but treat it as out-of-scope for JCStream audits and project skill curation. No project-level action needed; do not add it to any JCStream-specific allowlist, hook, or skill index.

================================================================================
## Subagent 7/10 — audit of `fewer-permission-prompts`
**Source report**: `audits/personal-skills/fewer-permission-prompts.md`
================================================================================

# Audit — `fewer-permission-prompts` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: High
- **Recommendation**: Keep enabled

## What it does
Scans recent transcripts for repeated read-only Bash/MCP calls and writes a prioritized allowlist to project `.claude/settings.json` to suppress redundant permission prompts.

## Fit for JCStream
Neither `.claude/settings.json` nor `.claude/settings.local.json` exists in this repo — only `.claude/skills/` and `.claude/agents/`. Sessions here repeatedly read `data/current.json`, `data/changelog.json`, `web/templates/*.html`, and `scraper/*.py` (sweep debugging, template edits, ORC curation all touch the same files), plus standard `git status`/`ls`/`pytest -q` Bash calls. A transcript-derived allowlist would meaningfully cut prompt friction for those well-trodden paths.

## Realistic triggers in this project
- "reduce my permission prompts"
- "stop asking me to approve `ls`/`git status`"
- "auto-allow the read commands I keep approving"
- "set up an allowlist for this repo"

## Risk
Low — the skill writes only what transcripts show the user already approving, scoped to the project's `.claude/settings.json`, so it can't grant broader access than the user has historically granted.

## Recommendation rationale
JCStream is a perfect candidate: stable file layout, predictable read patterns (data/, web/templates/, scraper/), repeated test/build commands, and no existing settings file to merge against. Keep the skill enabled; the owner can invoke it once a workflow rhythm has been established (e.g. after a few sweep-debug or template-edit sessions) to harvest the common read-only calls into a project allowlist. No conflict with project-level specialists.

================================================================================
## Subagent 8/10 — audit of `loop`
**Source report**: `audits/personal-skills/loop.md`
================================================================================

# Audit — `loop` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Medium
- **Recommendation**: Keep enabled

## What it does
Runs a prompt or slash command on a recurring interval (default 10m) until the user stops it, for in-session polling/babysitting tasks.

## Fit for JCStream
JCStream's sweep is a GitHub Actions cron at `*/30 * * * *` (best-effort 30–45 min cadence per the workflow comment), and PR CI / Pages deploys can take several minutes. In-session polling is a natural fit for "watch the next sweep land" or "tail the deploy until it goes green" — neither has a built-in blocking wait. It's not load-bearing day-to-day (most work is one-shot edits + tests), but it's the right tool when the owner explicitly wants to babysit a long-running thing.

## Realistic triggers in this project
- "watch the next sweep run and tell me when `data/current.json` changes"
- "poll the Pages deploy every 5 min until it's live"
- "loop until the latest sweep workflow finishes, then summarize"
- "keep checking the PR's CI every 10 min"
- "watch www.aretheyinjail.com until the new build shows up"

## Risk
None — user-initiated, interruptible, read-only by default (it just re-issues a prompt).

## Recommendation rationale
The 30-min sweep cadence plus occasional CI/Pages waits make `loop` a genuinely useful escape hatch a few times a month. It doesn't conflict with any JCStream specialist, has zero cost when unused, and the description's anti-pattern guard ("Do NOT invoke for one-off tasks") keeps it from misfiring. Keep enabled.

================================================================================
## Subagent 9/10 — audit of `session-start-hook`
**Source report**: `audits/personal-skills/session-start-hook.md`
================================================================================

# Audit — `session-start-hook` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: High
- **Recommendation**: Keep enabled

## What it does
Authors a `.claude/hooks/session-start.sh` + `.claude/settings.json` SessionStart entry that installs project dependencies so tests and linters work in Claude Code on the web sessions.

## Fit for JCStream
JCStream is a from-scratch solo repo that the owner runs primarily via Claude Code on the web, and `CLAUDE.md` explicitly requires `python -m pytest -q` to stay green (currently 34 tests). There is currently no `.claude/settings.json` and no `.claude/hooks/` directory in the repo, so a fresh web container has none of the runtime deps (`httpx`, `selectolax`, `pydantic`, `jinja2`, `Pillow`, `pytest`) — every session would need a manual `pip install -e .[dev]` (or `pip install -r requirements.txt`) before tests or `python -m web.build` will run. This is exactly the gap the skill closes.

## Realistic triggers in this project
- "set up a session-start hook so pytest works on the web"
- "make `python -m pytest -q` work without me installing things first each session"
- "install deps automatically when a web session starts"
- "add a `.claude/hooks/session-start.sh` for this repo"

## Risk
None — read/write is confined to `.claude/`, the script is idempotent, and the skill's own workflow validates the hook, linter, and a test before finishing.

## Recommendation rationale
The skill maps 1:1 onto a real, recurring pain point for this project: every web session currently starts cold and must `pip install` before the suite or the builder run. A SessionStart hook that runs `pip install -e .[dev]` (or against `requirements.txt`) is the exact intervention the skill is designed to produce, and nothing comparable exists in the repo today. Keep it enabled; it is a one-shot setup the owner is likely to invoke once and then forget.

================================================================================
## Subagent 10/10 — audit of `claude-api`
**Source report**: `audits/personal-skills/claude-api.md`
================================================================================

# Audit — `claude-api` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: None
- **Recommendation**: Keep enabled (harmless; will not auto-fire)

## What it does
Builds, debugs, optimizes, and version-migrates apps that call the Claude API via the Anthropic SDK, with prompt caching as a default.

## Fit for JCStream
`grep -rn "anthropic\|Anthropic" --include="*.py"` and the same for `openai` return zero hits. `requirements.txt` pins only `httpx`, `selectolax`, `pydantic`, `jinja2`, `Pillow`, `pytest` — a static-site/scraping stack with no LLM runtime. JCStream uses Claude Code as a development tool, not as a runtime dependency; the skill's trigger conditions therefore never match this codebase.

## Realistic triggers in this project
- None under the current architecture.
- Hypothetical only: if someone adds an LLM-backed feature (e.g. auto-generated ORC explainers, charge summarization, photo-captioning) it would then apply — but that would be a deliberate new direction, not in scope today. The existing `jcstream-orc-curator` skill maintains explainers by hand.

## Risk
None — the skill's trigger conditions (anthropic imports, Claude API questions, model-feature edits) cannot match anything currently in this repo, so it stays dormant.

## Recommendation rationale
Leave enabled. It is gated on imports and explicit Claude API/SDK language, neither of which exist in JCStream, so it imposes no cost on day-to-day work. Disabling it would only matter if it were misfiring, and there is nothing here for it to misfire on. If an LLM feature is ever added, the skill becomes immediately useful with no reconfiguration; until then it is inert.

