---
title: Migration and Traceability
reference_namespace: V1
status: approved
authority: v1-migration
owner_repository: AICincy/HCJC
document_family: migration
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-116
  relation: maps-to
  to: V2-121
- from: V1-118
  relation: implements
  to: A-43
- from: V1-119
  relation: implements
  to: A-46
- from: V1-120
  relation: implements
  to: A-45
---

# Migration and Traceability

> **Authority:** Controls V1 preservation, implementation inventory, mappings to shared concepts and V2, and pinned historical interpretation.

This module records how the V1 documentation snapshot is preserved and related to the HCJC2 canonical reference and successor requirements. It does not authorize V1 runtime changes or imply that V2 capabilities are present in V1.

## V1-115 V1 Preservation Scope

**Shared concept:** [A-24 Supporting Material](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-24-supporting-material).

The V1 reference preserves implemented architecture, data products, acquisition behavior, correlations, taxonomy, UI/UX, legal controls, operations, tests, workflows, and supporting history. Runtime data and generated public output remain implementation evidence rather than controlled documentation copies.

**Implementation and verification references:** `docs-reference/`, `README.md`, `scraper/`, `web/`, `.github/workflows/`, `tests/`.

## V1-116 V1-to-V2 Behavioral Mapping

**Shared concept:** [A-46 Accepted Difference](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-46-accepted-difference).

The current traceability program maps V1 behaviors to V2 requirements using explicit relationships such as preserves, refines, replaces, maps-to, and accepted-difference-from. The mapping does not presume equivalence merely because two entries concern the same subject.

**Implementation and verification references:** `docs-reference/reference/TRACEABILITY-MATRIX-SNAPSHOT.md`, `docs-reference/migration/LEGACY-DOCUMENT-MAPPING.md`, `docs-reference/MASTER-SPEC.md`.

## V1-117 Reviewed V1 Commit

The documentation snapshot records the exact V1 commit used to verify descriptions, source paths, test paths, and legacy mappings. Subsequent V1 changes require a new review record or an explicitly scoped documentation update.

**Implementation and verification references:** `docs-reference/reference/canonical-lock.json`, `git history`, `docs-reference/supporting/evidence/`.

## V1-118 Pinned Canonical Reference

**Shared concept:** [A-43 Supersession](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-43-supersession).

V1 interpretation is pinned to a semantic HCJC2 canonical-reference release and commit. Links to a current edition may be provided for convenience, but the pinned edition controls historical meaning for this V1 snapshot.

**Implementation and verification references:** `docs-reference/reference/canonical-lock.json`, `docs-reference/MASTER-SPEC.md`.

## V1-119 Accepted Differences

**Shared concept:** [A-46 Accepted Difference](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-46-accepted-difference).

An accepted difference records a reviewed and intentional divergence between implemented V1 behavior and a V2 requirement. Differences must identify both references and the reason the successor preserves, refines, replaces, or omits the V1 behavior.

**Implementation and verification references:** `docs-reference/migration/MIGRATION-AND-TRACEABILITY.md`, `docs-reference/reference/TRACEABILITY-MATRIX-SNAPSHOT.md`.

## V1-120 V1 Traceability Snapshot

**Shared concept:** [A-45 Evidence Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-45-evidence-record).

The generated V1 snapshot captures cross-version relationships against the pinned canonical release and records generation metadata, reviewed commits, and generator version. It is historical evidence and does not replace the current HCJC2 matrix.

**Implementation and verification references:** `docs-reference/reference/TRACEABILITY-MATRIX-SNAPSHOT.md`, `docs-reference/reference/canonical-lock.json`.

## Release evidence

The cross-version release review is recorded in [E-1 Cross-Version Documentation Release Review](https://github.com/AICincy/HCJC2/blob/main/docs/quality/RELEASE-EVIDENCE.md#e-1-cross-version-documentation-release-review).
