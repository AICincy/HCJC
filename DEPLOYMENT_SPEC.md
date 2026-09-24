# Remediation deployment specification

## Scope

This deployment addresses two defects in anonymized event enrichment:

1. release events were missing from enrichment because the sweep only inspected the current roster;
2. subsection charge codes were looked up without normalization, so values such as 2925.11A did not resolve to the base ORC section.

## Functional contract

_anon_enrichment(previous, current, offenses) MUST:

- consider every inmate in either snapshot;
- let the current snapshot override the previous snapshot for the same inmate number;
- normalize ORC codes through scraper.orc.normalize_code;
- resolve the normalized code through scraper.orc.lookup;
- convert the internal unknown degree sentinel ? to None;
- return None for missing titles and degrees;
- tolerate an empty or malformed offense catalog when called through _load_anon_offenses.

## Recovery contract

The backfill utility MUST:

- operate only on rows whose full identifiers are still within the selected retention window;
- use repository history only; it performs no new external data retrieval;
- prefer a historical snapshot appropriate to the event type;
- modify only existing tier and category fields;
- leave unresolved rows unchanged;
- write no new identifying fields.

## Safety contract

The deployment MUST:

- stop on unexpected untracked files;
- stage an explicit allow-list;
- never add .mcp.json;
- never push to a remote;
- emit newline-delimited JSON audit records;
- create an incident summary when historical recovery is unavailable.

## Verification contract

Success requires:

- V1: recent null-tag count is not increased;
- V2: the configured sweep dry-run exits successfully and recent null tags do not increase;
- V3: the complete pytest suite exits 0.

Any failure after commit causes a revert commit and exit 2.

## Non-goals

This remediation does not reconstruct data older than the seven-day retention period. It does not scrape a new source, alter current roster privacy rules, or change the public-site publication policy.
