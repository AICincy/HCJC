# Coverage audit record - 2026-07-05

Run of `audit/coverage_audit.py` against the repository at the state of PR #387
(dead data paths removed, retired-feed rationales encoded). Method: AST
dict-key extraction over `web/shape/*.py`, Jinja identifier scan over
`web/templates/*`, `data/` vs `docs/data/` publication diff, declared-feed
list parsed from the templates. Locked by `tests/test_coverage_audit.py`.

```
======================================================================
JCStream DATA COVERAGE AUDIT
======================================================================

## A. SHAPER-PRODUCED FIELDS

[UNSURFACED_NO_REASON]  0 fields

[WITHHELD_BY_DESIGN]  2 fields
   bond.py          my_bond  <- per-person value; only shown on that person's own detail page
   bond.py          my_percentile  <- per-person value; only shown on that person's own detail page

[INTERNAL_KEY]  4 fields
   court.py         civil  <- case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page
   court.py         criminal  <- case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page
   court.py         date_text  <- raw source date string carried beside parsed_date; the date renders via parsed_date
   court.py         traffic  <- case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page

[SURFACED]  73 fields
   (consumed by templates -- list suppressed for brevity)


## B. DATA FILES: stored in data/ vs published to docs/data/

[UNSURFACED_NO_REASON]  0 files

[WITHHELD_BY_DESIGN]  6 files
   egress_evidence.json  <- internal network-egress evidence; operational, not a public feed
   explainers.json  <- build input for statute explainer text; rendered into HTML
   incidents_recent.json  <- retired feed, last written 2026-05-19 (scraper removed); kept in data/ as historical record, not served
   oi_shootings_recent.json  <- retired feed, last written 2026-05-18; kept in data/ as historical record, not served
   orc_caselaw.json  <- build input for statute pages; content is rendered into HTML, not served raw
   pra_requests.json  <- internal PRA request log; may contain requester PII pre-redaction

[SURFACED]  15 files
   anon_changelog.json  <- published to docs/data/
   cca_complaints_recent.json  <- published to docs/data/
   cfs_pdi_recent.json  <- published to docs/data/
   cfs_recent.json  <- published to docs/data/
   changelog.json  <- published to docs/data/
   crime_stars_recent.json  <- published to docs/data/
   current.json  <- published to docs/data/
   history.json  <- published to docs/data/
   orc_offenses.json  <- published to docs/data/
   pedestrian_stops_recent.json  <- published to docs/data/
   shootings_recent.json  <- published to docs/data/
   traffic_stops_drivers_recent.json  <- published to docs/data/
   use_of_force_incidents_recent.json  <- published to docs/data/
   use_of_force_pdi_recent.json  <- published to docs/data/
   waf_block_log.json  <- published to docs/data/

[PUBLISHED BUT NOT NAMED IN ANY TEMPLATE]  0 files
   (served at a URL, but no link tells the public they exist)

======================================================================
SUMMARY
======================================================================
Fields  : 73 surfaced, 2 withheld-by-design, 4 internal-key, 0 UNSURFACED-NO-REASON
Files   : 15 published, 6 internal-by-design, 0 STORED-BUT-UNPUBLISHED
Hidden  : 0 published files not named in any template
```
