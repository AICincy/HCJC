# Chain of custody: Claude Code session transcripts

This directory is the designated authoritative storage location for the
exported transcripts of the court-evidence Claude Code sessions listed in
CLAUDE.md ("Chain of Custody: Session IDs"). The 2026-06-16 code review
flagged the absence of a documented storage location as a Critical finding
(`audit/code-review-2026-06-16/00-summary.md`).

Status: **designated, not yet populated.** No transcript has been filed.
Until every transcript below is filed, court submissions citing these
session IDs must state that the transcripts are held in the owner's
claude.ai session history pending export.

## Filing procedure (owner account required)

1. Sign in to the claude.ai account that owns the session.
2. Open `https://claude.ai/code/<session_id>`.
3. Export the transcript.
4. Save it here as `<session_id>.md` (or `.json` if the export is JSON),
   unmodified.
5. Record the export date and the session's date range in the table below
   and in the CLAUDE.md table.
6. Commit with message `evidence: file transcript <session_id>`.

## Ledger

| Session ID | Transcript file | Original export filename | Date range | Exported on |
| :-- | :-- | :-- | :-- | :-- |
| session_01Hbc6p9EspF6RH9ajNNb8tB | not yet filed | not yet filed | [VERIFY] | [VERIFY] |
| session_01MNnYgZMY5uFz9cHie3w6TY | not yet filed | not yet filed | [VERIFY] | [VERIFY] |
| session_019fDevbfpgmnjJP7A343T95 | not yet filed | not yet filed | [VERIFY] | [VERIFY] |
| session_01NGMSLESEepbgV8aSn4reVG | not yet filed | not yet filed | [VERIFY] | [VERIFY] |
| session_019qfYLXARs48orCHaQdM8cA | not yet filed | not yet filed | 2026-07-02 [VERIFY] | [VERIFY] |
| session_01DCTmLdgUma5GYA1JBrywGp | not yet filed | not yet filed | 2026-07-03 [VERIFY] | [VERIFY] |
| db5bf8bb-9850-49f0-8f3d-1c6abfa5a05e | not yet filed | not yet filed | 2026-07-05 [VERIFY] | [VERIFY] |

Note: the four original session IDs do not appear in any commit trailer in
this repository (checked 2026-07-02 with `git log --all --grep`), so their
date ranges cannot be reconstructed from git history and must come from the
claude.ai export. `session_019qfYLXARs48orCHaQdM8cA` and
`session_01DCTmLdgUma5GYA1JBrywGp` do appear in commit trailers (dated
2026-07-02 through 2026-07-04); their transcripts still require export to
confirm the full range.

`db5bf8bb-9850-49f0-8f3d-1c6abfa5a05e` is a local Claude Code desktop
session (UUID format, not a claude.ai `session_` ID). Its transcript lives
in the owner's local Claude Code session storage
(`~/.claude/projects/C--Users-jared-Documents-GitHub-HCJC/`), not on
claude.ai; the filing step is a local export, not a web export. Work
product: PRs #387-#391 (coverage audit + cleanup, wiki sync, stray-static-
docs removal, CLAUDE.md corrections, manual-sweep runbook), 2026-07-05.

## Git corroboration (measured 2026-07-08)

Committer-date span of commits carrying each session ID in a trailer
(`git log --all --grep=<id>`). This is a lower bound on when the session's
work landed, not the authoritative session date range, which still comes from
the export. Four sessions left no trailer, so git offers no corroboration for
them; their date ranges depend entirely on the claude.ai export.

| Session ID | Commits in git | Commit span |
| :-- | :-- | :-- |
| session_01Hbc6p9EspF6RH9ajNNb8tB | 0 | none in git |
| session_01MNnYgZMY5uFz9cHie3w6TY | 0 | none in git |
| session_019fDevbfpgmnjJP7A343T95 | 0 | none in git |
| session_01NGMSLESEepbgV8aSn4reVG | 0 | none in git |
| session_019qfYLXARs48orCHaQdM8cA | 23 | 2026-07-02 to 2026-07-04 |
| session_01DCTmLdgUma5GYA1JBrywGp | 13 | 2026-07-04 |
| db5bf8bb-9850-49f0-8f3d-1c6abfa5a05e | 1 | 2026-07-05 |

Two date-tag discrepancies to resolve on export:

- `session_019qfYLXARs48orCHaQdM8cA` is tagged `2026-07-02` in the ledger and
  CLAUDE.md, but its commits span through 2026-07-04. The session likely ran
  longer than one day.
- `session_01DCTmLdgUma5GYA1JBrywGp` is tagged `2026-07-03`, but its commits
  landed 2026-07-04. Confirm the session date from the export.
