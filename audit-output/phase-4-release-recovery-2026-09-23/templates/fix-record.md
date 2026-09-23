# Fix record

Human-completed. Required when a defect reaches `RETEST-READY`. One per fix; a fix covering two defects names both.

```
FIX RECORD - Defect [ID]

Fix description:
Commit or configuration change: [SHA, or the exact non-code change]
Behavioral path changed: [file paths]
Fixed by (name):
UTC date:
Rebuild required before retest: [Y/N]
Build identifier for retest: [URL plus commit or artifact manifest SHA-256]
Same-code-path defects closed by this fix: [IDs or NONE]
```

## Rules

1. The retest target is a build, not a working tree. A fix with no build identifier cannot advance to `RETEST-COMPLETE`.
2. Where a rebuild is required, BUILD-E's standing condition reopens: rebuild from the final reviewed commit, and record the new artifact identity.
3. D1 records this. D1 never authors it.
