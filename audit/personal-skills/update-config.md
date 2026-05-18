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
