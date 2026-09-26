# HCJC agentic audit and remediation contract

Do not add a persona preamble. Do not load dated `audit-output/` packets as current truth.

## Outcome

Raise the next agent's productivity. A fix counts only if it (a) makes live public truth correct, (b) removes a false constraint the next agent would reload, or (c) makes the sweep → docs → Pages path actually ship. A green annotation with no change to those three is not a result.

## Task boundary

Repo: `AICincy/HCJC`. Live site: `https://www.aretheyinjail.com`.

In scope:

- `.github/workflows/*` that still exist on `main`
- source that builds or publishes (`scraper/`, `web/`, `scripts/`, `tests/`)
- user-facing copy that states cadence, URLs, case-number rules, send/no-send
- `audit-output/` and other memos that agents treat as current
- comments and tests that freeze a superseded contract
- optional CI warnings that still name a Node 20 / unpinned / missing-config action

Out of scope unless a finding proves they block publish or mis-instruct an agent:

- visual redesign
- new product features
- scraping `courtclerk.org` (`robots.txt` disallows `/data/`)
- SMTP, Resend, or any send path

## Authority and live ground truth

Current truth is only:

1. `main` at the tip SHA you fetch this run
2. the live site and `https://www.aretheyinjail.com/data/current.json`
3. official clerk case-number help: `https://www.courtclerk.org/data/case_key.html`
4. live workflow files and the latest Actions run for each workflow name that still exists
5. this contract

Not truth:

- any file under `audit-output/` whose date is older than the tip, unless you first re-verify every claim against (1)–(4)
- comments that say "15-minute", "pylint.yml", "deno.yml", "strip the leading slash", "JCStream sends"
- a test that encodes a retired contract
- a prior chat summary

If a memo and `main` disagree, `main` plus live evidence win. Then delete or rewrite the memo so the disagreement cannot recur.

## Hard constraints

- Do not invent tools. Use only the tools this host actually exposes.
- Do not scrape `courtclerk.org/data/`.
- PRA letters are drafts for a human. JCStream never sends.
- Do not treat Actions annotations as P0 when the named action is already on a Node 24 SHA. Verify the pin before editing.
- Do not add another dated audit novel. If you write a report, it is a ledger of claims you killed and files you changed, then you change those files.
- Optional does not mean skip. Optional means last, and still closed in the same run if the edit is local.

## Productivity ranking

Work in this order. Do not start rank 3 while rank 1 still poisons the tree.

1. False ground truth. Dated audits, comments, README lines, and tests that contradict tip `main` or the live site.
2. Live public truth and the publish loop. Case links, footer vintage, `docs/` actually committed, Pages actually serving the new tree, sweep/rebuild/pages wiring.
3. Optional hygiene. Node runtime annotations, pin-label mismatches, unused workflow files, warning-level feed misses.

A rank-3 fix that does not also remove a stale sentence about the old pin is incomplete.

## Required method

1. Inventory live workflows from the tip tree, not from a memo. Names that are not on disk are dead. Do not "fix" them.
2. For every claim you are about to act on, write one line: claim, file:line or URL, status `verified` | `contradicted` | `not-found`. Contradicted claims must be edited or deleted in this run.
3. Confirm live site behavior with a fetch, not with generated HTML in an old `docs/` snapshot, when the finding is user-visible.
4. Patch the source of the false claim and every reader of it (test, template, comment, audit packet) in the same PR.
5. For `audit-output/` packets that are wrong: delete them, or replace the file with a four-line stub that names the date, says `ARCHIVED — not current`, and points at `AUDIT-CONTRACT.md` plus tip `main`. Do not leave a long narrative that still reads as current.
6. Open one PR per cluster. Wait for lint. Merge only if authorized as "PR then merge after lint green." Trigger `rebuild.yml` only when public HTML or data URLs change.
7. Re-fetch the live page or the workflow file after merge before calling the item done.

## Stop conditions

Stop when:

- every contradicted claim you opened has a file change or an archived stub
- live checks for the user-visible items pass
- optional CI items in the opened cluster are fixed or recorded as upstream-only (name the upstream action SHA and `runs.using`)
- or one human gate remains (send a letter, rotate a secret, enable a GitHub environment)

Do not stop at a plan. Do not stop at "optional, ignore."

## Output contract

Return only:

1. Tip SHA and the live `generated_utc` you actually fetched
2. Claim ledger: claim / source / status / file changed
3. PR URL and merge SHA if merged
4. What the next agent must not reload (paths now archived or deleted)
5. One remaining gate or `none`

No executive verdict. No second audit memoir.
