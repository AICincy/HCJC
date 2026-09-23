# Gate C decision record (fillable form)

Copy this file to `gate-c-decision-record-FILLED.md` before writing in it, so the blank form stays reusable. The filled copy is what C2 ingests.

This is the artifact the whole Gate C cycle has been waiting on. No committed record in this repository contains a performance threshold or a risk acceptance, and `closure/README.md:107` says that omission is deliberate: "No performance threshold or risk acceptance was invented." Do not let an agent fill any field below except as a scribe.

## Reference figures, with their limits attached

| Lab metric, median | Baseline (HEAD) | Remediation | Direction |
| :-- | --: | --: | :-- |
| Cold search suggestion completion | 516 ms | 912 ms | about 77 percent slower |
| Search-index compressed bytes | 20,096 | 62,970 | about 3.1 times larger |
| Homepage DOM interactive | 1,364 ms | 366 ms | improved |
| Homepage FCP and observed LCP | 1,364 ms | 1,040 ms | improved |
| Archive DOM interactive | 2,474 ms | 2,095 ms | improved |
| Archive filter completion | 483 ms | 529 ms | about 10 percent slower |

Method limits, copied so no reader treats these as field data: local gzip servers over loopback HTTP, not production HTTPS or CDN; 390 px viewport; fourfold CPU slowdown; 150 ms configured emulated latency; 1.6 Mbps; cache disabled; three samples per build. The record states the roughly 1 ms TTFB is not an internet-latency result and that three runs establish no statistical significance.

## Decision

```
GATE C DECISION RECORD

Named authority:
Authority role and how they hold it:
UTC date of decision:
Candidate build this decision covers: [commit SHA, and CI run ID for it]

Option chosen: [1 | 2 | 3]

Option 1, risk acceptance:
  Regression accepted, in the authority's own words:
  Affected user population and the concrete harm:
  Why acceptance rather than remediation:
  Review or revisit trigger:

Option 2, physical-device test:
  Acceptability definition, written before any measurement:
    e.g. "cold search suggestion median <= [___] ms on [device] over [network]"
  Metrics the definition covers: [must name all three: cold search suggestion
    completion, archive filter completion, homepage load, or state the gap]
  Conditions required: [iOS Safari device, Android Chrome device, network per condition]

Option 3, threshold test:
  Threshold per metric, with units:
    Cold search suggestion median <= [___] ms
    Archive filter completion     <= [___] ms
    Homepage DOM interactive      <= [___] ms
    [additional]
  Threshold declaration UTC timestamp: [must precede the first test sample timestamp]
  Consequence if a threshold is missed: [remediate and retest | convert to Option 1]
```

## What happens next

1. Return the filled record to the Phase 3 C2 processor for the Gate C determination.
2. Option 1: C2 determines on the existing lab evidence plus this record. No D-agent activation.
3. Option 2 or 3: Phase 4 D2 activates, supplies the protocol, and validates the evidence. D2 rejects the record if the definition or threshold is missing, and never proposes a number.
4. D2's PASS or FAIL returns to C2. Only C2 closes Gate C.

## Signature block

```
Signed by:
Signature or confirming comment URL:
UTC date:
Recorded in: [file path of the filled copy]
```
