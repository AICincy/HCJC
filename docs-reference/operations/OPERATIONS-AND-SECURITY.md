---
title: Operations and Security
reference_namespace: V1
status: approved
authority: v1-operations
owner_repository: AICincy/HCJC
document_family: operations
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-106
  relation: implements
  to: A-24
- from: V1-98
  relation: implements
  to: A-23
---

# Operations and Security

> **Authority:** Controls the descriptive reference for V1 automation, monitoring, evidence, credentials, deployment, and security practices.

V1 operations are repository-centered. GitHub Actions schedules data acquisition and publication, while Python monitors, evidence verifiers, security scanning, and documented command-line procedures support maintenance and incident response.

## V1-95 Scheduled Sweep Workflow

The `sweep` workflow runs on a fifteen-minute schedule and manual dispatch, uses a concurrency group that queues rather than cancels active runs, installs the pinned runtime dependencies, executes acquisition and feed stages, builds the site, and commits changed data and output.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `scraper/sweep.py`.

## V1-96 Source Freeze Monitoring

After the HCSO sweep, `scraper.freeze_alert` evaluates the age of the last successful roster snapshot. When the configured alarm threshold is exceeded, it emits an Actions error annotation and can open or deduplicate a GitHub issue; it also supports a removal-SLA warning range.

**Implementation and verification references:** `scraper/freeze_alert.py`, `scraper/sweep_guards.py`, `tests/test_freeze_alert.py`.

## V1-97 Deployment Staleness Monitoring

`scraper.deploy_alert` compares the committed roster generation time with the live public `current.json` value. A lag beyond ninety minutes can produce an annotation and deduplicated issue while leaving the data-acquisition workflow available.

**Implementation and verification references:** `scraper/deploy_alert.py`, `.github/workflows/sweep.yml`, `tests/test_deploy_alert.py`.

## V1-98 WAF Access Evidence Ledger

**Shared concept:** [A-23 Retained Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-23-retained-evidence).

The HCSO transport records selected source-access conditions in a hash-linked ledger containing event details and predecessor digest. Verification tooling detects chain inconsistencies, and the transparency view derives public summaries from the ledger.

**Implementation and verification references:** `scraper/client.py`, `scraper/verify_block_log.py`, `data/waf_block_log.json`, `tests/test_client.py`.

## V1-99 PRA Evidence Ledger

**Shared concept:** [A-23 Retained Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-23-retained-evidence).

Public-records-request tooling can prepare and send configured requests and record them in a hash-linked ledger. A dedicated verifier checks predecessor digests independently of the ordinary roster publication process.

**Implementation and verification references:** `scraper/pra.py`, `scraper/pra_log.py`, `scraper/verify_pra_log.py`, `tests/test_pra_log.py`.

## V1-100 Security and Dependency Checks

Continuous integration runs dependency advisory scanning, Ruff, Mypy, Pytest, evidence-chain verification, build smoke tests, and custom-domain checks. A separate CodeQL workflow performs static security analysis.

**Implementation and verification references:** `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `pyproject.toml`.

## V1-101 Optional Proxy and Egress Evidence

The HCSO client accepts an optional `JCSTREAM_HTTP_PROXY` secret for configured egress and can capture runner network information when `JCSTREAM_CAPTURE_EGRESS` is enabled. Egress evidence supports operational diagnosis and public-record access documentation.

**Implementation and verification references:** `scraper/client.py`, `scraper/egress_ip.py`, `.github/workflows/sweep.yml`, `tests/test_egress_ip.py`.

## V1-102 Workflow Permissions and Concurrency

The sweep workflow requests repository-content and issue permissions for its active commit and alert operations and documents permissions not currently needed. Its `jcstream-sweep` concurrency group prevents simultaneous publication cycles.

**Implementation and verification references:** `.github/workflows/sweep.yml`.

## V1-103 Feed Cache Scheduling

Supplemental feed modules use source-specific cache windows, including shorter intervals for Calls for Service and longer intervals for slowly changing feeds. The scheduled workflow can continue other feed and build stages when an individual supplemental adapter fails.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `scraper/cfs.py`, `scraper/shootings.py`, `scraper/open_data_feeds.py`.

## V1-104 Repository Automation Identity and Synchronization

Publication commits use the `jcstream-bot` identity, stage `data/` and `docs/`, fetch the current `main`, prefer rebase, fall back to a merge strategy when required, and push only when staged content changed.

**Implementation and verification references:** `.github/workflows/sweep.yml`.

## V1-105 Operator Command Surface

The repository exposes Python module entry points for sweep, feed retrieval, correlation, build, monitoring, ledger verification, and selected records-request functions. README and wiki operations guidance provide local setup and command examples.

**Implementation and verification references:** `README.md`, `wiki/Operations.md`, `scraper/sweep.py`, `web/build.py`.

## V1-106 Incident, Audit, and Runbook Records

**Shared concept:** [A-24 Supporting Material](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-24-supporting-material).

The `audit/` tree preserves security, parser, data-integrity, accessibility, architecture, legal, WAF, deployment, coverage, and operational-review material. These records support maintenance and historical interpretation without becoming executable runtime configuration.

**Implementation and verification references:** `audit/README.md`, `audit/00_index.md`, `audit/20_audit_runbook_reconcile.md`.
