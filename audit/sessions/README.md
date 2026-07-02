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

| Session ID | Transcript file | Date range | Exported on |
| :-- | :-- | :-- | :-- |
| session_01Hbc6p9EspF6RH9ajNNb8tB | not yet filed | [VERIFY] | [VERIFY] |
| session_01MNnYgZMY5uFz9cHie3w6TY | not yet filed | [VERIFY] | [VERIFY] |
| session_019fDevbfpgmnjJP7A343T95 | not yet filed | [VERIFY] | [VERIFY] |
| session_01NGMSLESEepbgV8aSn4reVG | not yet filed | [VERIFY] | [VERIFY] |

Note: none of these four session IDs appears in any commit trailer in this
repository (checked 2026-07-02 with `git log --all --grep`), so date ranges
cannot be reconstructed from git history and must come from the claude.ai
export.
