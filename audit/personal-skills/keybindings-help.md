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
