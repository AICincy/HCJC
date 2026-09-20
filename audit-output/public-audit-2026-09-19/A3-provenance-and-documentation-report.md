# A3 provenance and documentation report

**Work card:** A3-PROVENANCE-001  
**Question:** Do the supplied status report and renewal plan distinguish source-supported findings from documentation-only, private-state, and unsupported legal or operational assertions?  
**Completion condition:** Every scoped material claim has one source-audit status, a stable locator or stated search scope, and an explicit unresolved state.  
**Frozen baseline:** `fbe33ca9af7db6e08ab4a6f16515ece26085b241` at `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-baseline`  
**Observation window:** 2026-09-19 19:43Z through 2026-09-19 19:54Z  
**Access level:** public sources plus the frozen, read-only source baseline. No private configuration, account settings, secrets, mail, external correspondence, person-linked official-source comparison, or source changes were accessed or performed.

## Scope and verdict

The Technical Status Report is a useful lead register, but it is not reliable as a current verification record. It correctly identifies substantial static architecture and several real documentation conflicts. It overstates current private configuration, treats historical or issue-tracker recommendations as factual closure, and misstates several source-resolvable values.

The Remediation and Renewal Plan contains useful hypotheses and design ideas, but it must not be executed as written. Its Phase 0 assertions depend on the deferred private-state gates. Its proposed documentation deletions preempt an owner-decision issue. Its presumption-of-innocence citation misapplies the cited public-records statute. The iCalendar privacy claim requires a separate human-approved privacy protocol.

This is a source-and-provenance audit only. It does not determine live roster accuracy, current secret/variable state, legal liability, legal strategy, or whether any remediation should occur.

## Source hierarchy

| Rank | Source class | Use in this audit | Boundary |
|---|---|---|---|
| 1 | Current primary public source | Current HCSO `robots.txt`, public deployed site, Ohio Laws, Supreme Court of Ohio opinion | Establishes only the observed public fact or authority text. |
| 2 | Frozen executable source | Baseline code, workflows, templates, manifests, and committed aggregate ledger | Establishes implementation or committed historical data, not current production/private state. |
| 3 | Public GitHub evidence | Issue #278 and public Actions REST responses | Establishes the public issue/run fields observed, not hidden configuration or a completed fix. |
| 4 | Supplied documents | Technical Status Report and Remediation and Renewal Plan | Lead list and claims under review, never operational authority. |

## Sources, identity, and retrieval record

