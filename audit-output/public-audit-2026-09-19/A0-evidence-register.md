# A0 evidence register: public-only HCJC audit wave

**Frozen baseline:** `fbe33ca9af7db6e08ab4a6f16515ece26085b241`  
**Scope:** A0 through A4. Private-state and official-source comparison gates remain deferred.  
**Report status rule:** A report is provisional until later independent adversarial review. No row below is a technical verdict until its listed evidence arrives.

| Claim ID | Owner | Neutral question | Evidence threshold | Current state | Required artifact |
|---|---|---|---|---|---|
| A1-DEPLOY-FRESH-001 | A1 | Do three completed public cycles reveal the measured interval from sweep to visible snapshot? | Three timestamped public sequences or a documented source limit. | Submitted. Response-gate checked by A0. Awaiting later AQ review. | `A1-deployment-and-freshness-report.md` |
| A2-CI-REPRO-001 | A2 | Can declared CI behavior and dependency relationships be reproduced in an isolated environment? | Exact environment, command, exit result, and failure classification for every check attempted. | Submitted. Response-gate checked by A0. Awaiting later AQ review. | `A2-ci-reproducibility-report.md` |
| A3-PROVENANCE-001 | A3 | Which material status-report and remediation-plan claims are supported, contradicted, not found, or require manual review? | One permitted claim-source status and stable locator for every scoped atomic claim. | Submitted. Response-gate checked by A0. Awaiting later AQ review. | `A3-provenance-and-documentation-report.md` |
| A4-EVIDENCE-RESILIENCE-001 | A4 | Do evidence-chain verifiers and synthetic malformed-takedown fixtures demonstrate the documented behavior? | Isolated verifier results, aggregate-only summary, synthetic fixture matrix, and post-run status. | Submitted. Response-gate checked by A0. Awaiting later AQ review. | `A4-evidence-chain-and-resilience-report.md` |

## Intake rules

1. A report must name this SHA, its observation window, source or environment identity, and every blocked or excluded route.
2. A positive factual claim requires a stable locator, command result, or direct public observation. Prior reports and source comments are not enough.
3. Static source, isolated execution, public deployment, and private configuration remain separate evidence categories.
4. Source silence becomes `not found in searched sources`, not `conflicting` or fabrication.
5. A report with person-level data, secret material, unexplained retries, missing failure classification, or a scope breach is returned for repair.
