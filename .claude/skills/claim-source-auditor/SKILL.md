---
name: claim-source-auditor
description: >
  Verifies claims, quotes, timelines, and findings against supplied source
  files. Returns a source map with verified, conflicting, not-found, and
  manual-review statuses. Use when the user asks to fact-check a memo, audit,
  timeline, executive summary, research packet, complaint draft, or project
  brief against PDFs, XML, HTML, notes, screenshots, or exported chat logs
  before sending, publishing, or relying on the result. Also use when the
  user says "check this against the source," "verify the claims," "audit
  the facts," "does this match the record," or provides a draft alongside
  source documents. If the user is about to send something important, this
  skill applies.
---

# Claim Source Auditor

## Rules

IF the user provides a draft and source files:
THEN break compound paragraphs into individual claims. Search the source
set for each claim independently.

IF a claim matches exact text or faithful equivalent in the source:
THEN status is "verified." Cite the source filename and locator (page,
paragraph, XPath, or line range).

IF the source materially contradicts the claim:
THEN status is "conflicting." Provide side-by-side: claim language and
source language.

IF the claim is not found after exhaustive search of the defined scope:
THEN status is "not found in searched sources." Name the scope that was
searched. This does not mean the claim is false. It means the audit
cannot confirm it from available sources.

IF extraction fails (image content, low-quality scan, ambiguous wording):
THEN status is "manual review needed." State why automation fails.

IF the source exists outside the narrow audit scope but in the broader corpus:
THEN status is "verified in broader bundle." Note that the source is
outside the narrow scope.

Every claim gets exactly one status. Statuses do not blend. A claim is
not "partially verified."

## Output format

| Claim ID | Claim text | Status | Source file | Source locator | Basis note | Remediation note |
|---|---|---|---|---|---|---|

## References

- [references/status-taxonomy.md](references/status-taxonomy.md): Controlling
  specification for status assignments, required basis per status, selection
  rules, and forbidden patterns.
