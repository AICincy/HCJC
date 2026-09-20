# A1 deployment and freshness report

**Claim ID:** A1-DEPLOY-FRESH-001  
**Audit question:** Across three recent completed scheduled cycles, what public timestamps separate scheduled sweep start, generated snapshot, committed result, Pages completion, and the public rendered timestamp?  
**Overall technical verdict:** **Pass, bounded.** Three complete public pipeline sequences were reconstructed. The report does not establish roster accuracy, upstream-source accuracy, private Pages settings, or client-specific cache propagation at the historical deployment instant.

## Scope, custody, and completion condition

**Frozen source baseline:** `fbe33ca9af7db6e08ab4a6f16515ece26085b241` (`data+site: sweep 2026-09-19T19:28Z`).  
**Public-observation window:** `2026-09-19T19:41:27Z` through `2026-09-19T19:45:57Z`.  
**Access level:** public GitHub Actions and repository metadata, public source at the frozen baseline, and a non-interactive public site render.

The acceptance condition was three reconstructable completed scheduled sequences with UTC timestamps, stable locators, measured deltas, and cache qualification. It is met. No source, workflow, configuration, data, account, or public service was changed. No raw roster record, identifier, or person-level field is reproduced here.

The global public-audit composition plan governs this report. `aai-cognitive-interface` controlled custody and the private-state boundary; `research-execution-briefs` supplied current public-source retrieval; `claim-source-auditor` supplied atomic source status; `agent-churn-control` governed the failed Firecrawl aggregate-extraction route; and Browser supplied the independent live render.

## Evidence sources and grades

