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
