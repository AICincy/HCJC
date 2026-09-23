# Gate C Option 3: threshold test protocol

Produced by D2 after C2 records Option 3 selection with a predeclared threshold.

```
GATE C OPTION 3 - THRESHOLD TEST PROTOCOL

Pre-test gate (D2 rejects activation if any field below is absent from the C2 return):
  Predeclared threshold, from the authority's decision record:
    Cold search suggestion median <= [___] ms
    [each additional metric the authority declared, with units]
  Authority (named in C2 return):
  Threshold declaration UTC date: [must precede first test execution timestamp]
  Metric coverage check: [cold search, archive filter, homepage load - all three, or the gap is named]

Test setup: identical to Option 2 (two conditions minimum, physical devices, three samples per metric per condition).

Result, per threshold:
  Metric: [name]
  Declared threshold: [value + unit]
  Measured median per condition: [A value / B value]
  Meets threshold: [Y/N]

D2 result:
  Every predeclared threshold met, every condition: [Y/N]
  -> Y: emit OPTION-3-PASS for C2 re-ingestion
  -> N: emit OPTION-3-FAIL naming the threshold and measured value for each missed metric
        The authority then chooses: remediate and retest, or convert to Option 1 risk acceptance.
```

## Rules

1. D2 rejects, not repairs. A missing threshold or a declaration date that does not precede testing returns the record to C2 for rejection and requests the field.
2. A threshold declared for one metric does not extend to another. Silence on archive filter completion means archive filter completion is unaddressed, and D2 says so rather than passing the tested subset.
3. D2 does not characterize margin. "0.4 percent under threshold" and "38 percent under threshold" receive identical formatting from D2; the number is the authority's to weigh.
