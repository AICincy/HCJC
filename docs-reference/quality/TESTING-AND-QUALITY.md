---
title: Testing and Quality
reference_namespace: V1
status: approved
authority: v1-quality
owner_repository: AICincy/HCJC
document_family: quality
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-107
  relation: implements
  to: A-44
- from: V1-111
  relation: implements
  to: A-45
---

# Testing and Quality

> **Authority:** Controls the descriptive reference for V1 tests, CI checks, type checking, linting, security analysis, and build verification.

V1 combines offline unit and integration tests with linting, type checking, dependency review, static analysis, build verification, and evidence-chain checks. The repository test organization mirrors acquisition, transformation, presentation, operations, and policy behavior.

## V1-107 Pytest Verification Suite

**Shared concept:** [A-44 Verification Procedure](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-44-verification-procedure).

Pytest modules cover models, transport, parsers, sweep behavior, storage, photos, feeds, correlations, taxonomy, court integration, view shaping, static output, alerts, evidence logs, accessibility-related output, policy boundaries, and integration smoke behavior.

**Implementation and verification references:** `pyproject.toml`, `tests/`, `audit/_pytest_baseline.txt`.

## V1-108 Ruff Linting

Ruff enforces selected pycodestyle, Pyflakes, import sorting, and bugbear rules for Python 3.13, with the repository line-length and excluded-rule policy recorded in `pyproject.toml`. CI runs `ruff check .`.

**Implementation and verification references:** `pyproject.toml`, `.github/workflows/ci.yml`.

## V1-109 Mypy Type Checking

Mypy uses Python 3.13 semantics, checks untyped function bodies, enforces explicit package bases, and ignores missing third-party stubs for declared modules. CI explicitly checks the `scraper` and `web` packages.

**Implementation and verification references:** `pyproject.toml`, `.github/workflows/ci.yml`.

## V1-110 Empty-Data Build Smoke Test

CI executes the static builder with the production root-relative base setting after tests. The builder supplies empty bootstrap models and pages so deployment structure can be verified even without current runtime data.

**Implementation and verification references:** `.github/workflows/ci.yml`, `web/build.py`, `tests/test_build.py`.

## V1-111 Evidence Chain Verification

**Shared concept:** [A-45 Evidence Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-45-evidence-record).

CI invokes both WAF and PRA ledger verification modules. Each verifier exits unsuccessfully when predecessor hashes do not form the expected chain, making integrity verification an automated quality gate.

**Implementation and verification references:** `.github/workflows/ci.yml`, `scraper/verify_block_log.py`, `scraper/verify_pra_log.py`, `tests/test_pra_log.py`.

## V1-112 Custom Domain Verification

CI builds with `JCSTREAM_CNAME=www.aretheyinjail.com`, verifies that `docs/CNAME` exists, and checks that its content names the expected domain. This protects the branch-based GitHub Pages configuration from build regressions.

**Implementation and verification references:** `.github/workflows/ci.yml`, `web/build.py`, `tests/test_build.py`.

## V1-113 Architecture, Data, Security, and Policy Tests

Specialized tests validate repository conventions, public data-page schemas, output contracts, consumer-reporting boundaries, dependency-safe DOM behavior, court and bond analysis, and integration behavior in addition to conventional unit tests.

**Implementation and verification references:** `tests/test_architectural_compliance.py`, `tests/test_data_page_schema.py`, `tests/test_outputs.py`, `tests/test_cra_boundary.py`, `tests/test_integration_smoke.py`.

## V1-114 Accessibility, Visual, and Content Review Records

**Shared concept:** [A-24 Supporting Material](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-24-supporting-material).

Repository audits document HTML accessibility, stylesheet contrast and performance, UI structure, content governance, and design handoffs. These review records supplement executable tests with human analysis of public presentation.

**Implementation and verification references:** `audit/07_html_accessibility.md`, `audit/09_content_governance.md`, `audit/10_css_a11y_performance.md`, `audit/11_spa_structural_audit.md`.
