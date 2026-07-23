---
title: System Architecture
reference_namespace: V1
status: approved
authority: v1-architecture
owner_repository: AICincy/HCJC
document_family: architecture
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-1
  relation: implements
  to: A-3
- from: V1-4
  relation: implements
  to: A-13
- from: V1-5
  relation: implements
  to: A-21
---

# System Architecture

> **Authority:** Controls the descriptive reference for V1 system boundaries, components, topology, and architectural behavior.

This module records the implemented V1 static-publication architecture. It describes observable repository and runtime behavior without prescribing the successor design.

## V1-1 Static Site and Flat-File Architecture

**Shared concept:** [A-3 Canonical Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-3-canonical-record).

JCStream persists operational and publication state in JSON and media files, renders pages with Jinja2, and serves the resulting HTML and assets without a public application server or relational database. Python modules perform acquisition, transformation, rendering, and verification before GitHub Pages serves the generated tree.

**Implementation and verification references:** `README.md`, `wiki/Architecture.md`, `web/build.py`, `scraper/store.py`.

## V1-2 Repository and Publication Topology

The repository contains authored Python, templates, tests, workflows, operational data under `data/`, and the generated public distribution under `docs/`. The scheduled workflow updates data and generated output on the working branch, after which GitHub Pages serves the `docs/` directory.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `web/build.py`, `docs/`, `data/`.

## V1-3 Major Runtime Components

The principal components are the HCSO client, list and detail parsers, validated Pydantic models, sweep orchestrator, flat-file store, difference engine, photo processor, open-data adapters, correlation modules, ORC classification helpers, view-shaping functions, and static-site builder. Their interfaces are Python functions and files rather than networked internal services.

**Implementation and verification references:** `scraper/client.py`, `scraper/parsers.py`, `scraper/models.py`, `scraper/sweep.py`, `web/build.py`.

## V1-4 GitHub Pages Application Surface

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

The public application consists of generated HTML, CSS, JavaScript, JSON, XML, images, and metadata files in `docs/`. Pages are rooted for the custom domain through build configuration and `docs/CNAME`, while ordinary interaction occurs entirely in the browser.

**Implementation and verification references:** `web/build.py`, `web/templates/`, `web/static/`, `.github/workflows/sweep.yml`, `docs/CNAME`.

## V1-5 Version-Controlled Operational State

**Shared concept:** [A-21 Provenance](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-21-provenance).

Current roster snapshots, recent change events, public feed payloads, reference catalogs, selected evidence ledgers, photos, and generated site output are committed as repository state. Git history therefore records successive publication cycles together with source-code changes.

**Implementation and verification references:** `data/`, `.github/workflows/sweep.yml`, `scraper/store.py`, `docs/`.
