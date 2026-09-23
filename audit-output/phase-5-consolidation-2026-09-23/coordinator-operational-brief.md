# HCJC release coordinator brief (Phase 5, E1)

**Revision:** Phase 5, 2026-09-23T03:45Z.
**Valid for:** commit `d9ba0678d4171cf4e46fe62343cf5f1ef120ae8f`. Re-issue this brief whenever a commit touching anything outside `data/` and `docs/` lands on `main`; every gate below is bound to that build.
**Reader assumption:** you have read no phase document.
**Authority:** this brief grants nothing and determines nothing. Each instruction cites its source; the source holds the rules.

Operate from five files. Everything else is background.

| File | Use |
| :-- | :-- |
| `audit-output/remediation-2026-09-22/manual-qa-checklist.md` | The checklist a human tester fills in. Gates A and B live here |
| `audit-output/remediation-2026-09-22/closure/README.md` | Status of record for every gate. Read the table at lines 111-119 |
| `audit-output/phase-4-release-recovery-2026-09-23/cross-agent-state-table.md` | The dashboard. Your working view of what is open |
| `audit-output/phase-4-release-recovery-2026-09-23/recovery-state.json` | The machine view. Update it first, the dashboard second |
| `audit-output/phase-5-consolidation-2026-09-23/gate-d-failure-path.md` | What to do if production breaks after you authorize it |

## Section 1: What is done. Read only, no action required

**Automated gates.** Python 3.13 and 3.14 CI passed on `d9ba0678` (run `35809118882`, 2026-09-23T02:07:48Z): ruff, mypy, pip-audit, pytest, and both WAF-evidence chain steps. Source: `closure/README.md:118`, and the run itself at `https://github.com/AICincy/HCJC/actions/runs/35809118882`.

**Build isolation (Gate E) passed locally.** The remediation build reproduced from the same inputs, with the same four optional-feed failures as the fresh HEAD baseline and no canonical-data changes. Source: `closure/README.md:117` and `closure/build-final.txt`. Its condition, "rebuild from the final reviewed commit before deployment", is still owed if `main` moves.

**The UI remediation itself merged.** PR #485 merged 2026-09-22T22:31:45Z, contrary to the closure record's "not merged". A Pages deploy for `d9ba0678` succeeded (run `35809118858`). Source: `gh pr view 485 --json state,mergedAt`, and the divergence recorded in `closure/README.md:119`.

**Accessibility and layout automation passed, and does not substitute for you.** 72 axe scans with zero violations, seven viewport widths in both themes, 89,008 local reference checks with zero missing paths. The record states plainly that Linux headless Chromium results do not substitute for NVDA, JAWS, or VoiceOver. Source: `closure/README.md:23-45`, `:113`.

**Performance has a known regression, unresolved.** In a small lab sample, cold search suggestion completion went 516 ms to 912 ms and the compressed search index 20,096 to 62,970 bytes, while homepage DOM interactive improved 1,364 ms to 366 ms. No threshold and no risk acceptance has been set, deliberately. Source: `closure/README.md:98-107`.

## Section 2: What you need now. Four items, no dependencies between them

Run these in parallel. Do not sequence them behind each other.

### Item A: Screen-reader testing (Gate A)

- **Who:** a human tester with NVDA on Windows, JAWS on Windows, and VoiceOver on iPhone. Not a developer who built the change.
- **What to open:** `audit-output/remediation-2026-09-22/manual-qa-checklist.md`, sections "Record the test environment", "Required environments", "Keyboard and screen-reader checks".
- **What to do:** work the 12 rows of the keyboard and screen-reader table on the identified build, exercising dark and light themes, and use a record with multiple charges and case links for the table rows. Record any duplicate or confusing announcement verbatim.
- **Where to record:** in that same checklist, the environment table plus one `Done`/`Pass` mark per row, and the "Release sign-off" table at the bottom. If anything fails, fill the "Failure record" table too.
- **What makes it valid:** tester name, date, preview URL plus revision or build identifier, device and OS, browser and version, screen reader and version, theme, text size or zoom, and a Pass, Fail, or Not run result per row.
- **When done:** the completed checklist goes to the Phase 3 C1 processor for a CLOSED or FAILED determination. Until that determination exists, no one calls Gate A closed.
- **Source:** `closure/README.md:113`, `manual-qa-checklist.md` header and "Failure record".

