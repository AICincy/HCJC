# A0 work cards: public-only HCJC audit wave

**Frozen source baseline:** `fbe33ca9af7db6e08ab4a6f16515ece26085b241`  
**Evidence register:** This directory.  
**Common boundary:** No private configuration, secret values, mail, deployment, source modification, person-linked official-source comparison, external contact, or raw person-level data in artifacts.

## A1: Deployment and freshness

| Field | Assignment |
|---|---|
| Claim ID | A1-DEPLOY-FRESH-001 |
| Neutral proposition | Across three recent completed scheduled cycles, public sweep, commit, Pages, and published snapshot timestamps identify the measured deployment-freshness interval. |
| Allowed evidence | Public GitHub repository and Actions pages/API, public `aretheyinjail.com` pages and published aggregate metadata, source workflow configuration at the frozen SHA. |
| Forbidden conclusion | Workflow success proves roster accuracy, a public API 404 proves Pages is disabled, or a timestamp alone proves an upstream defect. |
| Acceptance criteria | Three sequence rows or a documented source limitation; UTC timestamps, retrieval route, source locator, deltas, cache qualification, and evidence grade. |
| Falsifier | A current public artifact or deployment event contradicts the proposed sequence. |
| Stop condition | Report is written to `A1-deployment-and-freshness-report.md`, contains no raw roster data, and identifies any remaining unknown. |

## A2: Source and CI reproducibility

| Field | Assignment |
|---|---|
| Claim ID | A2-CI-REPRO-001 |
| Neutral proposition | The declared source dependencies, CI pins, and checks can be reproduced in a separate isolated environment, and discrepancies are classified accurately. |
| Allowed evidence | Detached A2 worktree, project manifests, CI workflow files, documented supported Python versions, isolated virtual environment, and commands derived from the repository. |
| Forbidden conclusion | A local tool absence proves a source defect, one host result proves production health, or a passing lint result proves live deployment correctness. |
| Acceptance criteria | Environment identity, exact commands, exit results, tool/dependency matrix, working-tree status before and after, and explicit failure classification. |
| Falsifier | A clean isolated reproduction on the stated environment produces a materially different result. |
| Stop condition | Report is written to `A2-ci-reproducibility-report.md`, no source changes exist in the active checkout, and unsupported Python versions are marked unavailable rather than inferred. |

## A3: Documentation and provenance

| Field | Assignment |
|---|---|
| Claim ID | A3-PROVENANCE-001 |
| Neutral proposition | The supplied status report and remediation plan distinguish source-supported findings from documentation-only claims and unsupported legal or operational assertions. |
| Allowed evidence | Supplied text files, frozen source, public repository and issue evidence, public live-site evidence, and primary official sources when a proposition requires them. |
| Forbidden conclusion | Source silence proves fabrication, an issue recommendation proves a factual conclusion, or a legal proposition is current without primary-law verification. |
| Acceptance criteria | Atomic claim rows, one claim-source status each, stable source locators, exact searched scope, source hierarchy, and explicit unresolved claims. |
| Falsifier | A higher-authority source materially conflicts with the report's classification. |
| Stop condition | Report is written to `A3-provenance-and-documentation-report.md`, with no raw personal data and no external action. |

## A4: Evidence chain and resilience

| Field | Assignment |
|---|---|
| Claim ID | A4-EVIDENCE-RESILIENCE-001 |
| Neutral proposition | The local WAF and PRA evidence-chain verifiers and malformed-takedown failure path exhibit the documented behavior in a dependency-complete disposable environment with synthetic fixtures. |
| Allowed evidence | Detached A4 worktree, existing local non-identifying aggregate records, source verifier code, an isolated virtual environment, and synthetic malformed fixtures created outside tracked source paths. |
| Forbidden conclusion | A valid chain proves WAF effectiveness or live production health, an isolated fixture proves live resilience, or local evidence permits person-level reporting. |
| Acceptance criteria | Exact verifier results, aggregate-only summary, synthetic corruption/failure matrix, preservation result, environment identity, and post-run working-tree status. |
| Falsifier | The verifier or controlled fixture result differs from the expected source-defined behavior. |
| Stop condition | Report is written to `A4-evidence-chain-and-resilience-report.md`; temporary data is outside tracked source paths and private gates remain untouched. |
