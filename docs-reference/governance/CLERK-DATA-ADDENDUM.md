---
title: Clerk Data Governance Addendum
reference_namespace: V1
status: approved
authority: v1-governance
owner_repository: AICincy/HCJC
document_family: governance
effective_date: 2026-09-20
canonical_reference:
  version: 1.0.0
  tag: null
  commit: null
supersedes: []
superseded_by: null
relationships:
- from: V1-95
  relation: implements
  to: A-39
- from: V1-96
  relation: implements
  to: A-39
- from: V1-97
  relation: implements
  to: A-37
- from: V1-98
  relation: implements
  to: A-40
- from: V1-99
  relation: implements
  to: A-38
---

# Clerk Data Governance Addendum

> **Status:** Approved 2026-09-20. This document adds governance items V1-95
> through V1-99 to the V1 reference (`docs-reference/governance/PRIVACY-AND-LEGAL.md`,
> status: approved, effective 2026-07-23). Statutory citations verified
> against codes.ohio.gov on 2026-09-20: ORC 149.43 (effective 2026-09-07,
> HB 31, 136th GA) current; ORC 2953.32 (effective 2026-09-30, HB 96,
> 136th GA) current; former ORC 2953.52 renumbered to ORC 2953.33 by
> S.B. 288 (134th GA, effective 2023-04-04).

This addendum covers the two lawful channels for Hamilton County Clerk of
Courts data: (1) human reader submissions through the structured case-data
issue form, and (2) draft public-records request letters generated for
human senders. JCStream operates no automated access to courtclerk.org.

## V1-95 Reader-Submitted Case-Data Provenance Labeling

Every reader-submitted case record displayed on an inmate page must carry
its provenance: the submitting reader's handle, the ingest date, a link to
the submitting issue, and a link to the source docket page for independent
verification. The display must state that the entry is a reader-supplied
point-in-time snapshot, not the official docket.

**Implementation and verification references:** `web/templates/inmate.html`
(crowdsourced block), `web/pages.py` (`_load_crowdsourced_cases`),
`scraper/ingest_issue.py` (`source_url`, `issue_url`, `submitter`,
`ingested_utc`), `tests/test_ingest_issue.py`.

## V1-96 Case-Data Currency

Docket data changes as cases proceed. Submitted records are snapshots of
the docket as seen by the submitter on the ingest date. The display must
not imply live docket status. Next-hearing dates from submissions go stale
first and must be presented as "as submitted on <date>".

**Implementation and verification references:** `web/templates/inmate.html`,
`scraper/case_match.py` (annotation passthrough), `.github/ISSUE_TEMPLATE/case-data.yml`.

## V1-97 Sealed or Expunged Submitted Records

If a submitted case record is sealed or expunged under ORC 2953.32 /
2953.33 (former 2953.52, renumbered by S.B. 288, 134th General Assembly,
effective 2023-04-04) (or otherwise removed from public access at the
source), the submitted copy must be removed from `data/courtclerk_cases.json`
and from subsequent builds. The correction and removal routes in V1-89 apply
unchanged to submitted case data; a removal request for a submitted record
is handled with the same priority as a roster correction.

**Implementation and verification references:** `scraper/ingest_issue.py`
(`upsert` replacement semantics), `SECURITY.md`, `wiki/Legal.md`.

## V1-98 Access-Control-Respect Policy

JCStream does not circumvent access controls on external public-records
sources. Concretely: the project honors `robots.txt` disallow directives
(courtclerk.org disallows `/data/` and `/case-summary/` for all user
agents), does not automate CAPTCHA or bot-check challenges, and collects
Clerk of Courts data only through (a) human reader submissions in which
the submitter passes any challenge in their own browser, and (b) formal
public-records requests sent by humans. Automated scraping of the clerk's
site, and automated passing of its challenges, are out of scope by policy,
not merely by current capability.

**Implementation and verification references:** `scraper/courtclerk.py`
(docstring), `scraper/ingest_issue.py` (`valid_source_url`,
`confirmations_checked`), `.github/ISSUE_TEMPLATE/case-data.yml`,
`web/templates/data.html` (`#crowdsource`), `scraper/clerk_pra.py`.

## V1-99 No Legal Advice; Presumption of Innocence for Clerk-Sourced Charges

Submitted case data is public-record information, not legal advice, and
the project offers no interpretation of what a docket entry means for any
person's case. The V1-84 presumption of innocence applies to clerk-sourced
charges with the same force as to roster charges: the inmate-page display
of submitted records states that charges are accusations, not convictions.

**Implementation and verification references:** `web/templates/inmate.html`
(crowdsourced block notice), `web/templates/base.html` (footer),
`tests/test_cra_boundary.py`.
