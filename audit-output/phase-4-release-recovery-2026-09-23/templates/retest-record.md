# Retest record

Human-completed. Required when a defect reaches `RETEST-COMPLETE`.

```
RETEST RECORD - Defect [ID]

Retested by (name):
Fixer (name): [must differ from tester]
Environment parity with the original defect:
  Same tool or device: [Y/N - if N, state why the substitution is valid]
  Same OS version: [Y/N]
  Same browser version: [Y/N]
  Same screen reader and version: [Y/N]
Build or URL retested:
Checklist item re-executed (verbatim):
Dependent items also re-executed: [list, or NONE]
UTC date:
Outcome: [RESOLVED / STILL-FAILING / NEW-DEFECT-FOUND]
Evidence:
Notes (record exact announcements verbatim):
```

## Rules

1. Targeted retest only: the previously failing item plus items sharing the code path. Not a full checklist pass.
2. A different assistive technology, browser, or OS than the one that failed is not a retest. It is new coverage, and the original row stays open.
3. `NEW-DEFECT-FOUND` opens a second defect record and increments the cycle counter. At three cycles the defect escalates.
4. D1 must not mark a defect RESOLVED from a developer's report that a fix landed. This record, with a named tester, is the only path to RESOLVED.
