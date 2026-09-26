# Clerk PRA packet - 2026-09-26

1175 draft public-records request letters, one per inmate on the JCStream
roster snapshot of 2026-09-26 (generated 2026-09-26T19:23:16Z).

## How to use

1. Fill in the `[YOUR ...]` sender block at the top of each letter you send.
2. Verify the subject is still in custody (roster snapshots go stale fast).
3. Mail or hand-deliver to the Clerk of Courts address on the letter.

## Batching guidance

Do **not** send all 1175 letters at once. A mass mailing of this size
would burden the Clerk's office and undermine the request. Suggested
practice:

- Send in small batches (e.g. 5-10 per week).
- Prioritize inmates whose roster charges lack case numbers, or cases you
  are specifically researching.
- Log every response or denial back into `manifest.json` under
  `clerk_response` so the paper trail stays complete.

## What this is

- Each letter is a **draft** under Ohio Revised Code 149.43. JCStream
  generated the text; the human sender is the requester.
- `manifest.json` records the facts of each draft request: who, what case
  numbers were known, when the draft was generated. Treat it as the
  evidence log for this packet.
- Nothing here is legal advice. Charges listed are accusations, not
  convictions.

## Regenerating

Run `python -m scraper.clerk_pra --date YYYY-MM-DD` from the repo root to
build a fresh dated folder from the current `data/current.json`.
