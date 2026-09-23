# Upstream interface: what Phase 4 requires from Phase 3

**Status: transcribed, not verified.** Phase 4's brief names C1, C2, C3, C4 and a Phase 3 ingestion contract. No file in this repository at `d9ba0678` defines them, and the directory the brief names as state authority (`audit-output/phase-3-release-closure-2026-09-23/`) does not exist in the working tree or in any of the 107 reachable commits.

This file records the minimum interface Phase 4 needs so the contract is written down rather than assumed. It grants Phase 3 no authority the repository has not given it. If the Phase 3 prompt is committed, reconcile this file against it before any D-agent activates.

## Required fields per determination

| Emitter | Field | Why Phase 4 cannot proceed without it |
| :-- | :-- | :-- |
| C1 (checklist ingestion) | `gate`: `MANUAL-A` or `DEVICE-B` | D1 scopes one gate per instance; the shared-root-cause merge rule needs the gate identity |
| C1 | `determination`: `CLOSED` / `FAILED` / `INCOMPLETE` | Activation map; `CLOSED` forbids Phase 4 entirely |
| C1 | `defect`: the checklist "Failure record" table, with task text quoted verbatim | The checklist has no item IDs; verbatim task text is the only stable identifier |
| C2 (Gate C routing) | `option_selected`: `1`, `2`, or `3` | D2 never activates for Option 1 |
| C2 | `authority_name` | Risk acceptance and threshold ownership are human acts; unsigned records are rejected |
| C2 (Option 3 only) | `threshold_value` + `threshold_declared_utc` | D2 rejects activation without a predeclared threshold. The date must precede the first test timestamp |
| C2 (Option 2 only) | `acceptable_outcome_definition` | Same rule, applied to the qualitative criterion |
| C3 (build isolation) | `pending_note`: `PENDING-NEXT-SWEEP` and the path it describes | D3 must know which code path, in which workflow, at which cadence; the brief pointed at a mechanism that does not exist |
| C3 | `gate_e_ref` | BUILD-E carries the rebuild condition D3's standing note attaches to |
| C4 (final determination) | `blockers[]` | Any non-terminal dashboard row must appear; a row omitted from C4 output is a defect in C4, not a closure |
| any | `evidence_citations[]` | Every field needs a file path, line, or run ID. Uncited fields are treated as unsupplied |

## Return formats Phase 4 emits

| From | To | Payload |
| :-- | :-- | :-- |
| D0 | C1..C5 | reconciliation record, each delta marked RE-INGEST-BEFORE-D-ACTIVATION or NOTED-NO-EFFECT |
| D1 | C1 | addendum file path (defect, fix, retest or risk-acceptance record) plus the reviewer's applied initials in the checklist |
| D2 | C2 | PASS or FAIL evidence record per option template, with per-condition medians and binary criterion comparison |
| D3 | C3 and the standing note | SWEEP-VERIFIED or SWEEP-FAILED with run ID, timestamp, and behavior fields |
| D4 | applicable C-processor | freshness report with the exact command run per item |
| D5 | C-processor for LIVE-D | probe classification: SITE-EVIDENCE, PATH-EVIDENCE, or INCONCLUSIVE |

## Open items on the interface itself

1. Phase 3's valid return formats and CLOSED determination rules exist only in session text. Nothing binds them to this repository.
2. The brief's "Any automated evidence > 30 days" trigger needs a named owner for the periodic re-check; D4 has no scheduler of its own. It runs when a C-processor runs.
3. No C-processor in the brief emits a `BLOCKED` value for LIVE-D, though LIVE-D is recorded as `BLOCKED` in the repository. Phase 4 uses `BLOCKED` as an activation trigger for D5; Phase 3 should add it to the vocabulary or D5 will activate on nothing.