| Evidence ID | Source and stable locator | Observation | Grade | What it establishes |
|---|---|---|---|---|
| E1 | Frozen source: `.github/workflows/sweep.yml:21-25, 134-180` at `fbe33ca` | Declares `*/15` cron, comments that actual cadence is 20-45 minutes, builds `docs/`, commits changed data/site output, then runs the deploy-staleness alarm. | E | Implementation and documented expectation only. |
| E2 | Public GitHub Actions: [sweep #2561](https://github.com/AICincy/HCJC/actions/runs/35447978872), [#2562](https://github.com/AICincy/HCJC/actions/runs/35457570140), [#2563](https://github.com/AICincy/HCJC/actions/runs/35464350357) | Each is a completed, successful scheduled sweep. | B | Publicly recorded workflow starts, finishes, run heads, and result status. |
| E3 | Public GitHub Actions: [Pages #2822](https://github.com/AICincy/HCJC/actions/runs/35448112583), [#2823](https://github.com/AICincy/HCJC/actions/runs/35457712230), [#2825](https://github.com/AICincy/HCJC/actions/runs/35464469876) | Each is a completed, successful dynamic Pages build/deployment for the associated resulting commit. | B | Publicly recorded Pages completion, not private Pages configuration. |
| E4 | Public GitHub commit metadata for `72a1338`, `1c0c039`, and frozen `fbe33ca`; aggregate metadata fields parsed without retaining roster rows | Each resulting commit's parent equals the corresponding sweep run's `head_sha`; each commit contains the generated snapshot timestamp used below. | B | The run-to-result sequence is traceable without treating the run head as the resulting commit. |
| E5 | Fresh in-app-browser render of [aretheyinjail.com](https://www.aretheyinjail.com/) during the observation window | Page title and visible aggregate summary reported **1,116** in custody and **Sep. 19, 2026, 3:28 PM ET** as the sweep/generated time. | A | One direct public render matched the frozen commit's aggregate timestamp, subject to the cache limitation below. |
| E6 | Public repository API `GET /repos/AICincy/HCJC` and unauthenticated `GET /repos/AICincy/HCJC/pages`, observed `2026-09-19T19:45:57Z` | Repository metadata reported `has_pages: true`; the public `/pages` endpoint returned HTTP 404. | B | A public API discrepancy, not proof that Pages is off. |

### Retrieval limitation

A Firecrawl request forced fresh retrieval with an aggregate-only query and PII redaction. The connector returned HTTP 200 metadata but no extractable markdown for the JSON endpoint. An earlier structured-schema attempt was rejected by the connector schema before retrieval. The accepted retry receipt records this as a local extraction failure. It is **not** evidence of a site failure, and the direct browser route, GitHub Actions records, and public commit metadata were used instead.

## Reconstructed public sequences

The sweep workflow runs on the prior `main` head and creates a new commit near job completion. The parent relationship below is the control that ties a scheduled run to its resulting commit. It prevents the common error of calling a run's starting `head_sha` the newly published snapshot.

| Cycle | Scheduled sweep start | Resulting aggregate metadata | Resulting commit | Pages completion | Sweep to Pages complete | Generated to Pages complete | Evidence |
|---|---:|---:|---|---:|---:|---:|---|
| Sweep #2561 | `2026-09-19T14:11:31Z` | `2026-09-19T14:13:18Z`, aggregate count 1,121 | `72a1338` at `14:14:05Z`; parent `2bdcbd3` equals sweep run head | Pages #2822 at `14:14:42Z` | 191 s | 84 s | E2-E4 |
| Sweep #2562 | `2026-09-19T17:16:24Z` | `2026-09-19T17:18:12Z`, aggregate count 1,117 | `1c0c039` at `17:18:59Z`; parent `72a1338` equals sweep run head | Pages #2823 at `17:19:36Z` | 192 s | 84 s | E2-E4 |
| Sweep #2563 | `2026-09-19T19:26:25Z` | `2026-09-19T19:28:01Z`, aggregate count 1,116 | `fbe33ca` at `19:28:48Z`; parent `7fb5753` equals sweep run head | Pages #2825 at `19:29:19Z` | 174 s | 78 s | E2-E4 |

Across these three observed cycles, the public pipeline reached recorded Pages completion **2 minutes 54 seconds to 3 minutes 12 seconds** after the scheduled sweep run began. Snapshot generation preceded recorded Pages completion by **1 minute 18 seconds to 1 minute 24 seconds**. This establishes public pipeline timing for the measured runs. It does not establish that every external viewer received the update at that exact second.

## Current public-render cross-check

The non-interactive browser observation took place approximately **13 minutes 26 seconds to 16 minutes 33 seconds** after the frozen commit's `generated_utc` of `19:28:01Z`. The rendered aggregate count and displayed timestamp matched that frozen snapshot. This is a direct delivery check after Pages #2825, not a retrospective cache-propagation measurement at the original deployment minute.

The in-scope static source says the sweeper skips a snapshot younger than 20 minutes. The observed page was therefore below that source-defined no-double-scrape threshold during the observation window. No cache headers, CDN edge comparison, or geographically separate viewer comparison was collected, so client-specific cache behavior remains unknown.

## Atomic claim matrix

| Claim ID | Atomic claim | Claim-source status | Basis and locator | Technical verdict | Evidence grade |
|---|---|---|---|---|---|
| A1-C1 | Three recent completed scheduled cycles can be correlated from public sweep runs through Pages completion. | `verified` | E2-E4; run-head-to-commit-parent equality and Pages `head_sha` equality for all three rows. | Pass | B |
| A1-C2 | The measured public pipeline interval from scheduled sweep start to recorded Pages completion was under four minutes for all three observed cycles. | `verified` | 174 s, 191 s, and 192 s from E2-E4. | Pass | B |
| A1-C3 | At the observation window, the public rendered site displayed the frozen snapshot's aggregate time and count. | `verified` | E5 compared with frozen `fbe33ca` aggregate metadata in E4. | Pass | A |
| A1-C4 | The observed completed scheduled sweep cadence was consistent with the source comment's stated 20-45 minute effective cadence. | `conflicting` | E1 states 20-45 minutes; E2 recorded start gaps of **3 h 04 m 53 s** (#2561 to #2562) and **2 h 10 m 01 s** (#2562 to #2563). | Fail for the measured window | B versus E |
| A1-C5 | A public `GET /pages` HTTP 404 establishes that GitHub Pages is disabled for the repository. | `conflicting` | E6 returned 404, but the same public repository metadata says `has_pages: true`, E3 records successful Pages deployments, and E5 rendered the public site. | Fail | B and A |

## What this audit does not establish

- A successful sweep or Pages workflow does **not** prove the public roster is accurate, complete, or current against the official HCSO source. That is A6's deferred privacy-gated work.
- Public source and Actions evidence do **not** establish current Pages source configuration, custom-domain configuration, Actions variables, secrets, owner intent, or e-mail behavior. Those remain private-gate unknowns.
- The three latest available completed scheduled runs show a material gap from the workflow's documented 20-45 minute effective cadence. This report does not identify the cause of those gaps or call them an upstream, GitHub, or application defect.
- The direct public render is a single fresh-tab observation. It is not a multi-region CDN, cache-header, or historical browser-cache study.

## Smallest safe next audit action

AQ should independently reproduce **one** of the three sequences through an alternate public route, then conduct a passive, aggregate-only 24-hour observation of scheduled-run starts and public rendered timestamps. The target question is whether the 2-hour-plus spacing persists. No workflow change, rerun, secret inspection, source-fidelity comparison, or remediation is authorized by this report.

## Compact execution trail

| UTC | Action | Result |
|---|---|---|
| `2026-09-19T19:41Z-19:42Z` | Loaded A1 work card, frozen baseline, and public-only boundaries. | Controls applied. |
| `2026-09-19T19:41Z-19:43Z` | Retrieved public sweep, Pages, and commit metadata. | Three matched sequences reconstructed. |
| `2026-09-19T19:43Z-19:44Z` | Attempted Firecrawl aggregate-only JSON retrieval under anti-churn control. | Connector extraction failure recorded; no raw roster retained. |
| `2026-09-19T19:43Z-19:45Z` | Performed non-interactive fresh-tab public render and repository/Pages API check. | Aggregate timestamp/count observed; Pages API discrepancy retained as unresolved. |

**Actions deliberately not taken:** private Actions/Pages/Giscus inspection; workflow reruns; account login; official-source person-linked comparison; source or configuration changes; publication; and external contact.
