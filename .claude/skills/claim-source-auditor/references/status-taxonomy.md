# Claim Source Auditor - Status Taxonomy Reference

**Last updated:** May 6, 2026

This taxonomy is the controlling specification for status assignments in claim-source audits. Every audit row carries exactly one status. Statuses do not blend.

## Status Definitions

### verified
The claim is supported by exact text or faithful equivalent in the searched source set. Citation must include source filename and the locator within the file (page, paragraph, XPath, or line range).

**Required basis:** A specific source pointer.
**Example basis:** "UCH/DOC0001.XML, section 30954-2, observation @code='2951-2', value=139 mmol/L, time=2020-11-18."

### verified in broader bundle
The claim is supported by source content that exists in the broader corpus available to the auditor but outside the narrow packet under review. Use when the audit scope was defined as a specific subset and the supporting content lives elsewhere.

**Required basis:** Source pointer plus an explicit note that the source is outside the narrow scope.
**Example basis:** "Source found in CCHMC/DOC0042.XML; outside the UCH-only scope of the present audit."

### conflicting
The source materially contradicts the draft claim. The claim asserts X; the source establishes not-X or a materially different proposition. Use when the contradiction is concrete and documentable, not when the source is silent.

**Required basis:** Side-by-side excerpt showing claim language and source language.
**Example basis:** "Claim states 'patient was prescribed gabapentin in 2018'; source UCH/DOC0001.XML medication section shows gabapentin discontinued in 2017."

### not found in searched sources
The claim is not located in the named search scope. Use when the auditor exhaustively searched the defined scope and found no supporting content. The claim may be true; the audit cannot confirm it from available sources.

**Required basis:** Statement of what scope was searched.
**Example basis:** "Searched all 87 UCH XML files and the 170-page UCH PDF; no record of the asserted referral to Dr. X found."

**Critical:** This status does not establish that the claim is false. Absence of evidence is not evidence of absence. Distinguish source absence from search-scope limitation.

### manual review needed
The auditor cannot confirm or deny the claim with automated extraction. Use when the source is likely to contain the supporting content but extraction fails - image content, low-quality scan, ambiguous wording, or content that requires human judgment.

**Required basis:** Statement of why automation fails.
**Example basis:** "Claim asserts a verbal referral. The source PDF includes a scanned hand-written note at page 47 that may contain the referral but is not machine-readable; manual review required."

## Status Selection Rules

1. Every claim receives exactly one status.
2. Use **verified** when both exact match and citation are available.
3. Use **verified in broader bundle** when the source exists outside the narrow audit scope and the auditor confirms its existence.
4. Use **conflicting** when the source materially contradicts. Do not use **conflicting** when the source is merely silent.
5. Use **not found in searched sources** when the source is silent and the search scope is named.
6. Use **manual review needed** when extraction fails on otherwise relevant source.
7. When uncertain between **verified** and **manual review needed**, choose **manual review needed**. The downstream cost of a false positive exceeds the cost of a false negative.

## Forbidden Patterns

- Do not use **verified** without an exact-text or faithful-equivalent match.
- Do not use **conflicting** when the source is silent on the claim.
- Do not use **not found** without naming the searched scope.
- Do not blend statuses. A claim is not "partially verified."
- Do not paraphrase a quote and call it verified. The exact wording or a faithful equivalent must appear in the source.

## Audit Output Schema

Each row in the audit table carries:

| Column | Required | Type |
|--------|:--------:|------|
| claim_id | yes | string |
| claim_text | yes | string |
| status | yes | one of the six taxonomy values |
| source_file | conditional | string (required when status is verified, verified-in-broader-bundle, or conflicting) |
| source_locator | conditional | string (page, paragraph, XPath, line range) |
| source_excerpt | conditional | string (300 chars max; required when status is verified or conflicting) |
| basis_note | yes | string (200 chars max; explains the status assignment) |
| remediation_note | optional | string (recommended action when status is conflicting, not-found, or manual-review-needed) |

The `basis_note` is mandatory regardless of status. Every status assignment must be defensible by reference to a specific basis.