### Item B: Physical device testing (Gate B)

- **Who:** a human with a real iPhone and a mid-range Android phone.
- **What to open:** same file, sections "iPhone, touch and zoom" and "Required environments".
- **What to do:** the six device rows, covering VoiceOver on and off, pinch zoom and text size, rotation, tier-badge taps beside record links, sticky-control overlap, and legibility in both themes.
- **Where to record:** the same checklist rows and sign-off table.
- **What makes it valid:** device model and OS version per row, browser version, and a result per row. An unavailable environment is marked `Not run`, never `Pass`.
- **When done:** to C1 with the Gate A results, since both feed one checklist.
- **Source:** `closure/README.md:114`, `manual-qa-checklist.md`.

### Item C: Performance authority decision (Gate C)

- **Who:** a named individual who owns the risk of shipping a slower cold search. Currently `NEEDS-OWNER`; `closure/README.md:121` records every owner as unassigned. You must name this person before anything else in this item can happen.
- **What to open:** `templates/gate-c-decision-record.md` in this directory. Copy it to `gate-c-decision-record-FILLED.md` before anyone writes in it, so the blank form stays reusable.
- **What to do:** choose Option 1 (accept the risk as documented), Option 2 (require a physical-device test against a stated acceptability definition), or Option 3 (declare a numeric threshold in advance and test it). Fill the human fields only.
- **Where to record:** the decision record file: option chosen, authority name, UTC date, and either the acceptability definition (Option 2) or the numeric thresholds (Option 3).
- **What makes it valid:** a name, a UTC date, and a criterion written **before** any new measurement is taken. For Option 3 the declaration timestamp must precede the first test timestamp; that ordering is what makes the test meaningful.
- **Option 2 or 3 follow-up:** those activate Phase 4 D2, which supplies the protocol and rejects the record if the criterion is missing. D2 will not propose a number for you.
- **Source:** `closure/README.md:107,115`, `PHASE-4-agent-prompts.md` D2, `audit-output/phase-4-release-recovery-2026-09-23/templates/gate-c-option-2.md` and `gate-c-option-3.md`.

### Item D: Build isolation and sweep closure note

- **Who:** no reviewer is required for the merge itself; see the governance note below. Someone named does need to own the standing note.
- **What to open:** `closure/README.md` line 117 (BUILD-E) and `audit-output/phase-4-release-recovery-2026-09-23/cross-agent-state-table.md` row 6.
- **What to do:** confirm the release build you are shipping is the one that was tested, by comparing the artifact and source manifest identifiers in `closure/README.md` "Exact tested build" against the deployed commit. Then acknowledge that the scheduled sweep publish path is unconfirmed: `PENDING-NEXT-SWEEP`, tracked by D3, and not a blocker.
- **Where to record:** the standing note in the release readiness record, updated to `SWEEP-VERIFIED` with the CI run ID and UTC timestamp when D3 emits it. See `audit-output/phase-4-release-recovery-2026-09-23/templates/sweep-verification.md`.
- **What makes it valid:** a run ID, a UTC timestamp, and every behavior field `Y`.
- **Sweep note:** the cron cadence is hourly but best-effort. As of 03:21Z the last scheduled run was 00:07Z and it failed before the fix, so this item is genuinely open, and it needs no action from you beyond watching for the note to clear.
- **Source:** `closure/README.md:117`, `PHASE-4-agent-prompts.md` D3, `.github/workflows/sweep.yml`, `scripts/commit_generated_changes.sh:34`.

**Governance collision you must resolve, not route around.** `CLAUDE.md` under "Merge discipline" carries an owner directive dated 2026-07-23: the agent merges its own PRs once verification passes, the owner does not merge. The Phase 4 and Phase 5 briefs assume a named human reviewer approves an isolation merge before it happens. Those two cannot both be true for this release. Either the directive is waived for release-bearing merges, which means you name a reviewer, or it stands, which means no human pre-merge review exists and post-merge verification is the only control. Pick one and write the choice in `DECISIONS.md`, where this project already records exactly this kind of owner decision.

## Section 3: If something fails or changes

