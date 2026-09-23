# Gate C Option 2: physical device performance protocol

Produced by D2 after C2 records Option 2 selection and the authority's acceptability definition. D2 returns the record to C2.

```
GATE C OPTION 2 - PHYSICAL DEVICE PERFORMANCE PROTOCOL

Pre-test (human, before any measurement):
  Named authority confirmed: [from C2 return]
  Acceptable outcome definition: [authority-defined, e.g. "cold search median <= X ms on target device"]
  Definition recorded UTC (must precede first sample):
  Metrics covered: [cold search suggestion completion, archive filter completion, homepage load]

Conditions (minimum two, per D2 coverage rule):
  Condition A: iOS Safari on [device]     Condition B: Android Chrome on [device]

Per condition:
  Device (physical, not emulated):
  OS version:
  Browser and version:
  Network: [actually constrained, or documented 3G simulation - never developer-tool throttle on desktop]
  URL: https://www.aretheyinjail.com or isolated build on local network
  Build identifier:
  Cache state: cleared before each cold-load sample

Measurements (three samples per metric per condition):
  Cold search suggestion completion: S1 / S2 / S3 / Median
  Search-index first byte or visible response: S1 / S2 / S3 / Median
  Archive filter completion: S1 / S2 / S3 / Median
  Homepage load: S1 / S2 / S3 / Median
  Tool or method per metric:

Context, not a criterion (Phase 2 lab, Chromium loopback, 390px, 4x CPU, 150 ms emulated latency, 1.6 Mbps):
  Cold search suggestion median: baseline 516 ms, remediation 912 ms
  Search-index compressed bytes: baseline 20,096, remediation 62,970
  Archive filter completion: baseline 483 ms, remediation 529 ms
  Recorded limits: loopback HTTP is not production HTTPS/CDN; ~1 ms TTFB is not an internet-latency result; three runs establish no statistical significance

Evidence:
  Tester name:
  UTC date:
  Recording or screenshot:

D2 result:
  Median within the authority's definition, per condition and metric: [Y/N]
  -> Y: emit OPTION-2-PASS for C2 re-ingestion
  -> N: emit OPTION-2-FAIL with measured deltas for the authority to choose risk-accept or remediate
  Any missing required field: return to C2 as INCOMPLETE; D2 does not supply it
```

## Rules

1. No criterion may be invented after seeing a result. The pre-test declaration timestamp is checked against the first sample timestamp.
2. D2 does not suggest, adjust, or interpret the threshold, and does not call a number good or bad beyond the binary comparison.
3. The lab context block is copied with its limits. Removing the limits turns context into a claim.
