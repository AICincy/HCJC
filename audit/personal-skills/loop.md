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
