# Recovery state schema

**Normative reference for `recovery-state.json`.** `tests/test_recovery_state.py` enforces agreement between this document and the test constants. Changing one without the other fails CI.

**Machine-readable convention.** The `VOCAB` and `TRANS` lines below are parsed by the test. One per line, colon after the keyword, comma-separated values, `->` between source and target set, `|` between targets.

## Top-level keys

| Key | Type | Meaning |
| :-- | :-- | :-- |
| `schema_version` | int | Bump on incompatible change; the test pins the expected value |
| `as_of_date_utc` | str | ISO-8601 UTC, ends in `Z` |
| `state_authority` | str | Path of the gate status of record |
| `candidate` | object | `{ "commit": str, "ci_run_id": int }`, the release candidate under review |
| `phase_3_snapshot` | object | Gate statuses mirrored from the status of record, never invented here |
| `recovery_items` | object | One entry per tracked item, keyed as below |
| `c4_activation` | object | `{ "eligible": bool, "rationale": str }` |
| `events` | array | Append-only transition log |

## recovery_items keys

`d0_snapshot`, `d1_gate_a`, `d1_gate_b`, `d2_option_2`, `d2_option_3`, `d3_sweep`, `d4_freshness`, `d5_live_probe`.

Every item carries `agent`, `status`, `feeds_back_to`. `d1_gate_a` and `d1_gate_b` also carry `defects`; `d2_option_2`, `d2_option_3` carry `attempts`; `d3_sweep` carries `verification_runs`; `d4_freshness` carries `aged_items`; `d5_live_probe` carries `observations`.

## Status vocabulary

VOCAB gate_status: CLOSED, FAILED, NOT-RUN, OPEN, BLOCKED, LOCAL-PASS, PASSED, RISK-ACCEPTED, SUPERSEDED-PARTIAL
VOCAB d0: NOT-RUN, RECONCILE-FIRST, DELTAS-EMITTED, CURRENT
VOCAB d1_gate: NOT-ACTIVATED, IN-PROGRESS, STALLED, READY-FOR-C1-REINGESTION
VOCAB d1_defect: OPEN, IN-FIX, RETEST-READY, RETEST-COMPLETE, RESOLVED, WONT-FIX, STALLED, ESCALATED
VOCAB d2_option: NOT-ACTIVATED, PENDING, PENDING-BLOCKED, INCOMPLETE, PASS, FAIL, STALLED, READY-FOR-C2-REINGESTION
VOCAB d3: NOT-ACTIVATED, PENDING-NEXT-SWEEP, SWEEP-VERIFIED, SWEEP-FAILED
VOCAB d4: NOT-AGED, VALID-NO-ACTION, RENEWAL-REQUIRED, RENEWED
VOCAB d5: NOT-ACTIVATED, INCONCLUSIVE-EVIDENCE, SITE-EVIDENCE, PATH-EVIDENCE, STALLED

Three values the Phase 5 brief omitted are required here: `STALLED`, `ESCALATED`, `PENDING-BLOCKED`. All three exist because the record at `closure/README.md:121` reports unassigned owners, and an unowned item must be a state rather than a silence. The brief's `NOT-AGED` and `RENEWED` are adopted.

## Transitions

`-> NONE` marks a terminal state: the parser reads it as an empty successor set. A terminal state still appears as a source, because the test must know that leaving it is illegal.

