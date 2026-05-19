---
name: authority-currency-auditor
description: >
  Audits cited legal authorities, regulatory references, and factual assertions
  for currency, accuracy, and correct application. Use when the user needs to
  verify statutes have not been amended or repealed, regulatory citations
  reflect current rules, factual claims match the supplied record, or a work
  product's legal foundation is reliable before filing. Also use when the user
  says "check the citations," "verify this is current," "audit the authorities,"
  "is this statute still good," or asks about any specific ORC section, U.S.C.
  provision, or C.F.R. part. If the user is about to file, publish, or send
  anything with legal citations, this skill applies.
---

# Authority Currency Auditor

## Rules

IF the user provides a work product with legal citations:
THEN extract every authority, regulation, case, and factual assertion into
an inventory table before checking any individual item.

IF verifying a statute:
THEN check whether the cited provision is still in force as of today.
Check for amendments, recodifications, or sunset clauses. Use the
canonical source for that authority type (see Verification Sources below).

IF verifying a case citation:
THEN check whether the case has been overruled, distinguished in the
relevant jurisdiction, or limited by subsequent authority.

IF verifying a factual assertion tied to a supplied record:
THEN verify the claim against the specific source document, page, date,
or data point cited.

IF a verification source is inaccessible:
THEN flag the item as "unverifiable" with the specific blocking reason.
Do not treat inability to verify as confirmation.

IF the audit finds an authority that is amended, superseded, or repealed:
THEN provide a correction note with the current authority, effective date,
and the specific discrepancy. Do not rewrite the entire work product.

## Status taxonomy

| Status | Meaning |
|---|---|
| current | Verified as in force and correctly applied as of today |
| amended | Still exists but amended in a way that may affect the work product |
| superseded | Replaced by a successor provision or ruling |
| repealed | No longer in force |
| misapplied | Current but the work product applies it incorrectly |
| factually-inaccurate | Does not match the cited source record |
| unverifiable | Cannot be confirmed or denied; blocking reason noted |

## Verification sources

| Authority type | Primary source |
|---|---|
| Federal statutes | uscode.house.gov |
| Federal regulations | ecfr.gov, federalregister.gov |
| Ohio Revised Code | codes.ohio.gov/ohio-revised-code |
| Ohio Administrative Code | codes.ohio.gov/ohio-administrative-code |
| HHS OCR guidance | hhs.gov/hipaa |
| Federal case law | CourtListener, Justia, or issuing court PACER |
| Ohio case law | sconet.state.oh.us |

## Output format

One table. One row per audited item.

| Identifier | Type | Citation | Status | Basis | Effective date | Correction note |
|---|---|---|---|---|---|---|

End with a summary: total items audited, items confirmed current, items
requiring update, items unverifiable.
