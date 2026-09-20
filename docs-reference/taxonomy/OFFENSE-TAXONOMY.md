---
title: Offense Taxonomy
reference_namespace: V1
status: approved
authority: v1-taxonomy
owner_repository: AICincy/HCJC
document_family: taxonomy
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-53
  relation: implements
  to: A-34
- from: V1-54
  relation: implements
  to: A-33
- from: V1-56
  relation: implements
  to: A-35
- from: V1-58
  relation: implements
  to: A-36
---

# Offense Taxonomy

> **Authority:** Controls the descriptive reference for V1 ORC normalization, degree tiers, categories, statute pages, and charge presentation.

V1 supplements raw source charge descriptions with a project-maintained ORC reference catalog and presentation classifications. These derived labels support browsing, filtering, comparison, and explanatory context.

## V1-53 ORC Reference Catalog

**Shared concept:** [A-34 Authority Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-34-authority-record).

`data/orc_offenses.json` maps normalized offense identifiers to reference titles and degree labels consumed by scraper and web helpers. The catalog combines curated records and observed identifiers according to V1 update procedures.

**Implementation and verification references:** `data/orc_offenses.json`, `scraper/orc.py`, `scraper/update_orc_offenses.py`, `tests/test_orc.py`.

## V1-54 ORC Code Normalization

**Shared concept:** [A-33 Charge Observation](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-33-charge-observation).

The ORC helper normalizes source code strings into lookup keys, loads the catalog, and supplies title and degree lookups. Web classification separately determines whether a code is treated as a current ORC reference and constructs public statute links.

**Implementation and verification references:** `scraper/orc.py`, `web/classify.py`, `tests/test_orc.py`, `tests/test_statute_url.py`.

## V1-55 Severity Ladder

**Shared concept:** [A-35 Offense Concept](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-35-offense-concept).

V1 orders recognized degree labels from F1 through F5, M1 through M4, and MM. The ordered tier supports selection of a primary or maximum displayed degree and supplies the structure for severity ladders and statistics.

**Implementation and verification references:** `scraper/orc.py`, `web/classify.py`, `web/static/style.css`, `tests/test_classify.py`.

## V1-56 Offense Category Grouping

**Shared concept:** [A-35 Offense Concept](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-35-offense-concept).

The web classifier maps statutory chapters and selected non-ORC records into analytical categories such as violence, weapons, property, theft, drugs, family, traffic, and other. Category values drive card styling, legends, statistics, and peer context.

**Implementation and verification references:** `web/classify.py`, `web/static/style.css`, `tests/test_classify.py`.

## V1-57 Statute Pages

**Shared concept:** [A-34 Authority Record](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-34-authority-record).

The static builder renders a statute index and code-specific sections from the current roster and reference catalog. Pages show titles, degree context, current records, and links to Ohio code sources when the code qualifies.

**Implementation and verification references:** `web/build.py`, `web/templates/statute.html`, `web/classify.py`, `tests/test_statute_url.py`.

## V1-58 Charge-Tier Presentation

**Shared concept:** [A-36 Charge Assessment](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-36-charge-assessment).

Roster cards and individual pages derive a charge tier from recognized offense records and present it as statutory context. Public copy explains that the tier is descriptive and not a judicial determination or proof of guilt.

**Implementation and verification references:** `web/classify.py`, `web/templates/_card.html`, `web/templates/inmate.html`, `tests/test_classify.py`.

## V1-59 Primary Degree Selection

`scraper.orc.primary_degree` and web classification helpers select the highest recognized degree according to the V1 order when a record carries multiple charge codes. Empty or unrecognized inputs follow the helper-specific fallback behavior.

**Implementation and verification references:** `scraper/orc.py`, `web/classify.py`, `tests/test_orc.py`, `tests/test_classify.py`.

## V1-60 Chapter Classification

**Shared concept:** [A-35 Offense Concept](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-35-offense-concept).

The web layer extracts and normalizes ORC chapter context, including collapsed presentation groupings for related chapters. The chapter class supports charge styling and analytical summaries without modifying the source charge text.

**Implementation and verification references:** `web/classify.py`, `web/static/style.css`, `tests/test_classify.py`.

## V1-61 Case Category Classification

Court case numbers are classified into presentation categories used by case groups, labels, and court context. The logic recognizes supported case-number shapes and retains an other category for unmatched values.

**Implementation and verification references:** `web/classify.py`, `web/shape/court.py`, `tests/test_case_classify.py`.

## V1-62 Severity Statistics and Filtering

Tier counts, primary tier, and maximum tier are calculated for current roster records and aggregate views. These values support tier query parameters, filter controls, severity distributions, and peer comparisons.

**Implementation and verification references:** `web/classify.py`, `web/shape/stats.py`, `web/templates/index.html`, `web/templates/stats.html`, `tests/test_classify.py`.

## V1-63 Official Statute Source Links

**Shared concept:** [A-21 Provenance](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-21-provenance).

For codes recognized as ORC records, V1 constructs external links to `codes.ohio.gov`; non-ORC or unrecognized records follow alternate presentation behavior. Source links accompany project reference labels rather than replacing them.

**Implementation and verification references:** `web/classify.py`, `web/templates/statute.html`, `tests/test_statute_url.py`.

## V1-64 Taxonomy Tests and Currency Review

**Shared concept:** [A-44 Verification Procedure](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-44-verification-procedure).

ORC and classification tests cover normalization, catalog lookup, degree ordering, chapter behavior, source URL generation, and presentation helpers. Repository audit material records periodic currency review of the catalog.

**Implementation and verification references:** `tests/test_orc.py`, `tests/test_classify.py`, `tests/test_statute_url.py`, `audit/22a_orc_offenses_currency_audit.md`.
