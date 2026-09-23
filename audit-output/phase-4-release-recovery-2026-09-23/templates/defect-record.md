# Defect record

Written by D1. One file per defect: `defect-[GATE]-[ID].md`. Schema extends the "Failure record" table in `../../remediation-2026-09-22/manual-qa-checklist.md`; no new field names beyond phase, scope, and loop tracking.

```
DEFECT RECORD - [Gate A / Gate B] - Defect [ID]

Phase: [OPEN / IN-FIX / RETEST-READY / RETEST-COMPLETE / RESOLVED / WONT-FIX / STALLED / ESCALATED]
Cycle: [1 of 3]
Checklist item (verbatim task text):
Checklist pass criteria (verbatim):
Gate: [MANUAL-A / DEVICE-B]
Shared-root-cause link: [other defect ID, or NONE]

Defect detail (from C1):
  Tool or device:
  OS and version:
  Browser and version:
  Screen reader and version: [NVDA / JAWS / VoiceOver / other]
  URL and build identifier:
  Starting focus or location:
  Exact reproduction steps:
  Expected behavior:
  Observed behavior or exact announcement:
  Severity: [Blocking / Non-blocking]
  Theme: [Dark / Light / Both]
  Evidence: [recording, screenshot, or log reference]

Reported by:
UTC date reported:
```

## Rules

1. Record the exact announcement text. Do not paraphrase a screen reader, and do not infer behavior from the accessibility tree or axe output; the checklist forbids it.
2. Screenshots and recordings stay limited to what demonstrates the defect. Do not copy unnecessary personal record data into this file, issue titles, or public commentary.
3. An unavailable environment is `Not run`, never `Pass`. If a defect exists only because an environment could not be exercised, that is a coverage gap, not a defect; report it to C1 as such.
4. `RETEST-COMPLETE` requires retest-record.md to exist. `RESOLVED` requires a named tester distinct from the fixer.