| Situation | First action | Then |
| :-- | :-- | :-- |
| Screen-reader or device test finds a blocking defect | Fill the "Failure record" table in the checklist | Phase 4 D1 opens a defect record; `templates/defect-record.md` |
| Retest shows the same defect again | Keep the record open; do not mark RESOLVED | D1 cycles up to three times, then escalates to fix, accept, or descope |
| No tester or device exists | Mark the row `Not run` and write `STALLED` on the dashboard row | Naming the missing role is the action. Silence is not a state |
| Authority picks Option 2 or 3 | Fill the pre-test declaration before testing | Phase 4 D2 runs the protocol and returns PASS or FAIL to C2 |
| You want to accept the performance regression | Record Option 1 with your name and the affected population in plain terms | C2 determines the gate; no evidence cycle needed |
| CI turns red on a new `main` commit | Read the failure | Phase 4 D4 will call the tip evidence invalid; re-issue gate evidence against the new tip |
| Any gate evidence reaches 2026-10-23 | Run the D4 assessment | `templates/freshness-report.md` |
| The candidate commit changes for any reason | Immediately re-run the D4 test before anyone re-reads a gate status | CI validity is bound to `d9ba0678` |
| Post-deployment verification fails, or a deploy does not land | `gate-d-failure-path.md` Step 0 first: confirm it is the site, not your network | Class 1, 2a, 2b, or 3 routing; 2a needs the Rollback Authorization Record |
| The two state views disagree | Stop. Read `recovery-state.json`, correct the dashboard | `tests/test_recovery_state.py` is the mechanical form of this rule |

## Section 4: Unresolved identities

Nothing in the architecture can supply these names, and no gate closes without them.

| Item | Required role | Named individual | Date assigned |
| :-- | :-- | :-- | :-- |
| Gate C decision | Named individual who sets the performance threshold or accepts the regression | `NEEDS-OWNER` | |
| Isolation merge and standing note | Named `HCJC` maintainer or release authority | `NEEDS-OWNER` | |
| Production outage ownership | Named individual for a Class 1 total outage, since no runbook file exists | `NEEDS-OWNER` | |
| Actions-versus-branch deploy decision (F-01) | Named maintainer to reconcile `pages.yml` with the `CLAUDE.md` directive | `NEEDS-OWNER` | |
| `AAI-HCJC-v2` domain claim | Organization owner decision on the duplicate's `CNAME` | `NEEDS-OWNER` | |

## Section 5: How to know release is authorized

All three must hold, mechanically rather than by judgment:

1. Every row of the gate table in `closure/README.md:111-119` above Gate D shows `CLOSED` or `RISK-ACCEPTED`.
2. `recovery-state.json` shows `c4_activation.eligible == true`. Do not hand-edit that flag; `tests/test_recovery_state.py` recomputes it from the items and fails CI on a mismatch.
3. No `d1`, `d2`, `d4`, or `d5` item sits in a non-terminal state, including `STALLED`, `ESCALATED`, and `PENDING-BLOCKED`. `d3_sweep` is excluded by design and never blocks authorization.

Then proceed through the Gate D authorization in `gate-d-failure-path.md`'s companion record and the deployment sequence in the Phase 3 C4 contract. If `main` moved since `d9ba0678`, start over at Section 2 items C and D against the new build; automated evidence renews with a CI run, human testing does not.

## Section 6: Contacts

You fill this in. Nothing here invents a name.

| Role | Name | Contact | Escalate when |
| :-- | :-- | :-- | :-- |
| Release authority | `NEEDS-OWNER` | | Gate D authorization, any risk acceptance, any rollback |
| Performance authority | `NEEDS-OWNER` | | Gate C decision and any D2 activation |
| `HCJC` maintainer | `NEEDS-OWNER` | | CI, merge, deploy, and F-01 |
| Screen-reader tester | `NEEDS-OWNER` | | Gate A execution |
| Device tester | `NEEDS-OWNER` | | Gate B execution |
| Data and legal review | `NEEDS-OWNER` | | Any change to roster content, legal framing, or FCRA copy |

## What this brief deliberately does not contain

No gate rule appears above. Every rule lives in the cited phase document, so a rule change needs one edit rather than three. No section tells you to trust an agent's local determination: D-agents produce evidence and C-processors decide. Section 1 states closed items with citations; Sections 2 through 6 state open ones with owners. The `NEEDS-OWNER` rows are the current critical path, and no further agent phase will resolve them.
