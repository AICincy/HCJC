# Audit runbook reconcile — what is already shipped vs still open

## Audit metadata

- Date: 2026-05-22
- Trigger: external "JCStream Audit Runbook" (dated 2026-05-21, audited HEAD `2aea083b`) proposing six scraper remediations plus a Datadog observability pass.
- Method: grounded every runbook claim against the repo at HEAD `1cf4ab7`.
- Outcome: the runbook is ~95% already shipped. All six remediations exist in code. Datadog monitoring is not used and has been removed from the repository. Only two test gaps and an issue template were genuinely missing (closed in PR #220).

## Reality check on the runbook

The runbook was drafted in a no-network sandbox against a documented API surface, not the real source. Its Appendix A/B drafts assume symbol names that do not match this repo:

| Runbook assumption | Reality in repo |
|--------------------|-----------------|
| `scraper.client.Client` | `scraper.client.HcsoClient`, built via `make_client()` |
| `_BOILERPLATE_KEYWORDS` lowercase frozenset | UPPERCASE frozenset (`scraper/parsers.py`) |
| `_compact_anon_entries` rows keyed `ts` | keyed `timestamp_utc` / `event_summary` / `month` (`scraper/store.py`) |
| WAF returns HTTP 403/429 | WAF returns HTTP 200 with a <5 KB stub (see `audit/14_hcso_waf.md`) |
| `ddlog()` in `scraper/observability.py` (to be wired) | already shipped as `emit()` in `scraper/ddlog.py`; sweep already emits |

Because of this, PR #220 wrote fresh tests against the real surface rather than applying the runbook's drafts verbatim.

## Six remediations: all present at HEAD `1cf4ab7`

| # | Defect | Repo state |
|---|--------|-----------|
| 1 | crawl-delay sleep inside the lock | `client.py` `_sleep_for_crawl_delay` sleeps inside `with self._lock`. Test added in #220. |
| 2 | retry off-by-one (`range(1)`) | `client.py` `get_response` uses `range(1)`. Covered by `test_client.py` (5xx/429 retry tests). |
| 3 | `WafBackoffTracker` (no module-global streak) | `sweep.py` dataclass. Covered by `test_sweep.py` thread test. |
| 4 | boilerplate name guard | `parsers.py` `_looks_like_person_name` + `_BOILERPLATE_KEYWORDS`. Covered by `test_parsers.py`. |
| 5 | `keepalive_expiry=30` | `client.py` `__enter__` sets it on `httpx.Limits`. Test added in #220. |
| 6 | `anon_changelog` compaction (365d) | `store.py` `_compact_anon_entries`, `ANON_COMPACTION_MAX_DAYS=365`. Covered by `test_store.py`. |

## Action items (runbook section 20) mapped to repo state

| # | Runbook item | State |
|---|--------------|-------|
| 1 | Run pytest against patched tree | DONE — suite green |
| 2 | Add `DD_API_KEY` secret | NOT USED — Datadog removed |
| 3 | Wire `ddlog` into client/sweep | NOT USED — Datadog removed |
| 4 | Verify Datadog ingest | NOT USED — Datadog removed |
| 5 | Publish monitor 19947564 | NOT USED — Datadog removed |
| 6 | Tune `>=8 events/6h` threshold | NOT USED — Datadog removed |
| 7 | Add 5 missing unit tests | DONE — repo had 4/6; #220 adds #1 and #5 |
| 8 | Decide data-acquisition strategy | Owner decision (see HCSO feed finding below) |
| 9 | Freshness banner on site | Already implemented — `index.html:13-22` renders a server-side `<aside role="status">` interruption banner driven by `roster_stale.blocked` (build.py `_roster_stale_context`), no JS required. The runbook's JS every-page version is not needed. |
| 10 | Investigate HCSO RSS/JSON feed | See below |

## Item 10: HCSO structured-feed finding

- HCSO publishes the roster as an HTML search UI (WordPress on nginx), not a structured feed. No RSS, JSON, CSV, or documented export endpoint is exposed. The detail pages are HTML the parser was written against (`scraper/parsers.py`, `audit/14_hcso_waf.md`).
- Since 2026-05-19 the WAF returns HTTP 200 stubs to the GitHub runner rather than blocking with a 4xx. There is no alternate machine-readable surface to fall back to.
- The channel to request a real feed already exists: the ORC § 149.43(B) public-records request in `audit/15_pra_149_43B_request.md`. A feed/allowlist ask should go through that, not a new scraper path.
- Recommendation: do not build a feed fetcher speculatively. Keep the polite HTML scraper, keep documenting the denial, and route any feed request through the existing PRA letter.
