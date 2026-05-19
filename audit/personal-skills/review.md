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
