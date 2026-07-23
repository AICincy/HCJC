---
title: Privacy and Legal
reference_namespace: V1
status: approved
authority: v1-governance
owner_repository: AICincy/HCJC
document_family: governance
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-88
  relation: implements
  to: A-38
- from: V1-89
  relation: implements
  to: A-37
---

# Privacy and Legal

> **Authority:** Controls the descriptive reference for V1 public-records posture, legal language, indexing, photo lifecycle, corrections, and use restrictions.

The public interface combines public-record access with recurring legal and privacy framing. This module records the implemented notices, publication boundaries, removal behaviors, and reporting channels.

## V1-83 Public Records and Independent Status

V1 describes itself as an independent, non-governmental mirror of records published by governmental sources and cites the Ohio Public Records Act as part of its public-records context. It does not represent itself as an official jail, sheriff, county, city, or court system.

**Implementation and verification references:** `README.md`, `wiki/Legal.md`, `web/templates/base.html`, `web/templates/data.html`.

## V1-84 Presumption of Innocence

Page metadata, footer language, individual-page context, and legal documentation state that arrest and charges are accusations rather than convictions or proof of guilt.

**Implementation and verification references:** `web/templates/base.html`, `web/templates/inmate.html`, `wiki/Legal.md`, `tests/test_cra_boundary.py`.

## V1-85 Consumer Reporting Restriction

The footer and legal documentation state that JCStream is not a consumer reporting agency and prohibit use for employment, housing, credit, insurance, tenant screening, and other FCRA-governed eligibility purposes.

**Implementation and verification references:** `web/templates/base.html`, `web/templates/data.html`, `wiki/Legal.md`, `tests/test_cra_boundary.py`.

## V1-86 No-Index and No-Archive Controls

Generated pages include `noindex, noarchive` metadata. The implemented intent is to reduce ordinary search-engine indexing and cached copies of individual custody records within a current-mirror publication model.

**Implementation and verification references:** `web/templates/base.html`, `web/build.py`, `tests/test_outputs.py`.

## V1-87 Generic Social Metadata

Open Graph and Twitter metadata are site-level and generic rather than person-specific. Individual routes therefore inherit project framing instead of generating a social card centered on a person name or booking photo.

**Implementation and verification references:** `web/templates/base.html`, `tests/test_build.py`.

## V1-88 Current Photo Removal

**Shared concept:** [A-38 Removal](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-38-removal).

When an accepted roster update no longer contains an inmate number, sweep photo reconciliation removes the corresponding current photo file, with a safety guard for unexpectedly large deletion sets. The next public build reflects the reconciled current photo collection.

**Implementation and verification references:** `scraper/sweep.py`, `scraper/sweep_guards.py`, `scraper/photos.py`, `tests/test_photos.py`.

## V1-89 Correction and Removal Assistance

**Shared concept:** [A-37 Correction](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-37-correction).

Public legal, data, visit, and help content directs users to no-fee correction, sealing, expungement, removal, privacy, and project-reporting routes. Repository issue forms and security guidance provide structured contact paths.

**Implementation and verification references:** `wiki/Legal.md`, `web/templates/data.html`, `web/templates/help.html`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `SECURITY.md`.

## V1-90 Source Attribution and Limitations

**Shared concept:** [A-21 Provenance](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-21-provenance).

Public pages identify HCSO and supplemental source agencies, display generation context, and link methodology. Copy explains that upstream records can change and that JCStream mirrors what its sources make available.

**Implementation and verification references:** `web/templates/base.html`, `web/templates/data.html`, `README.md`.

## V1-91 Public-Use and Licensing Notices

The footer distinguishes the MIT-licensed source code, the project-arranged record-data license, and the legal status of underlying public records. These notices accompany the non-affiliation and use-restriction statements.

**Implementation and verification references:** `web/templates/base.html`, `LICENSE`, `README.md`.

## V1-92 Security and Privacy Reporting

`SECURITY.md` and generated `security.txt` provide routes for privately reporting security or privacy issues. Public issue channels remain available for ordinary defects and corrections that do not disclose sensitive vulnerability details.

**Implementation and verification references:** `SECURITY.md`, `web/build.py`, `.github/ISSUE_TEMPLATE/bug_report.yml`.

## V1-93 Commentary and Case-Data Contributions

The individual-page template can expose configured GitHub-backed commentary, while a structured issue form collects proposed case information for reviewed ingestion. Both mechanisms remain separate from the official source record fields.

**Implementation and verification references:** `web/templates/inmate.html`, `.github/ISSUE_TEMPLATE/case-data.yml`, `scraper/ingest_issue.py`, `tests/test_ingest_issue.py`.

## V1-94 Identity Retention and Anonymization

**Shared concept:** [A-38 Removal](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-38-removal).

The current roster and recent identified changelog support current-publication and recent-activity functions. Long-term activity routines remove selected identifying information after the configured window while aggregate history remains non-identifying.

**Implementation and verification references:** `scraper/store.py`, `web/build.py`, `wiki/Legal.md`, `tests/test_store.py`.
