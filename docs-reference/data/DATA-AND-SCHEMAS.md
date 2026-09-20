---
title: Data and Schemas
reference_namespace: V1
status: approved
authority: v1-data
owner_repository: AICincy/HCJC
document_family: data
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-11
  relation: implements
  to: A-11
- from: V1-11
  relation: implements
  to: A-4
- from: V1-12
  relation: implements
  to: A-5
- from: V1-12
  relation: implements
  to: A-6
- from: V1-13
  relation: implements
  to: A-10
- from: V1-13
  relation: implements
  to: A-8
- from: V1-13
  relation: implements
  to: A-9
- from: V1-16
  relation: implements
  to: A-2
- from: V1-19
  relation: implements
  to: A-18
- from: V1-24
  relation: implements
  to: A-17
---

# Data and Schemas

> **Authority:** Controls the descriptive reference for V1 entities, fields, identifiers, artifacts, serialization, and retention behavior.

V1 uses Pydantic models for central custody records and JSON conventions for roster, activity, feed, reference, evidence, and generated indexes. Source text is generally retained in the string forms supplied by upstream systems.

## V1-11 Current Roster Snapshot

**Shared concept:** [A-4 Current Roster](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-4-current-roster).

`data/current.json` is the current project snapshot. Its `Snapshot` model includes `schema_version`, `generated_utc`, `inmate_count`, and an `inmates` collection; model validation enforces count consistency and unique inmate numbers.

**Implementation and verification references:** `scraper/models.py`, `scraper/store.py`, `tests/test_models.py`, `tests/test_store.py`.

## V1-12 Inmate and Charge Models

**Shared concept:** [A-6 Custody Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-6-custody-record).

The `Inmate` model records source identifiers, name components, demographic source fields, custody dates, holder status, charges, photo filename, and observation timestamps. Each nested `Charge` can carry court cases, court date, ORC code, description, bond information, disposition, and comments.

**Implementation and verification references:** `scraper/models.py`, `tests/test_models.py`, `tests/test_parsers.py`.

## V1-13 Change Events

**Shared concept:** [A-10 Material Change Event](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-10-material-change-event).

The `ChangeEvent` model represents `booked`, `released`, and `updated` observations with source inmate number, display name, UTC timestamp, and note. The difference engine constructs these events by comparing successive snapshots.

**Implementation and verification references:** `scraper/models.py`, `scraper/diff.py`, `tests/test_store.py`.

## V1-14 Anonymized Activity History

**Shared concept:** [A-23 Retained Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-23-retained-evidence).

The build and store routines maintain long-term activity records in an anonymized form after the configured identifying window. Retained entries preserve analytical dimensions such as event date, event type, primary category, and severity tier while removing selected direct identity fields.

**Implementation and verification references:** `scraper/store.py`, `web/build.py`, `tests/test_store.py`.

## V1-15 Booking Photo Records

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

An inmate record may contain a `photo_filename` associated with a normalized JPEG in `data/photos/`. The public build copies eligible current photos to `docs/photos/`, and sweep reconciliation removes files no longer represented in the current roster subject to safety guards.

**Implementation and verification references:** `scraper/models.py`, `scraper/photos.py`, `scraper/sweep.py`, `tests/test_photos.py`.

## V1-16 Supplemental Feed Artifacts

**Shared concept:** [A-2 Source Observation](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-2-source-observation).

Cincinnati public-safety feeds are serialized as JSON payloads under `data/` and copied or transformed into public artifacts during the static build. Feed modules retain their dataset-specific rows together with generation and source-status information defined by each adapter.

**Implementation and verification references:** `scraper/cfs.py`, `scraper/cfs_pdi.py`, `scraper/shootings.py`, `scraper/open_data_feeds.py`, `tests/test_open_data_feeds.py`.

## V1-17 Daily Aggregate History

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

`data/history.json` stores day-level aggregate roster size and 24-hour booking and release counts through `HistoryRecord`. The model contains no individual identity and supports statistics and trend displays.

**Implementation and verification references:** `scraper/models.py`, `web/build.py`, `tests/test_build.py`.

## V1-18 Source Access Evidence Ledger

**Shared concept:** [A-23 Retained Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-23-retained-evidence).

`data/waf_block_log.json` records selected blocked, empty, recovery, and observation events with hash-linked integrity fields. A dedicated verifier walks the chain and reports integrity failures.

**Implementation and verification references:** `scraper/client.py`, `scraper/verify_block_log.py`, `tests/test_client.py`.

## V1-19 Transparency Metrics

**Shared concept:** [A-18 Source Status](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-18-source-status).

The web transparency module derives public summary measures from access evidence, including current condition, event counts, interruption streaks, recovery information, and cumulative denied time. The builder publishes the resulting transparency artifact and page.

**Implementation and verification references:** `web/transparency.py`, `web/build.py`, `tests/test_transparency.py`.

## V1-20 Statutory and Explanatory Reference Data

**Shared concept:** [A-34 Authority Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-34-authority-record).

V1 maintains ORC offense references, selected case-law references, and explanatory content in JSON files used by classification helpers and public statute or methodology pages. These records support presentation and lookup without replacing source charge text.

**Implementation and verification references:** `data/orc_offenses.json`, `data/orc_caselaw.json`, `data/explainers.json`, `scraper/orc.py`, `web/classify.py`.

## V1-21 Client-Side Search Index

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

The site builder emits `search.json`, a compact current-roster index consumed by browser JavaScript for lookup assistance. Index records are derived from the same snapshot and presentation fields used to render roster pages.

**Implementation and verification references:** `web/build.py`, `web/static/main.js`, `tests/test_outputs.py`.

## V1-22 Dispatch Map Index

**Shared concept:** [A-13 Public Artifact](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-13-public-artifact).

The build emits `dispatches.json` for browser map and public-safety presentation. The map script loads and presents this index as an enhancement to the corresponding textual information.

**Implementation and verification references:** `web/build.py`, `web/static/map.js`, `tests/test_outputs.py`.

## V1-23 RSS Activity Artifacts

**Shared concept:** [A-8 Booking Event](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-8-booking-event).

The builder renders all-change, booking, and release RSS feeds from recent change events. Feed entries use stable generated GUID logic and the configured site origin for public links.

**Implementation and verification references:** `web/build.py`, `web/templates/feed.xml`, `tests/test_outputs.py`.

## V1-24 Checksums and Publication Metadata

**Shared concept:** [A-17 Release Manifest](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-17-release-manifest).

The public build writes metadata and policy files including checksums, robots instructions, a security contact, a web manifest, human-readable attribution, `.nojekyll`, and the custom-domain file when configured.

**Implementation and verification references:** `web/build.py`, `tests/test_outputs.py`, `tests/test_build.py`.
