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
