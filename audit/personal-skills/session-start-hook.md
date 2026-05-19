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
