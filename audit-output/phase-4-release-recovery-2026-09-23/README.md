# Phase 4 release recovery architecture: state reconciliation

**Built:** 2026-09-23T03:25Z, at commit `d9ba0678d4171cf4e46fe62343cf5f1ef120ae8f`, branch `arena/01a0cc3e-hcjc`.
**Classification:** BUILD.
**Scope:** Non-happy-path gate recovery, sub-option evidence cycles, sweep closure event, evidence freshness boundary.
**Deliverables:** [PHASE-4-agent-prompts.md](PHASE-4-agent-prompts.md), [cross-agent-state-table.md](cross-agent-state-table.md), [templates/](templates/).

This directory does not replace the Phase 3 evidence. It supplements it, in the same manner as `../remediation-2026-09-22/closure/README.md` supplements the audit reports it executes.

## Verdict on the incoming brief

The diagnosis holds. Phase 3's contract covers happy paths and leaves three recovery paths unspecified, and a freshness rule is genuinely absent. That part is correct and is built below.

The brief's factual anchors do not hold. Four of seven load-bearing claims are false or mislabeled as of `d9ba0678`. Every D-agent was specified against them.

| ID | Claim in the Phase 4 brief | Status | What is actually in the repository |
| :-- | :-- | :-- | :-- |
| CLAIM-001 | State authority is `audit-output/phase-3-release-closure-2026-09-23/` | **FALSIFIED** | No such directory exists in the working tree or in any of the 107 commits reachable from `d9ba0678`. The real gate state lives in `audit-output/remediation-2026-09-22/closure/README.md` and `audit-output/remediation-2026-09-22/manual-qa-checklist.md` |
| CLAIM-002 | CI run `35809118882` captured 2026-09-23 | **VERIFIED** | Run `35809118882`, workflow `ci`, `conclusion=success`, created `2026-09-23T02:07:48Z`, `headSha=d9ba0678`, `headBranch=main`. Age at build: 1 hour, not 30 days |
| CLAIM-003 | B4 lab baseline is "cold search suggestion median 912 ms; search-index compressed 62,970 bytes" | **MISLABELED** | Those are the *remediation* column values. Baseline is 516 ms and 20,096 bytes (`closure/README.md:102-103`). 912 ms is the post-remediation regression that opened PERF-01, not a passing reference point |
| CLAIM-004 | Phase 1 UI source identity is 134 paths, captured 2026-09-23 | **FALSIFIED** | No 134-path manifest exists. Actual counts: `tested-source-sha256.json` 1,592 paths; `artifact-sha256.json` 2,447; `inputs-before.json` 1,536; `evidence-sha256.json` 43. Captured `2026-09-22T21:47:46.899Z` |
| CLAIM-005 | A composite action with `include-working-data: "true"`, `git commit-tree`, and `ARCHIVE_COMMIT` merged in "B5" | **FALSIFIED** | `.github/actions/` does not exist. `include-working-data`, `git commit-tree`, `ARCHIVE_COMMIT`, and `PENDING-NEXT-SWEEP` appear in no file in the tree or history. `sweep.yml` publishes via `scripts/commit_generated_changes.sh` |
| CLAIM-006 | Gates are A (screen reader), B (device), C (performance), D (deploy authorization) | **INCOMPLETE** | Real taxonomy is five gates plus two records: MANUAL-A, DEVICE-B, PERF-01 (Gate C), LIVE-D, BUILD-E (Gate E), plus CI-01 and RELEASE-01 (`closure/README.md:111-119`). LIVE-D is a live-site verification, not an authorization. BUILD-E has no D-agent owner |
| CLAIM-007 | The gate snapshot describes current release state | **SUPERSEDED** | The record says "not merged and not deployed." PR #485 merged `2026-09-22T22:31:45Z`. Pages deploy run `35809118858` succeeded `2026-09-23T02:07:48Z`. Scheduled sweep run `35800597032` failed `2026-09-23T00:07:01Z`, after the record was written |

CLAIM-001 and CLAIM-005 are the two that would have made Phase 4 inoperable. Every D-agent input contract pointed at a directory that does not exist, and D3 was built to track a mechanism that was never merged. The architecture in the brief is sound; its wiring diagram describes a different repository.

## Corrected state authority