TRANS d0: NOT-RUN -> RECONCILE-FIRST | DELTAS-EMITTED | CURRENT
TRANS d0: RECONCILE-FIRST -> DELTAS-EMITTED | CURRENT
TRANS d0: DELTAS-EMITTED -> CURRENT
TRANS d0: CURRENT -> RECONCILE-FIRST
TRANS d1_gate: NOT-ACTIVATED -> IN-PROGRESS | STALLED
TRANS d1_gate: IN-PROGRESS -> READY-FOR-C1-REINGESTION | STALLED
TRANS d1_gate: STALLED -> IN-PROGRESS
TRANS d1_gate: READY-FOR-C1-REINGESTION -> IN-PROGRESS
TRANS d1_defect: OPEN -> IN-FIX | STALLED | ESCALATED
TRANS d1_defect: IN-FIX -> RETEST-READY | OPEN
TRANS d1_defect: RETEST-READY -> RETEST-COMPLETE | OPEN
TRANS d1_defect: RETEST-COMPLETE -> RESOLVED | OPEN | ESCALATED
TRANS d1_defect: ESCALATED -> WONT-FIX | IN-FIX
TRANS d1_defect: STALLED -> OPEN
TRANS d1_defect: RESOLVED -> NONE
TRANS d1_defect: WONT-FIX -> NONE
TRANS d2_option: NOT-ACTIVATED -> PENDING | PENDING-BLOCKED
TRANS d2_option: PENDING-BLOCKED -> PENDING
TRANS d2_option: PENDING -> INCOMPLETE | PASS | FAIL | STALLED
TRANS d2_option: INCOMPLETE -> PENDING
TRANS d2_option: FAIL -> PENDING
TRANS d2_option: PASS -> READY-FOR-C2-REINGESTION
TRANS d2_option: STALLED -> PENDING
TRANS d2_option: READY-FOR-C2-REINGESTION -> PENDING
TRANS d3: NOT-ACTIVATED -> PENDING-NEXT-SWEEP
TRANS d3: PENDING-NEXT-SWEEP -> SWEEP-VERIFIED | SWEEP-FAILED
TRANS d3: SWEEP-FAILED -> PENDING-NEXT-SWEEP
TRANS d3: SWEEP-VERIFIED -> NONE
TRANS d4: NOT-AGED -> VALID-NO-ACTION | RENEWAL-REQUIRED
TRANS d4: VALID-NO-ACTION -> RENEWAL-REQUIRED | VALID-NO-ACTION
TRANS d4: RENEWAL-REQUIRED -> RENEWED
TRANS d4: RENEWED -> VALID-NO-ACTION
TRANS d5: NOT-ACTIVATED -> INCONCLUSIVE-EVIDENCE | SITE-EVIDENCE | PATH-EVIDENCE | STALLED
TRANS d5: INCONCLUSIVE-EVIDENCE -> SITE-EVIDENCE | PATH-EVIDENCE | STALLED
TRANS d5: PATH-EVIDENCE -> INCONCLUSIVE-EVIDENCE | SITE-EVIDENCE
TRANS d5: SITE-EVIDENCE -> NONE
TRANS d5: STALLED -> INCONCLUSIVE-EVIDENCE

`RESOLVED` and `WONT-FIX` are terminal for a defect. A defect that is reopened after a `RESOLVED` retest is a new defect record with `supersedes`, not a status rewind: a resolved-then-reopened defect is a different fact about the build.

`SWEEP-VERIFIED` and `SWEEP-FAILED -> PENDING-NEXT-SWEEP` reflect that a failed sweep re-arms on the next cron rather than retrying immediately.

## C4 eligibility

D3 status is excluded from the C4 eligibility calculation by design; see Phase 4 D3, which is post-LIVE-D.

The eligible computation is the conjunction of exactly these clause names:

- `phase_3_snapshot.gate_a == "CLOSED"`
- `phase_3_snapshot.gate_b == "CLOSED"`
- `phase_3_snapshot.gate_c == "CLOSED"`
- `phase_3_snapshot.isolation_merge == "CLOSED"`
- `d1_gate_a.status not blocking`
- `d1_gate_b.status not blocking`
- `d2_option_2.status not blocking`
- `d2_option_3.status not blocking`
- `d4 has no RENEWAL-REQUIRED item`

Blocking sets: `d1_gate` blocks on `IN-PROGRESS`, `STALLED`, `READY-FOR-C1-REINGESTION`. `d2_option` blocks on `PENDING`, `PENDING-BLOCKED`, `INCOMPLETE`, `STALLED`. Any `OPEN`, `IN-FIX`, `RETEST-READY`, `RETEST-COMPLETE`, `ESCALATED` defect inside a D1 item blocks it, independent of the instance status.

## Event log

Each event: `event_id`, `utc_timestamp`, `item`, `from_status`, `to_status`, `actor`, `evidence` (list), `feeds_back_to`.

- `events` is append-only. No `event_id` repeats. The array order is the emission order.
- `utc_timestamp` is ISO-8601 with a trailing `Z`.
- `actor` is a non-empty name or handle. `recovery-state-agent` is not acceptable for a human-only act; the actor is the human who performed or authorized it.
- `from_status` of event *n* must equal `to_status` of event *n-1* for the same `item`. First event per item must use the item's initial status (`NOT-RUN`, `NOT-ACTIVATED`, or `NOT-AGED`).

## Dashboard agreement

`cross-agent-state-table.md` in this directory is the human-facing view. The test does not parse its prose. It asserts that every `recovery_items` key appears in the dashboard file, so an item cannot exist in JSON while missing from the table a human reads.

- `sync_note` on each item names the dashboard row that carries it.

## Synchrony check

The test compares the last commit touching `recovery-state.json` against the last commit touching `cross-agent-state-table.md`, using git history rather than file mtimes. mtimes are set at checkout and are equal for every tracked file, so an mtime rule can never fire in CI and fires arbitrarily in a working tree.

- A dashboard commit more than 30 minutes newer than the state file yields a warning, never a failure. It is a coordination prompt, consistent with Phase 4 D4's treatment of age.
