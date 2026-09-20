---
title: JCStream V1 Master Specification
reference_namespace: V1
status: approved
authority: v1-master
owner_repository: AICincy/HCJC
document_family: master
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-7
  relation: implements
  to: A-42
---

# JCStream V1 Master Specification

> **Authority:** Approved controlling entry point for implemented JCStream V1 behavior, reference ownership, preservation, and cross-version interpretation.

JCStream V1 is the implemented static public-records system maintained in `AICincy/HCJC`. This master specification identifies the V1 documentation authority, preserves the boundary between implemented behavior and successor requirements, and directs readers to the detailed controlled modules.

## V1-6 System Identity and Public Purpose

**Shared concept:** [A-1 Source System](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-1-source-system).

JCStream transforms public Hamilton County Justice Center roster material and selected public contextual datasets into a searchable static site and machine-readable publication. The system presents source-reported custody information with source attribution, legal context, and public-use limitations.

**Implementation and verification references:** `README.md`, `web/templates/base.html`, `web/templates/data.html`.

## V1-7 Descriptive Documentation Authority

**Shared concept:** [A-42 Controlled Document](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-42-controlled-document).

The V1 controlled documents describe behavior evidenced by the repository snapshot. They do not create new runtime requirements and do not represent planned HCJC2 behavior as an existing V1 capability.

**Implementation and verification references:** `docs-reference/MASTER-SPEC.md`, `README.md`, `wiki/Architecture.md`.

## V1-8 Implemented Behavior Boundary

**Shared concept:** [A-44 Verification Procedure](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-44-verification-procedure).

A statement is treated as implemented V1 behavior when it is supported by source code, workflow configuration, generated-contract logic, tests, or retained operational documentation in the reviewed repository snapshot. Proposed enhancements remain outside this authority unless they were merged into the implementation.

**Implementation and verification references:** `scraper/`, `web/`, `tests/`, `.github/workflows/`.

## V1-9 Preservation and Historical Use

**Shared concept:** [A-24 Supporting Material](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-24-supporting-material).

The V1 documentation set preserves system topology, public interfaces, data products, operational controls, design choices, legal language, tests, and historical context for maintenance and migration comparison. Legacy documents remain discoverable through the mapping ledger and supporting-history directories.

**Implementation and verification references:** `docs-reference/migration/LEGACY-DOCUMENT-MAPPING.md`, `docs-reference/supporting/historical/`, `audit/`.

## V1-10 Module Ownership and Canonical Pinning

**Shared concept:** [A-43 Supersession](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-43-supersession).

Each detailed subject is controlled by one of ten V1 modules. Shared cross-version terms are interpreted against the pinned HCJC2 canonical-reference release recorded in this document and the V1 traceability snapshot.

**Implementation and verification references:** `docs-reference/reference/canonical-lock.json`, `docs-reference/reference/TRACEABILITY-MATRIX-SNAPSHOT.md`, `docs-reference/migration/MIGRATION-AND-TRACEABILITY.md`.

## Controlled modules

1. [System Architecture](architecture/SYSTEM-ARCHITECTURE.md)
2. [Data and Schemas](data/DATA-AND-SCHEMAS.md)
3. [Acquisition and Publication](pipeline/ACQUISITION-AND-PUBLICATION.md)
4. [Correlations](correlations/CORRELATIONS.md)
5. [Offense Taxonomy](taxonomy/OFFENSE-TAXONOMY.md)
6. [Product and UI/UX](product/PRODUCT-AND-UI-UX.md)
7. [Privacy and Legal](governance/PRIVACY-AND-LEGAL.md)
8. [Operations and Security](operations/OPERATIONS-AND-SECURITY.md)
9. [Testing and Quality](quality/TESTING-AND-QUALITY.md)
10. [Migration and Traceability](migration/MIGRATION-AND-TRACEABILITY.md)
