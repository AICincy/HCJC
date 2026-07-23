---
title: V1 Legacy Document Mapping
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
relationships: []
---

# V1 Legacy Document Mapping

> **Authority:** Controls the staged mapping from pre-structure V1 documentation into the controlled V1 reference and preserved supporting material.

This ledger prevents silent loss during documentation restructuring. A `migrated` entry means substantive current descriptions were incorporated into controlled modules; `preserved-supporting` means the source remains useful as non-authoritative analysis or history; `source-reference` means the file is cited as implementation evidence; `excluded-generated` identifies runtime or generated material that was intentionally not copied into controlled documentation.

## Migration state definitions

| State | Meaning |
|---|---|
| Inventoried | File or section identified |
| Classified | Authority and purpose identified |
| Mapped | Controlled destination selected |
| Migrated | Substantive content incorporated |
| Verified | Destination checked against source or implementation |
| Archived | Original preserved with historical status |
| Retired | Original no longer serves as current guidance |

## Root documentation mapping

| Legacy source | Substantive subject | Classification | Destination | Action | State |
|---|---|---|---|---|---|
| `README.md` | Purpose, architecture, acquisition, data, legal posture, UI, operations, tests | Mixed descriptive orientation | `V1-1` through `V1-120` across controlled modules | Consolidated and rewritten as concise orientation | Verified |
| `CLAUDE.md` | Contributor commands, repository rules, implementation conventions | Contributor guidance | `V1-8`, `V1-105`, supporting history | Preserved in place and cited where applicable | Mapped |
| `SECURITY.md` | Security and privacy reporting | Operational policy | `V1-92` | Migrated; original retained | Verified |
| `_headers` | Reference security-header policy | Implementation evidence | `V1-100` | Retained as source reference | Verified |
| `pyproject.toml` | Runtime, dependencies, test, Ruff, Mypy configuration | Implementation evidence | `V1-3`, `V1-107` to `V1-109` | Retained as source reference | Verified |

## Wiki mapping

| Legacy source | Substantive subject | Destination | Action | State |
|---|---|---|---|---|
| `wiki/Architecture.md` | Repository documentation and subject sections | V1-1 through V1-5 | Migrated or consolidated; original retained | Verified |
| `wiki/Contributing.md` | Repository documentation and subject sections | V1-8, V1-92, V1-105 | Migrated or consolidated; original retained | Verified |
| `wiki/Data.md` | Repository documentation and subject sections | V1-11 through V1-24 | Migrated or consolidated; original retained | Verified |
| `wiki/Home.md` | Repository documentation and subject sections | V1-6 through V1-10 | Migrated or consolidated; original retained | Verified |
| `wiki/Legal.md` | Repository documentation and subject sections | V1-83 through V1-94 | Migrated or consolidated; original retained | Verified |
| `wiki/Operations.md` | Repository documentation and subject sections | V1-25 through V1-40 and V1-95 through V1-106 | Migrated or consolidated; original retained | Verified |
| `wiki/README.md` | Repository documentation and subject sections | V1-7 and V1-9 | Migrated or consolidated; original retained | Verified |
| `wiki/Roadmap.md` | Repository documentation and subject sections | Supporting historical material | Preserved as `docs-reference/supporting/historical/ROADMAP.md` | Verified |
| `wiki/_Sidebar.md` | Repository documentation and subject sections | README and controlled-module navigation | Migrated or consolidated; original retained | Verified |

## Audit mapping

All Markdown files directly beneath `audit/` were inventoried as non-authoritative review, research, legal, incident, or historical material and copied to `docs-reference/supporting/audits/`. Their implementation findings were used to verify applicable controlled modules, but the audit copies do not define current V1 behavior independently.

| Legacy group | Classification | Destination | Action | State |
|---|---|---|---|---|
| `audit/*.md` | Supporting audits and research | `docs-reference/supporting/audits/` | Copied without deleting originals | Verified |
| `audit/sessions/README.md` | Historical session-export guidance | `docs-reference/supporting/historical/sessions/README.md` | Copied | Verified |
| `audit/sessions/EXPORT-CHECKLIST.md` | Historical export procedure | `docs-reference/supporting/historical/sessions/EXPORT-CHECKLIST.md` | Copied | Verified |
| `audit/sessions/*.jsonl` | Potentially sensitive session transcripts | None | Intentionally excluded from controlled documentation copies | Verified |
| `audit/_commit.txt` | Baseline commit evidence | `docs-reference/supporting/evidence/_commit.txt` | Copied | Verified |
| `audit/_pytest_baseline.txt` | Baseline test evidence | `docs-reference/supporting/evidence/_pytest_baseline.txt` | Copied | Verified |

## GitHub workflow and issue-form mapping

| Source | Subject | Destination | Action | State |
|---|---|---|---|---|
| `.github/workflows/sweep.yml` | Scheduled acquisition, build, commit, monitoring | `V1-25` to `V1-40`, `V1-95` to `V1-104` | Retained as implementation evidence | Verified |
| `.github/workflows/ci.yml` | Test, lint, type, dependency, ledger, build, domain checks | `V1-100`, `V1-107` to `V1-112` | Retained as implementation evidence | Verified |
| `.github/workflows/codeql.yml` | Static security analysis | `V1-100` | Retained as implementation evidence | Verified |
| `.github/workflows/ingest_case_data.yml` | Reviewed case-data ingestion | `V1-93` | Retained as implementation evidence | Verified |
| `.github/workflows/pra_daily.yml` | Records-request operations | `V1-99` | Retained as implementation evidence | Verified |
| `.github/workflows/refresh_caselaw.yml` | Case-law reference refresh | `V1-20`, `V1-64` | Retained as implementation evidence | Verified |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Defect and correction intake | `V1-89` | Retained as implementation evidence | Verified |
| `.github/ISSUE_TEMPLATE/case-data.yml` | Case-data contribution | `V1-93` | Retained as implementation evidence | Verified |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Historical enhancement intake | Supporting history | Retained in place | Verified |
| `.github/ISSUE_TEMPLATE/waf-block.yml` | Source-access incident intake | `V1-98`, `V1-106` | Retained as implementation evidence | Verified |

## Runtime and generated material exclusions

| Source group | Classification | Action | Rationale |
|---|---|---|---|
| `data/*.json` | Runtime and reference state | Not copied | Cited in controlled modules; remains repository implementation evidence |
| `data/photos/` | Active media state | Not copied | Avoids duplicating identity-bearing media |
| `docs/` | Generated public distribution | Not copied or modified | V1 GitHub Pages application output |
| `__pycache__/`, local caches | Generated local state | Not copied | No documentation authority |
| session JSONL | Potentially sensitive historical data | Not copied | Minimize unnecessary duplication |

## Verification statement

The controlled V1 entries were reviewed against the imported repository snapshot, primary implementation files, workflows, tests, and preserved legacy documentation. Originals remain available in place or under the supporting historical boundary.
