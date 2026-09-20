# Cover memo for counsel: the WAF-block evidence dossier

**Status: DRAFT entry point. Counsel reviews and verifies all citations.**
Date drafted: 2026-05-20. This memo is the single starting point for the
documents in `audit/14` through `audit/18` and the data files they reference.

## The claim in one paragraph

The Hamilton County Justice Center inmate roster that the Hamilton County
Sheriff's Office (HCSO) publishes is a public record under R.C. 149.43. HCSO's
web application firewall blocks JCStream's automated retrieval of that roster
from the GitHub Actions IP range while continuing to serve the same records to
ordinary browser traffic. JCStream documents the block as durable, timestamped
evidence and does not attempt to evade it. The record below supports a written
R.C. 149.43(B) request and, if that is ignored or denied, an R.C. 149.43(C)
action in mandamus.

## The dossier

| File | Role |
|---|---|
| `audit/14_hcso_waf.md` | Diagnosis (WAF blocking the runner IP), the do-not-evade posture, and the evidence-file schema. |
| `data/waf_block_log.json` | Append-only, hash-chained record of each blocked sweep cycle and each recovery (status, headers, body sample, SHA-256). |
| `data/egress_evidence.json` | Snapshot tying the blocked source to GitHub's published Actions IP ranges. |
| `audit/15_pra_149_43B_request.md` | Draft written R.C. 149.43(B) request (machine-readable roster export + the WAF rule/policy). |
| `audit/16_evidence_affidavit.md` | Draft operator affidavit authenticating the log and its hash chain. |
| `audit/17_mandamus_petition.md` | Draft R.C. 149.43(C) petition for a writ of mandamus. |
| `audit/18_offplatform_capture.md` | Runbook to corroborate a block from a non-GitHub IP. |

## How the record is kept honest

Three independent integrity layers stand behind `data/waf_block_log.json`:

1. **Per-body SHA-256.** Each block sample carries the SHA-256 of the response
   body, so the captured block page cannot be altered undetectably.
2. **`prev_sha256` hash chain.** Each record hashes the previous record, so any
   edit or removal of an earlier record is detectable. Run
   `python -m scraper.verify_block_log` to check the chain (exit 0 intact,
   1 broken).
3. **Git commit history.** The sweep commits the log every cycle to a public
   repository, giving an external, timestamped, third-party-hosted seal.

The off-platform runbook (`audit/18`) adds a second source: a capture from a
non-GitHub IP plus a Wayback snapshot, showing the records served normally
while the automated path is denied.

## The legal hooks (counsel to verify all citations)

- The roster is a public record (R.C. 149.43(A)(1)).
- The records must be made available within a reasonable period; a denial must
  be in writing with its legal authority (R.C. 149.43(B)).
- A requester may choose the medium the office keeps the record in, which is the
  basis for the machine-readable export in `audit/15` (R.C. 149.43(B)(6)).
- If the request is ignored or denied, R.C. 149.43(C) provides a mandamus
  remedy with potential statutory damages, court costs, and attorney fees.
- The log is offered as a contemporaneous business record under Ohio
  Evid.R. 803(6); the affidavit in `audit/16` lays the foundation.

## Suggested order of operations

1. Read `audit/14` (diagnosis + posture).
2. Send the `audit/15` request; preserve the dated send confirmation.
3. If ignored or denied, execute the `audit/16` affidavit and run the verifier
   for its exhibit.
4. During a live block, run the `audit/18` capture for second-source
   corroboration.
5. File the `audit/17` petition.

Every citation, the choice of forum, and the statutory-damages trigger are for
counsel to confirm against current law before any filing.