| Purpose | Path | State at `d9ba0678` |
| :-- | :-- | :-- |
| Gate status of record | `audit-output/remediation-2026-09-22/closure/README.md` | "Local automated gates passed. Release closure remains blocked." |
| Manual checklist of record (human-approved) | `audit-output/remediation-2026-09-22/manual-qa-checklist.md` | "Execution status: NOT RUN." Approved 2026-09-22; approval is not test completion |
| Phase 2 lab evidence | `audit-output/remediation-2026-09-22/closure/lab-performance.json`, `README.md:96-107` | Three samples per build, loopback HTTP, one viewport, CPU 4x, 150 ms emulated latency, 1.6 Mbps |
| Identity manifests | `closure/tested-source-sha256.json`, `artifact-sha256.json`, `environment.json` | 1,592 / 2,447 paths; explicitly "not a deployed-build identifier" |
| CI evidence anchor | run `35809118882`, Pages deploy run `35809118858` | Both success on `d9ba0678` |
| Open scheduled-path item | scheduled sweep; last run `35800597032` failed at `00:07Z`, pre-fix | No scheduled run since the fix merged at `02:07Z` |

Phase 4 output is written to this directory. Phase 3 artifacts are never rewritten.

## The upstream gap this build must declare

The Phase 3 C-processors (C1 checklist ingestion, C2 Gate C option routing, C3 build isolation, C4 final determination) exist only as prompt text supplied in-session. No file in this repository defines them. Their return formats are therefore not machine-checkable, and D-agents have no committed upstream contract to parse.

Phase 4 cannot invent that contract, and it must not pretend one exists. Resolution: [upstream-phase3-interface.md](upstream-phase3-interface.md) records the interface exactly as the brief states it, labeled transcribed and unverified, plus the three fields Phase 4 strictly requires to activate. If Phase 3 is ever committed, that file is where the two architectures meet.

## Independent findings gathered during reconciliation

1. **LIVE-D's blocking evidence does not reproduce.** The record's blocker is a TLS probe failure: `curl: (35) SSL_ERROR_SYSCALL`, exit 35, at `2026-09-22T21:54:04Z` (`closure/production-probe.txt`). At `2026-09-22T23:55:54Z`, `live-parity.yml` run `35799729427` completed the step "Probe current production URLs" with `success`. Per `scripts/verify_live_url_parity.py:72-73`, a `URLError` from a TLS reset appends a non-404 error, and recovery mode only returns 0 when every error is a 404. A handshake failure could not pass that step silently. The live site answered at HTTP level from a GitHub runner after the failed manual probe.
2. **This workspace's egress cannot settle it either way.** At `03:12Z` here, `https://api.github.com` returned 200 while both `www.aretheyinjail.com` and `aicincy.github.io` connections reset immediately after the TLS Client Hello (TCP connect succeeded, no alert returned). One observation point is unreliable for negative findings. D-agents must not treat a single-path probe as authoritative in either direction.
3. **The log text of run `35799729427` was not retrievable.** `gh run view --log` failed with EOF from `results-receiver.actions.githubusercontent.com`. Finding 1 rests on step conclusions plus the script's control flow, not on log contents. That is stated rather than papered over.
4. **A real scheduled-path gap exists right now**, and it is the structural twin of what D3 was written to track. Commits `25080285` and `b47cf77b` changed `sweep.yml` and `rebuild.yml` to check out the fresh tip (`ref: github.ref`) so the publisher rebase fast-forwards. CI is green on the merge. The changed path runs only on the hourly cron, and the last cron run failed before the fix landed. D3 is rebuilt on this.

## Parking lot

| ID | Item | Why it is parked |
| :-- | :-- | :-- |
| PARK-001 | Phase 3 prompt text is not committed anywhere in the repository | Phase 4 declares the interface it needs; committing C-processors is the owner's call, not a Phase 4 side effect |
| PARK-002 | The 16 MB `audit-output/ui-ux-remediation-2026-09-22.zip` and other committed binaries in `audit-output/` | Out of scope for gate recovery; noted because this directory also adds tracked files |
| PARK-003 | Gate E (BUILD-E) says "rebuild from the final reviewed commit before deployment" and no agent owns that condition | D0 flags it; assigning it needs a human decision on who re-runs the build |
| PARK-004 | All manual and device owners remain unassigned per `closure/README.md:121` | Phase 4 adds an explicit STALLED state so unowned gates degrade visibly instead of silently waiting |
