# Transcript export checklist (10-minute task, owner account required)

Work through top to bottom. Each row takes about two minutes.

## Prerequisites

- Signed in at claude.ai on the account that owns the sessions.
- This repo cloned locally (or use the GitHub web editor for steps 3-4).

## Per-session steps

For each session below:

1. Open the URL.
2. Export the transcript (Share / Export in the session menu). Prefer the
   fullest format offered; Markdown if given a choice.
3. Save the file unmodified into `audit/sessions/` with the exact name shown.
4. Note the first and last message dates from the transcript.

| # | Open this URL | Save as |
| :-- | :-- | :-- |
| 1 | https://claude.ai/code/session_01Hbc6p9EspF6RH9ajNNb8tB | `session_01Hbc6p9EspF6RH9ajNNb8tB.md` |
| 2 | https://claude.ai/code/session_01MNnYgZMY5uFz9cHie3w6TY | `session_01MNnYgZMY5uFz9cHie3w6TY.md` |
| 3 | https://claude.ai/code/session_019fDevbfpgmnjJP7A343T95 | `session_019fDevbfpgmnjJP7A343T95.md` |
| 4 | https://claude.ai/code/session_01NGMSLESEepbgV8aSn4reVG | `session_01NGMSLESEepbgV8aSn4reVG.md` |

## After all four files are saved

5. Update the ledger table in `audit/sessions/README.md`: transcript
   filename, date range (from step 4), export date (today).
6. Update the matching table in `CLAUDE.md` ("Chain of Custody"): replace
   each date-range `[VERIFY]` with the confirmed range.
7. Commit everything in one commit:
   `evidence: file chain-of-custody transcripts (4 sessions)`
8. Push to main (or hand the commit to a Claude session to push and PR).

Done. This closes the 2026-06-16 Critical finding entirely; the repository
becomes the attestable location of record for all four sessions.

If a session URL 404s: the session may belong to a different claude.ai
account or workspace. Check the account switcher before concluding the
transcript is lost, and record the outcome in the README ledger either way.
