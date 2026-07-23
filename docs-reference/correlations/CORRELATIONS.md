---
title: Correlations
reference_namespace: V1
status: approved
authority: v1-correlations
owner_repository: AICincy/HCJC
document_family: correlations
effective_date: 2026-07-23
canonical_reference:
  version: 1.0.0
  tag: reference-v1.0.0
  commit: 281541be8e6f690d5f918967f5f0abeb12da808f
supersedes: []
superseded_by: null
relationships:
- from: V1-41
  relation: implements
  to: A-26
- from: V1-42
  relation: implements
  to: A-25
- from: V1-44
  relation: implements
  to: A-27
- from: V1-45
  relation: implements
  to: A-31
- from: V1-47
  relation: implements
  to: A-30
- from: V1-51
  relation: implements
  to: A-29
---

# Correlations

> **Authority:** Controls the descriptive reference for V1 public candidate dispatch matching and research correlation output.

V1 contains two correlation-oriented implementations. They serve different publication and research functions and are documented separately rather than treated as one interchangeable engine.

## V1-41 Public Candidate Dispatch Matching

**Shared concept:** [A-26 Candidate Relationship](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-26-candidate-relationship).

`scraper.match` produces bounded candidate dispatch rows for presentation with a custody record. It evaluates a booking against recent dispatch material using configured time, agency, and disposition conditions and returns candidate public records rather than an authoritative identity join.

**Implementation and verification references:** `scraper/match.py`, `tests/test_match.py`, `web/build.py`.

## V1-42 Research Correlation Output

**Shared concept:** [A-25 Correlation](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-25-correlation).

`scraper.correlate` builds a separate research-oriented set of candidate pairs from current roster and Calls for Service payloads. It writes joined keys and evidence values to `private/dispatch_correlations.json`, outside the ordinary public data and generated-site directories.

**Implementation and verification references:** `scraper/correlate.py`, `tests/test_correlate.py`, `.github/workflows/sweep.yml`.

## V1-43 Public Correlation Presentation

**Shared concept:** [A-26 Candidate Relationship](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-26-candidate-relationship).

Individual pages label public results as `Candidate dispatch calls`, preserving the distinction between a possible relationship and a source-confirmed fact. The presentation provides dispatch details and context without redefining the source inmate identifier as a dispatch identity key.

**Implementation and verification references:** `web/templates/inmate.html`, `web/build.py`, `tests/test_build.py`.

## V1-44 Correlation Input Signals

**Shared concept:** [A-27 Supporting Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-27-supporting-evidence).

The public path uses available booking and dispatch timing, agency, and disposition information. The research path additionally evaluates primary-charge description overlap against dispatch disposition or incident text and recognizes selected arrest dispositions.

**Implementation and verification references:** `scraper/match.py`, `scraper/correlate.py`, `tests/test_match.py`, `tests/test_correlate.py`.

## V1-45 Correlation Output Fields

**Shared concept:** [A-31 Evidence Score](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-31-evidence-score).

Research candidates contain inmate number, feed source, source-row index, rounded confidence value, and a `signals` object carrying temporal difference, textual overlap, booking date, and arrest-disposition boost state. Public matches retain the dispatch fields required by the individual-page view.

**Implementation and verification references:** `scraper/correlate.py`, `scraper/match.py`, `tests/test_correlate.py`.

## V1-46 Public Matching Window and Candidate Limit

The public matcher uses a configured temporal window and a bounded maximum number of matches returned for one custody record. Stable sorting and bounding support predictable page size and presentation.

**Implementation and verification references:** `scraper/match.py`, `tests/test_match.py`.

## V1-47 Agency and Disposition Eligibility

**Shared concept:** [A-30 Disqualifying Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-30-disqualifying-evidence).

The public matching path filters candidate dispatches using configured source-agency and disposition expectations before returning them for display. These conditions are part of candidate eligibility rather than a statement that the records identify the same event.

**Implementation and verification references:** `scraper/match.py`, `tests/test_match.py`.

## V1-48 Research Textual Overlap

**Shared concept:** [A-27 Supporting Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-27-supporting-evidence).

The research matcher tokenizes the primary charge description, removes short and common terms, and measures how many distinctive charge tokens appear in selected CFS text fields. A candidate requires nonzero textual overlap.

**Implementation and verification references:** `scraper/correlate.py`, `tests/test_correlate.py`.

## V1-49 Research Arrest-Disposition Boost

**Shared concept:** [A-31 Evidence Score](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-31-evidence-score).

The research score combines temporal proximity and textual overlap and can add a bounded boost when the CFS disposition contains a recognized arrest value. The score is rounded before serialization and compared with the configured minimum.

**Implementation and verification references:** `scraper/correlate.py`, `tests/test_correlate.py`.

## V1-50 Research Candidate Ordering

Research candidates are sorted by descending confidence, then inmate number, feed source, and source row index. This stable order makes repeated output deterministic when inputs are unchanged.

**Implementation and verification references:** `scraper/correlate.py`, `tests/test_correlate.py`.

## V1-51 Correlation Data Boundary and Disclaimer

**Shared concept:** [A-29 Missing Evidence](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-29-missing-evidence).

The research output is stored beneath `private/` and its module documentation describes the result as a research aid rather than a naming assertion. The public path uses candidate terminology on individual pages.

**Implementation and verification references:** `scraper/correlate.py`, `web/templates/inmate.html`, `README.md`.

## V1-52 Correlation Verification

**Shared concept:** [A-44 Verification Procedure](https://github.com/AICincy/HCJC2/blob/reference-v1.0.0/docs/reference/HCJC-CANONICAL-REFERENCE.md#a-44-verification-procedure).

The dedicated matcher and research-correlation test modules exercise eligibility, time parsing, text overlap, arrest boosts, thresholds, stable ordering, serialization, and candidate presentation assumptions.

**Implementation and verification references:** `tests/test_match.py`, `tests/test_correlate.py`, `tests/test_build.py`.
