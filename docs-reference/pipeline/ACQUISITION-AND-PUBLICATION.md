---
title: Acquisition and Publication
reference_namespace: V1
status: approved
authority: v1-pipeline
owner_repository: AICincy/HCJC
document_family: pipeline
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-25
  relation: implements
  to: A-1
- from: V1-32
  relation: implements
  to: A-15
- from: V1-38
  relation: implements
  to: A-16
- from: V1-40
  relation: implements
  to: A-13
---

# Acquisition and Publication

> **Authority:** Controls the descriptive reference for V1 acquisition, validation, persistence, building, repository publication, and GitHub Pages delivery.

The V1 pipeline is an automated extract, validate, compare, persist, render, and commit process. Source-specific guards and atomic file operations support continuity between successful publication cycles.

## V1-25 Alphabetic Surname Sweep

**Shared concept:** [A-1 Source System](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-1-source-system).

The HCSO list acquisition iterates configured surname substrings, ordinarily the letters A through Z, because the source search form does not expose a single view-all operation. Results are deduplicated by source inmate identifier before detail processing.

**Implementation and verification references:** `scraper/sweep.py`, `data/surnames.txt`, `tests/test_sweep.py`.

## V1-26 List and Detail Acquisition

**Shared concept:** [A-2 Source Observation](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-2-source-observation).

List pages provide summary rows and detail-page locations; detail pages provide custody, charge, case, bond, disposition, and photo fields. The sweep fetches list results first, determines which records need detail refresh, then parses detail pages into validated models.

**Implementation and verification references:** `scraper/sweep.py`, `scraper/client.py`, `scraper/parsers.py`, `tests/test_parsers.py`.

## V1-27 Concurrency and Crawl Delay

The HCSO client and sweep use bounded parallel detail retrieval together with a configured request delay. Shared transport coordination applies retry and backoff behavior while retaining a project-specific user agent and optional proxy support.

**Implementation and verification references:** `scraper/client.py`, `scraper/sweep.py`, `tests/test_client.py`, `tests/test_sweep.py`.

## V1-28 Source Health Evaluation

**Shared concept:** [A-18 Source Status](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-18-source-status).

Before normal persistence and photo reconciliation, sweep guards evaluate query failures, candidate roster volume, parsing quality, runtime limits, and potentially destructive photo cleanup. Guard outcomes determine whether candidate state is accepted, degraded, or retained only for diagnosis.

**Implementation and verification references:** `scraper/sweep.py`, `scraper/sweep_guards.py`, `tests/test_sweep.py`.

## V1-29 Atomic File Persistence

JSON writes use temporary files and filesystem replacement so readers observe either the prior complete file or the replacement complete file. The store validates core snapshot structure before serializing current state.

**Implementation and verification references:** `scraper/store.py`, `tests/test_store.py`.

## V1-30 Booking, Release, and Update Diffing

**Shared concept:** [A-10 Material Change Event](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-10-material-change-event).

The difference engine compares previous and candidate snapshots by source inmate number and material record content. It emits booking records for new identifiers, release records for removed identifiers, and update records for materially changed continuing records.

**Implementation and verification references:** `scraper/diff.py`, `scraper/store.py`, `tests/test_store.py`.

## V1-31 Static Site Build

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

`web.build` loads current state and supplemental inputs, prepares template helpers and shaped view models, renders routes and feeds, copies static assets and photos, and writes public JSON, metadata, and checksums. The build can render an empty-data state for deployment verification.

**Implementation and verification references:** `web/build.py`, `web/shape/`, `web/templates/`, `tests/test_build.py`.

## V1-32 Repository Commit and GitHub Pages Publication

**Shared concept:** [A-15 Approved Release](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-15-approved-release).

The scheduled workflow stages `data/` and `docs/`, commits substantive changes with the automation identity, synchronizes with `main`, and pushes. GitHub Pages serves the generated `docs/` directory from the branch configuration.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `docs/CNAME`, `README.md`.

## V1-33 Freshness Gate and Scheduled Cadence

The workflow is triggered every fifteen minutes on a best-effort scheduler. Sweep logic can skip acquisition when the current snapshot remains within its configured freshness interval, preventing unnecessary immediate repeat retrieval.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `scraper/sweep.py`, `tests/test_sweep.py`.

## V1-34 Known-Record Refresh and Detail Reuse

Routine sweeps can reuse sufficiently current known detail data while new or stale records receive detail requests. The command-line `--refresh-known` option requests a complete known-record detail refresh for operations or verification.

**Implementation and verification references:** `scraper/sweep.py`, `tests/test_sweep.py`, `README.md`.

## V1-35 Photo Processing and Reconciliation

Detail acquisition passes embedded image content to the photo processor for validation, resizing, and JPEG normalization. At the end of an accepted sweep, current identifiers determine the eligible photo set, with a guard against unexpectedly large deletion.

**Implementation and verification references:** `scraper/photos.py`, `scraper/sweep.py`, `scraper/sweep_guards.py`, `tests/test_photos.py`.

## V1-36 Supplemental Feed Acquisition

**Shared concept:** [A-1 Source System](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-1-source-system).

Dedicated and registry-driven adapters retrieve Cincinnati Open Data feeds using dataset-specific windows, selected fields, ordering, limits, and cache intervals. Each adapter can skip a network request when its existing output remains fresh.

**Implementation and verification references:** `scraper/cincy_open.py`, `scraper/cfs.py`, `scraper/cfs_pdi.py`, `scraper/shootings.py`, `scraper/open_data_feeds.py`.

## V1-37 Correlation Build Stage

**Shared concept:** [A-25 Correlation](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-25-correlation).

After roster and supplemental feed acquisition, the workflow invokes the research correlation module before the static site build. Public candidate matching is also performed in the presentation-building path for individual custody pages.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `scraper/correlate.py`, `scraper/match.py`, `web/build.py`.

## V1-38 Current and Last-Good Persistence Behavior

**Shared concept:** [A-16 Last-Known-Good Release](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-16-last-known-good-release).

Health guards preserve the preceding roster when acquisition conditions indicate a degraded candidate. The current snapshot therefore acts as the project publication baseline until an accepted sweep writes a replacement.

**Implementation and verification references:** `scraper/sweep.py`, `scraper/sweep_guards.py`, `scraper/store.py`, `tests/test_sweep.py`.

## V1-39 Root-Relative Custom-Domain Build

Production sets an empty site base URL so internal links are root-relative for `www.aretheyinjail.com`. The configured site URL supplies absolute origins for RSS and metadata, and `JCSTREAM_CNAME` causes the build to write the custom-domain file.

**Implementation and verification references:** `.github/workflows/sweep.yml`, `web/build.py`, `tests/test_build.py`.

## V1-40 Generated Public Output Tree

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

The build recreates the public distribution as route directories, data files, feeds, static resources, photos, checksums, and policy metadata beneath `docs/`. This tree is the deployable application artifact served by GitHub Pages.

**Implementation and verification references:** `web/build.py`, `docs/`, `tests/test_outputs.py`.
