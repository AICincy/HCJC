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
- prefer a historical snapshot appropriate to the event type;
- when history is incomplete, use the checked-in current roster as a fallback for non-release events;
- never use the current roster as the sole source for a release event;
- modify only existing tier and category fields;
- leave unresolved rows unchanged;
- write no new identifying fields.

## Safety contract

The deployment MUST:

- stop on unexpected untracked files;
- reject pre-staged paths outside the commit allow-list before making changes;
- revalidate the cached index against the allow-list immediately before commit;
- never add .mcp.json;
- never push to a remote;
- emit newline-delimited JSON audit records;
- create an incident summary when historical recovery is unavailable.

## Verification contract

Success requires:

- V1: recent null-tag count is not increased;
- V2: the configured sweep dry-run runs from a detached temporary Git worktree, exits successfully, and recent null tags do not increase in the operator worktree;
- V3: the complete pytest suite exits 0.

Any failure after commit causes a revert commit and exit 2.

## Non-goals

This remediation does not reconstruct data older than the seven-day retention period. The live-roster fallback reads only the repository's existing `data/current.json`; it does not perform new external retrieval. Released events still require a historical pre-release roster. The change does not alter current roster privacy rules or the public-site publication policy.