| ID | Source | Locator or retrieval route | Observed result |
|---|---|---|---|
| S1 | Frozen baseline | `git rev-parse HEAD` | `fbe33ca9af7db6e08ab4a6f16515ece26085b241`; working tree clean before report persistence. |
| S2 | Supplied status report | `C:\Users\jared\Desktop\Technical Status Report.txt:1-326` | Dated 2026-09-18; it expressly says deployed access was blocked and source directories were not directly read. |
| S3 | Supplied plan | `C:\Users\jared\Desktop\Remediation and Renewal Plan.txt:1-631` | A proposal document containing commands and setup directions; treated only as auditable evidence. |
| S4 | Public deployed site | [homepage](https://www.aretheyinjail.com/) and [robots.txt](https://www.aretheyinjail.com/robots.txt), direct HTTP at 19:47Z | Both returned HTTP 200. The homepage rendered a JCStream title; robots requests search engines not to index, but did not block direct retrieval. |
| S5 | Official upstream robots source | [HCSO robots.txt](https://www.hcso.org/robots.txt), direct HTTP at 19:46Z | HTTP 200 and current `Crawl-delay: 10` directive. |
| S6 | Public issue record | [GitHub issue #278](https://github.com/AICincy/HCJC/issues/278), public REST response during the observation window | Closed 2026-06-04 with zero comments. Body repeatedly says owner decision is needed for R1, R8, R9, and R10. |
| S7 | Public workflow records | [sweep workflow runs API](https://api.github.com/repos/AICincy/HCJC/actions/workflows/sweep.yml/runs?per_page=100) and [all-runs API](https://api.github.com/repos/AICincy/HCJC/actions/runs?per_page=100) | Sweep run numbers 2544-2551 returned `completed/success`; CI 1165 returned `completed/cancelled`; CI 1166 returned `completed/success`. |
| S8 | Current Ohio statute | [Ohio Revised Code § 149.43](https://codes.ohio.gov/ohio-revised-code/section-149.43), retrieved 2026-09-19 | Current page identifies the provision as public-record availability, effective 2026-09-07. |
| S9 | Court authority identity | [Supreme Court of Ohio opinion, 2016-Ohio-8447](https://www.supremecourt.ohio.gov/rod/docs/pdf/0/2016/2016-Ohio-8447.pdf), with CourtListener identity search | The case reference in the report corresponds to a real Ohio Supreme Court public-records opinion. No later-treatment analysis was needed because neither attachment relies on its holding. |

## Claim inventory reconciliation

**Inventory rule:** 31 material factual or source-dependent claims were scoped. Each row below has exactly one permitted claim-source status. Excluded items are styling preferences, effort estimates, future design choices, and claims assigned to A1, A2, or A4 for direct execution testing rather than provenance review.

### Technical Status Report claims

| Claim ID | Claim text | Status | Source file or source | Stable locator | Source excerpt or result | Basis and remediation note |
|---|---|---|---|---|---|---|
| TSR-01 | The deployed site was inaccessible because of `robots.txt`. | conflicting | S4 | Homepage and `robots.txt`, HTTP 200 at 19:47Z | Both endpoints returned 200. | Robots guidance does not establish access blocking here. Replace this premise with the observed route and timestamp. |
| TSR-02 | JCStream is a static HCSO mirror using supplemental Cincinnati Open Data, Jinja rendering, `docs/`, and JSON persistence. | verified | Frozen baseline | `README.md:3-4`; `web/build.py:1-6,20,95-97`; `scraper/store.py:1-7` | Source describes static rendering to `docs/` and JSON snapshot persistence. | Static implementation is supported. This does not prove current live correctness. |
| TSR-03 | `*/15` sweep scheduling is configured. | verified | Frozen baseline | `.github/workflows/sweep.yml:21-25`; `scraper/sweep.py:234` | Cron is `*/15`; interval constant is 20 minutes. | Configuration is verified, not every expected run or production freshness. |
| TSR-04 | Successful workflow entries establish that the core pipeline ran as intended. | conflicting | Frozen baseline | `.github/workflows/sweep.yml:85-88` | The `python -m scraper.sweep` step uses `continue-on-error: true`. | A successful workflow can coexist with a failed sweep command. Require step-level logs and published-artifact correlation from A1. |
| TSR-05 | Seven production and three development dependencies are exactly pinned in both `requirements.txt` and `pyproject.toml`. | conflicting | Frozen baseline | `pyproject.toml:11-24`; `requirements.txt:1-7` | Six production dependencies appear in `pyproject`; `ruff` and `mypy` are absent from `requirements.txt`. | Correct the inventory before treating the files as synchronized. |
| TSR-06 | CI runs Ruff 0.16.7 and mypy 2.3.1. | conflicting | Frozen baseline | `pyproject.toml:24`; `.github/workflows/ci.yml:28-33` | CI installs Ruff 0.15.22 and mypy 2.3.0. | Static pin drift exists. A2 owns reproducibility and impact classification. |
| TSR-07 | The 20-minute skip gate is implemented. | verified | Frozen baseline | `scraper/sweep.py:234,500-512` | `MIN_SWEEP_INTERVAL_S = 20 * 60`; fresh data returns from the cycle. | This is static implementation evidence only. |
| TSR-08 | Roster-volume, query-failure, stale-alarm, and photo-prune guard values are 0.5, 0.10, 6 hours, and 0.5 respectively. | verified | Frozen baseline | `scraper/sweep_guards.py:28,63-64,83,92-96,158-166` | Constants and enforcement paths match the listed values. | The status report correctly identifies the static values except where it later calls two of them unknown. |
| TSR-09 | PRA code and a scheduled daily workflow exist. | verified | Frozen baseline | `.github/workflows/pra_daily.yml:1,17-22,51-77`; `scraper/pra.py:64-80`; `scraper/pra_capias.py:69-86` | Workflow and guarded send paths are present. | Code existence does not establish present mail configuration or delivery. |
| TSR-10 | Current PRA SMTP secrets are unset and the current loop is logging-only. | not found in searched sources | S2-S4 plus frozen baseline | Search scope: all supplied documents, frozen PRA source/workflow, public GitHub issue/runs, and public site | No authorized public source exposes the current secret values or their presence. | Retain as Unknown. Route only to deferred A5 with owner-authorized read-only metadata. |
| TSR-11 | The PRA ledger has no real records while dry-run is active. | conflicting | Frozen baseline | `data/pra_requests.json`, Git blob `d4f3987b2b8a6d966862919918c6e19652133bf7`, aggregate-only review | 352 records: 192 `sent`, 48 `failed`, 112 `dry_run`. | Historical `sent` statuses refute “no real records,” but do not prove current SMTP configuration or external delivery. |
| TSR-12 | Giscus code is gated on configured IDs. | verified | Frozen baseline | `web/build.py:192-200`; `web/templates/inmate.html:463-485` | Rendering checks `giscus.repo_id`; IDs are build-time environment values. | Static capability is established. |
| TSR-13 | Current Giscus variables are absent and the widget is currently non-operational. | not found in searched sources | S2-S4 plus frozen baseline | Search scope: source, public site routes reviewed, issue/runs, and supplied documents | No owner-authorized configuration view was available. | Do not infer variable state from template defaults or prior prose. Deferred A5 gate. |
| TSR-14 | Issue #278 is closed, has no visible comments, and leaves R1/R8/R9/R10 unresolved. | verified | S6 | GitHub issue #278 metadata/body | Closed 2026-06-04; `comments: 0`; body says “Decision needed.” | Correctly limited as to closure/comments. It does not prove no linked remediation exists outside the inspected public record. |
| TSR-15 | R8, R9, and R10 are all “hallucination-confirmed” and each underlying statement is fictitious. | conflicting | S6, S9 | Issue #278 sections R8-R10; official opinion | Issue uses conditional/recommendatory language; the cited case reference is a real official opinion. | Distinguish lack of project-corpus support from external falsity and from owner decision. |
| TSR-16 | The report’s exact three-way crawl-delay attribution is current: wiki says 0, README says 10, and code says 0.5. | conflicting | S5 plus frozen baseline | `wiki/Architecture.md:53-54`; `wiki/Legal.md:64-68`; `scraper/client.py:29-41`; complete baseline `README.md` crawl search | Frozen wiki says HCSO sets no delay; frozen README does not contain the asserted 10 value; code is 0.5; live HCSO robots says 10. | Preserve the real source conflict, but correct the stale/misattributed wording before use. |
| TSR-17 | Operative default concurrency cannot be established. | conflicting | Frozen baseline | `scraper/client.py:38-41,54-58` | `DEFAULT_CONCURRENCY = 16` and the client default consumes it. | Static default is resolved as 16. Actual runtime override remains a distinct question. |
| TSR-18 | Operative photo-prune threshold cannot be established. | conflicting | Frozen baseline | `scraper/sweep_guards.py:80-83,143-166` | `PHOTO_PRUNE_MAX_FRACTION = 0.5`; deletion is skipped above it. | Static threshold is resolved as 50 percent. |
| TSR-19 | The 7-day anonymization and 365-day compaction interaction cannot be established without code. | conflicting | Frozen baseline | `scraper/store.py:290-296,384-396,420,437-460,488-491` | The source anonymizes after seven days, then compacts anonymous rows older than 365 days. | Implementation separation is established; a population-level behavior claim would require A4’s controlled tests. |
| TSR-20 | CNAME routes requests directly to `docs/index.html`. | conflicting | Frozen baseline | `CNAME:1`; `index.html:5-6,14-15`; `.github/workflows/sweep.yml:179-181` | CNAME contains a hostname only; root HTML performs the `./docs/` redirect. | Separate hostname mapping from route handling. |
| TSR-21 | CI runs #1165 and #1166 both completed successfully. | conflicting | S7 | Public Actions response filtered by `name=ci`, `run_number=1165..1166` | #1165 was `completed/cancelled`; #1166 was `completed/success`. | Correct the historical run summary. |

### Remediation and Renewal Plan claims

| Claim ID | Claim text | Status | Source file or source | Stable locator | Source excerpt or result | Basis and remediation note |
|---|---|---|---|---|---|---|
| RRP-01 | Phase 0’s PRA and Giscus gaps are confirmed current non-functional features requiring only configuration. | not found in searched sources | S3 plus frozen baseline | Plan:31-59; frozen PRA/Giscus locators in TSR-09/12 | Code supports optional configuration gates, not current setting state. | The plan must be rewritten as a deferred private-state hypothesis, not a current defect. |
| RRP-02 | The remediation table’s crawl-delay facts are source-supported: HCSO advertises 10 seconds and JCStream code defaults to 0.5 seconds. | verified | S5 plus frozen baseline | Plan:76-83; HCSO `robots.txt`; `scraper/client.py:29-41` | Live upstream declares `Crawl-delay: 10`; source constant is 0.5. | These facts support a documentation reconciliation task only after an accepted audit packet. |
| RRP-03 | The photo guard’s authoritative definition is in `scraper/sweep.py`. | conflicting | Frozen baseline | Plan:81-83; `scraper/sweep_guards.py:80-83`; `scraper/sweep.py:52-60` | The constant is defined in `sweep_guards.py`; `sweep.py` imports the function. | Correct the plan’s source locator before any documentation work. |
| RRP-04 | Issue #278 conclusively authorizes deletion/quarantine of R8-R10 passages. | conflicting | S6 | Plan:84-96; issue #278 R8-R10 | Issue says owner decision is needed and uses recommended or conditional language. | Do not convert an issue recommendation into an authorized deletion. |
| RRP-05 | The proposed untracked-build-artifact guard fails when untracked files are present and passes when absent. | verified | S3 and isolated shell reproduction | Plan:137-144; Git for Windows Bash reproduction at frozen baseline | Synthetic matching line produced exit 1; non-matching line produced exit 0. | The `exit 1` terminates the shell before `|| true`; do not label this plan step defective. |
| RRP-06 | `--released: --muted` makes the `released` status token equal the `muted` token. | conflicting | S3 plus W3C CSS specification | Plan:286-289; [CSS Custom Properties §3](https://www.w3.org/TR/css-variables-1/#using-variables) | Custom properties are substituted through `var()`; the plan stores literal `--muted`. | Use `var(--muted)` if an alias is intended; validate in the eventual CSS scope. |
| RRP-07 | ORC §149.43 supports the plan’s presumption-of-innocence disclaimer. | conflicting | S8 | Plan:364-371; Ohio Laws §149.43 | The current statute is an availability-of-public-records provision. | The citation does not supply the stated presumption proposition. See legal-authority inventory below. |
| RRP-08 | An iCalendar feed with person identifiers has no privacy implication beyond data already public. | manual review needed | S3 | Plan:418-430 | The plan proposes person identifiers but supplies no field inventory, retention rule, audience control, or privacy protocol. | Direct technical inspection cannot decide the privacy/legal judgment. This is an A6 and human-gate question. |
| RRP-09 | Current PRA dry-run behavior produces no records. | conflicting | Frozen baseline | Plan:218-228; `data/pra_requests.json` aggregate in TSR-11 | Frozen ledger contains historical `sent`, `failed`, and `dry_run` statuses. | Separate present workflow behavior from historical ledger contents. |
| RRP-10 | The proposed §149.43(C) dossier is ready to be treated as a legal-filing support mechanism. | manual review needed | S3 and S8 | Plan:549-563; Ohio Laws §149.43(C) | The statute has public-records remedies; the plan supplies no case-specific filing facts or legal review. | Human legal-purpose gate required. No filing or legal conclusion is authorized. |

## Legal-authority inventory

This table audits citation currency and fit. It is not legal advice, a legal conclusion, or a filing assessment.

| Identifier | Type | Citation | Status | Treatment | Basis | Retrieval source | Verified as of | Effective date | Correction note |
|---|---|---|---|---|---|---|---|---|---|
| LAW-01 | Ohio statute | ORC § 149.43, used at Plan:368-371 | misapplied | Not a negative-treatment finding | Current §149.43 governs public-record availability; it does not supply the plan’s presumption-of-innocence proposition. | [Ohio Laws](https://codes.ohio.gov/ohio-revised-code/section-149.43) | 2026-09-19 | 2026-09-07 | Remove this citation from that proposition unless another primary authority is verified before use. |
| LAW-02 | Ohio statute | ORC § 149.43(C), used at Plan:554 | current | Application not evaluated | The current provision includes court-action/remedy language, but a project dossier’s use in a real matter needs facts and legal review outside scope. | [Ohio Laws](https://codes.ohio.gov/ohio-revised-code/section-149.43) | 2026-09-19 | 2026-09-07 | Keep the authority separate from any assertion that the described materials satisfy a filing requirement. |
| LAW-03 | Ohio case | *State ex rel. Shaughnessy v. Cleveland*, 2016-Ohio-8447 | unverifiable | No comprehensive later-treatment review performed | Case identity is confirmed by the official opinion, but the attachments provide no proposition that requires reliance or treatment analysis. | [Supreme Court of Ohio](https://www.supremecourt.ohio.gov/rod/docs/pdf/0/2016/2016-Ohio-8447.pdf) | 2026-09-19 | 2016-12-29 | Do not call the case fictitious. Assess relevance and later treatment only if it is proposed for substantive use. |

## Material contradictions and ownership

| Contradiction | Evidence grade | Consequence for this audit wave | Owner or gate |
|---|---|---|---|
| Direct site access was reported blocked, but public homepage and robots endpoints were directly reachable. | A | Replace the report’s live-access premise. A1 still measures freshness rather than treating access as proof of accuracy. | A1 / A0 |
| Report calls dependency files synchronized and CI pins current, but frozen manifests and workflow pins differ. | E | Do not call local or CI results reproducible until A2 completes its isolated matrix. | A2 |
| Report calls concurrency and photo thresholds unknown, but frozen source resolves their static defaults. | E | Correct the documentation lead list. Runtime overrides remain separate. | A0, then A2 if runtime reproduction matters |
| Report and plan call PRA current-state conclusions confirmed, but secret/variable state is private; frozen historical ledger includes non-dry-run statuses. | E and X | Preserve current state as Unknown. Do not configure or send. | Deferred A5 human gate |
| Issue #278 asks for owner decisions, but report and plan convert that into completed factual conclusions and deletion directives. | B | Retain each DOCX item as unverified pending authorized source-bundle review and owner decision. | A0 / AQ |
| Plan cites public-records law for a presumption-of-innocence statement. | A | Citation must not be reused for that proposition. | Human legal-purpose gate |

## Unresolved claims and exact next routes

| Unresolved claim | Why unresolved | Smallest safe next route | Gate |
|---|---|---|---|
| Current PRA SMTP and recipient configuration | Secrets and variables are not public evidence. | Owner-authorized read-only metadata listing presence only, never values. | Deferred A5 |
| Current Giscus state | Source shows the gate, not the actual configured values. | Owner-authorized read-only variables metadata or a public no-identifier rendered-page observation. | Deferred A5 |
| Official-source roster fidelity | A mirror count or Pages success cannot prove record accuracy. | Aggregate-first comparison under a written retention and redaction protocol. | Deferred A6 |
| The DOCX material’s exact factual basis and intended use | Issue #278 is a lead, not the source bundle or an owner decision. | Inspect the authorized document bundle with source citations and a per-passage claim map. | A0 authorization / owner decision |
| Whether the proposed iCalendar feature is acceptable | It depends on fields, publication surface, retention, and privacy policy. | Privacy design review before prototyping or generating a feed. | Human gate |

## Quality and limitation record

- The status taxonomy is limited to `verified`, `verified in broader bundle`, `conflicting`, `not found in searched sources`, and `manual review needed`. No row blends them.
- Static source and committed ledger data establish implementation or historical artifact state only. They do not establish live deployment health, current secret state, mail delivery, or legal sufficiency.
- The report reads only aggregate PRA status counts. It includes no raw jail records, names, inmate identifiers, correspondence contents, secret values, or session material.
- A direct attempt to treat small run numbers as GitHub Actions API run IDs returned HTTP 404. That route was discarded. The accepted replacement queried the public workflow/run-list endpoints by `run_number`.
- The direct Ohio Laws page route returned a tool-level empty response and a later HTTP 404 through a separate web client. The accepted primary-authority route was the current Ohio Laws search result and its official statute page. This limitation does not change the legal-citation finding because the returned official text identified the statute, effective date, and subject matter.
- The plan’s CI guard reproduction used synthetic command output only. It created no file and did not run a build or change the baseline.

## Compact execution trail

| UTC window | Observable action | Result |
|---|---|---|
| 19:43Z | Resolved work card, frozen manifest, charter, supplied documents, and source-audit taxonomy. | Scope fixed to public provenance review. |
| 19:43-19:47Z | Read frozen manifests, workflows, source modules, templates, aggregate ledger metadata, and documentation locators. | Source map established; baseline remained clean. |
| 19:46-19:49Z | Retrieved HCSO/site robots, public homepage, GitHub issue/run metadata, Ohio Laws, CourtListener identity, and official Ohio opinion. | Public source contradictions and authority checks recorded. |
| 19:50-19:54Z | Reproduced the plan’s shell guard with synthetic matched and unmatched output. | Match exits 1; no-match exits 0; earlier masking concern rejected. |

## A3 handoff to A0 and AQ

1. Amend the prior status audit to remove the claim that the proposed CI guard cannot fail. The isolated shell reproduction shows it fails correctly on a matching untracked path.
2. Accept no report assertion that current SMTP, recipient, Giscus, Pages, or Actions variable state is “confirmed” without the deferred read-only owner-state gate.
3. Return any report that labels R8-R10 “fabricated” or “hallucination-confirmed” solely from Issue #278. The accepted phrasing is: unsupported in the inspected project corpus, owner decision pending.
4. Require A1 to preserve the distinction between a successful workflow, a successful sweep command, a successful Pages deployment, and a fresh public artifact.
5. Require AQ to independently verify the document-to-source mappings for TSR-05, TSR-06, TSR-15 through TSR-21, RRP-04 through RRP-07, and the legal-authority table before synthesis.

**A3 audit verdict:** **Partial.** The public-only provenance scope is complete for the 31 material claims above. Current private state, privacy acceptability, record-level fidelity, document-bundle provenance, and legal application remain explicitly gated rather than inferred.
