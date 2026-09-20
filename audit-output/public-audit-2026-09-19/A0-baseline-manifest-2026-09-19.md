# A0 baseline manifest: public-only HCJC audit

**Audit wave:** Public-only A0 through A4  
**Frozen at:** 2026-09-19 19:28:48Z commit time; local audit setup completed 2026-09-19  
**Remote:** `https://github.com/AICincy/HCJC.git`  
**Frozen commit:** `fbe33ca9af7db6e08ab4a6f16515ece26085b241`  
**Commit subject:** `data+site: sweep 2026-09-19T19:28Z`

## Isolated working trees

| Purpose | Directory | HEAD | Integrity and status check |
|---|---|---|---|
| A0 baseline and source reference | `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-baseline` | `fbe33ca9af7db6e08ab4a6f16515ece26085b241` | `git fsck --no-dangling --no-reflogs` completed without output; status clean. |
| A2 CI reproducibility | `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-a2` | `fbe33ca9af7db6e08ab4a6f16515ece26085b241` | `git fsck --no-dangling --no-reflogs` completed without output; status clean. |
| A4 evidence and resilience checks | `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-a4` | `fbe33ca9af7db6e08ab4a6f16515ece26085b241` | `git fsck --no-dangling --no-reflogs` completed without output; status clean. |

## Baseline-custody note

The first `git clone` helper did not finish cleanly and left no fetched ref. It was not accepted as an audit baseline. A controlled repair fetched public `main`, checked out `fbe33ca`, created the two detached worktrees, and restored the isolated clone's local remote metadata and Windows-safe `core.filemode=false` setting. All three worktrees then resolved to the same SHA, passed the stated Git integrity check, and had clean status.

The original reference checkout at `C:\Users\jared\.codex\HCJC` remains outside test execution. This audit writes only to its `audit-output\public-audit-2026-09-19` directory.

## Authorized public-only scope

| Included now | Explicitly deferred |
|---|---|
| Public site and public GitHub evidence, public-source and documentation claims, static source review, isolated dependency and test reproducibility, local evidence-chain verification, and synthetic failure-path fixtures. | Actions secrets or variables, Pages or Giscus private settings, PRA current configuration, any mail action, official-source person-linked comparison, legal conclusions, remediation, deployment, and external correspondence. |

## Dispatch contract

- A1 measures public deployment and freshness across scheduled cycles without treating workflow success as roster accuracy.
- A2 reproduces declared CI behavior only in its detached worktree and does not modify the active checkout.
- A3 maps sources to atomic claims and retains `not found` and `unknown` without converting them to fabrication.
- A4 uses only its isolated worktree, existing local artifacts, aggregate evidence, and synthetic fixtures. It must not place person-level data in an audit report.
- Every report is provisional until a later independent adversarial review. No report authorizes remediation.
