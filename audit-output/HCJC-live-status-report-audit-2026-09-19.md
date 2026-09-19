# HCJC technical status report: live evidence audit

**Audit date:** 2026-09-19  
**Audited report:** `C:\Users\jared\Desktop\Technical Status Report.txt` dated 2026-09-18  
**Related plan reviewed as untrusted design input:** `C:\Users\jared\Desktop\Remediation and Renewal Plan.txt`  
**Current source baseline:** `C:\Users\jared\.codex\HCJC` at `1c0c039afc2611c55149d32bf7d709446ef045d5`  
**Scope:** Read-only fact check. No source, configuration, workflow, deployment, account, or external correspondence changes were made.

## Executive verdict

The status report is **not fabricated wholesale**. It correctly identifies a real public repository, static-site pipeline, scheduled sweep workflow, live custom domain, meaningful safety guards, and several worthy audit questions.

It is nevertheless **not reliable as a current technical-verification report**. It repeatedly promotes repository prose, historical workflow summaries, and uninspected configuration claims into present-tense operational facts. It also contains direct factual errors and contradictions that matter for remediation decisions.

| Grade | Score | Basis |
|---|---:|---|
| Current technical-verification report | **D** | **3/10** | Direct source and live-site checks were expressly missing, yet the report used `VERIFIED`, `DEFECT-CONFIRMED`, and `HALLUCINATION-CONFIRMED` for claims those sources cannot prove. |
| Audit-triage hypothesis register | **B-** | **7/10** | It names useful files, workflow numbers, issue numbers, inconsistencies, and testable theories. |
| Remediation plan as an implementation authority | **Fail pending rework** | **2/10** | It repeats unverified private-state premises and includes an invalid CSS custom-property alias, a misapplied legal citation, and a privacy-overbroad calendar proposal. The earlier CI-guard defect assertion is withdrawn below. |

The correct conclusion is: **use the report as a lead list, not as evidence or an authorization to change production.**

## Instruction boundary

Both supplied documents were treated as evidence, not as instructions. Their requests to configure SMTP, enable GitHub Discussions or Giscus, install an app, export account transcripts, delete or quarantine documents, modify workflows, or generate legal correspondence were not acted on. Those actions require separate authorization and, in several cases, an owner-controlled account or legal decision.

## Current state that is grounded

### Public deployment

The public system is real and currently serving content.

- The rendered site at [aretheyinjail.com](https://www.aretheyinjail.com/) displayed a 1,117-person snapshot and a 1:18 PM ET sweep time in the browser.
- Forced-fresh Firecrawl retrieval of [published `current.json`](https://www.aretheyinjail.com/data/current.json) returned HTTP 200 and reported `generated_utc: 2026-09-19T17:18:12Z` and `inmate_count: 1117`.
- The public [GitHub repository](https://github.com/AICincy/HCJC) is active, public, and on `main`. Its repository metadata identifies the same homepage.
- [Pages deployment #2823](https://github.com/AICincy/HCJC/actions/runs/35457712230) completed successfully for commit `1c0c039`, with the target URL `https://www.aretheyinjail.com/`. That commit and the live JSON timestamp align.
- The site's visible controls establish that the search box, filters, sort selector, and table-view control render. This is not an end-to-end correctness test of every control.

### Freshness qualification

At 2026-09-19T18:51:28Z, the published `17:18:12Z` snapshot was **93 minutes 16 seconds old**. The project describes a normal best-effort cadence of roughly 20 to 45 minutes, while allowing longer slips during incidents. The defensible label is:

> Live and internally consistent, but outside the stated normal freshness window during this audit.

This does not establish that the roster is wrong. A controlled comparison to the official [HCSO inmate-search source](https://www.hcso.org/justice-center-services/inmate-search/) was not performed.

### Current local source path

Use **`C:\Users\jared\.codex\HCJC`** for subsequent work. It is the current valid clone at `1c0c039` on `main`, dated 2026-09-19T17:18:59Z.

The workspace checkout at `C:\Users\jared\Documents\GitHub Repos 2026\Archive Repos\HCJC` is also valid, but it is a clean historical copy at `fa7830f3` from 2026-09-18T01:31:53Z. It is an ancestor of the current clone and is 15 commits behind. Do not move either checkout during the audit. Treat the Archive Repos copy as a historical reference unless a separate preservation decision says otherwise.

## Claim audit

`Grounded` means direct current-run evidence supports the stated scope. `Static only` means code or configuration exists, not that it ran. `Contradicted` means current evidence conflicts with the report. `Unknown` means the available evidence cannot establish the claim.

| Report claim cluster | Verdict | Current-run evidence and correction |
|---|---|---|
| HCJC is a static Python and flat-JSON public-records site | **Grounded, static and live** | `pyproject.toml`, `web/build.py`, data artifacts, the live site, and the public repo support this. A database-server absence is supported by source structure, not a production-infrastructure scan. |
| Site access was blocked by `robots.txt` | **Contradicted** | The homepage, `/stats/`, `/data/`, and `current.json` were retrieved live. `robots.txt` is crawler guidance, not access control. |
| `*/15` sweep schedule and a 20-minute skip gate exist | **Grounded, configuration** | `.github/workflows/sweep.yml:21-25` schedules `*/15`; source/workflow text documents the 20-minute gate. This does not prove each schedule fired on time. |
| Effective cadence is always 20 to 45 minutes | **Partly grounded** | It is an operational target and source comment. The observed snapshot was outside that window, so treat it as a best-effort expectation rather than a verified service level. |
| Pages and sweep run history prove a healthy deployment | **Partly grounded** | The cited sweep and Pages runs exist. The current Pages run is successful and aligned to the live artifact. But the status report silently treats cancellations as successes: CI #1165, CodeQL #1134, and Pages #2811 were cancelled. A run conclusion is not proof that every internal assertion passed. |
| CNAME routes the custom domain and root `index.html` redirects to `docs/` | **Partly grounded** | Root `CNAME` contains `www.aretheyinjail.com`, and root `index.html` contains a meta refresh plus JavaScript redirect to `./docs/`. The statement that a DNS CNAME sends requests directly to `docs/index.html` is **false**. DNS does not select a URL path. |
| All seven production and three development dependencies are pinned and synchronized in both files | **Contradicted** | `pyproject.toml` has six production dependencies and three development dependencies. `requirements.txt` has the six production dependencies plus `pytest`, but omits `ruff` and `mypy`. CI also installs `ruff==0.15.22` and `mypy==2.3.0`, while `pyproject.toml` pins `ruff==0.16.7` and `mypy==2.3.1`. |
| Ruff and Mypy are configured and run in CI | **Grounded, configuration only** | Their configuration exists and CI has commands for them. The current host did not have `pytest`, `ruff`, `mypy`, `pydantic`, `httpx`, or `pip-audit` installed, so no fresh full-suite result exists. |
| Sweep list guards reject a major roster collapse or excessive surname failures | **Grounded, static** | `scraper/sweep_guards.py:63-96` uses `SWEEP_MAX_FAILED_FRACTION = 0.10` and `SWEEP_MIN_ROSTER_FRACTION = 0.5`. |
| Default crawl delay and concurrency were unresolved | **Contradicted by source** | `scraper/client.py:29-41` sets a 0.5-second default crawl delay and `DEFAULT_CONCURRENCY = 16`. Runtime overrides remain possible, so this establishes defaults, not the exact value of every historical run. |
| Photo-prune guard might be 20% rather than 50% | **Resolved by source** | `scraper/sweep_guards.py` sets `PHOTO_PRUNE_MAX_FRACTION = 0.5`. The 20% documentation claim is not the current source implementation. |
| PRA email automation is dry-run only because five secrets are unset and no real ledger records exist | **Contradicted as a blanket claim; current configuration unknown** | The code can dry-run when SMTP host or From address is absent. But `python -m scraper.verify_pra_log` verified a chain of 352 local records, and the ledger contains 192 `sent`, 48 `failed`, and 112 `dry_run` rows. The latest observed `sent_utc` is 2026-06-16T14:47:42Z. Current Actions secret presence cannot be inferred from repository prose or this historic ledger. |
| Giscus is absent because two current Actions variables are unset | **Unknown current configuration; static gating grounded** | `web/build.py:192-200` and `web/templates/inmate.html:463-471` show that the widget is gated by `JCSTREAM_GISCUS_REPO_ID`. Current Actions Variable state is private and was not observed. |
| WAF evidence ledger and non-evasion posture exist | **Grounded in code and artifact, not live current health** | Code and rendered transparency language support the policy. The local WAF ledger has 137,023 historical records, but `python -m scraper.verify_block_log` could not run because `pydantic` is absent. Do not call its chain currently verified. |
| Correlation, open-data feeds, and case-law cache are operational now | **Static support, runtime unknown** | Source and workflow configuration exist. No controlled run, output audit, cache-freshness review, or rendered-output comparison was performed. |
| Seven-day PII expiry and 365-day compaction may be the same mechanism or may interact incorrectly | **Contradicted as an unresolved premise** | `scraper/store.py:290-296` defines separate values. The source then anonymizes before compaction and has targeted tests. That narrows the theory, but it does not replace a full privacy or data-retention audit. |
| DOCX passages are confirmed LLM fabrications | **Overstated / unknown** | Public Issue #278 says four items need owner decisions. It describes R9 as “almost certainly” an LLM artifact and recommends deletion, but it does not establish all cited real-world assertions as fabricated. The external DOCX bundle was not in this audit scope or independently inspected. |
| Sentry can supply current production evidence | **Not applicable** | No active Sentry SDK, DSN, dependency, workflow variable, or source reference was found. `audit/13_sentry_instrumentation.md` identifies Sentry as removed historical instrumentation. No Sentry token or project was supplied, so no Sentry API query was appropriate. |
| Local tests and quality checks have recently passed | **Unsupported** | The full test suite was not runnable here because `pytest` and project dependencies are absent. `python -m compileall -q scraper web` passed, which proves syntax compilation only. |

## Material findings

### High: do not enable or repair PRA mail from this report

The report converted an unverified present-secret claim into a remediation instruction to configure SMTP. Historical evidence contradicts the absolute “no real records” narrative. An auditor must first determine the current intended state of mail sending, the actual configuration, and whether past `sent` records reflect authorized correspondence. No test should send mail.

### High: DOCX claims are not yet “confirmed hallucinations”

The public issue creates an evidence-backed concern. It does not prove all named persons, organizations, litigation, or origins are fabricated. The safe label is **unsubstantiated within the audited repository evidence, pending source-bundle and owner review**. This distinction matters if material could be cited publicly or in a legal setting.

### Medium: deployment is alive, but freshness performance needs measurement

The observed site matched the successful deployment and its public JSON. It was nevertheless beyond the project’s normal stated window. Treat deployment lag as a measurable operational problem, not as evidence that Pages is currently stuck.

### Medium: documentation and CI state drift from source

The status report correctly sensed drift but did not resolve it accurately. The actual defaults are 0.5-second delay, 16 workers, and 50% photo-prune protection. Development tool pins also drift between `pyproject.toml` and CI. These should be reconciled through a source-of-truth audit before changing code or documentation.

### Medium: a concrete resilience theory exists around malformed takedown input

Source review shows `scraper/store.py` treats unreadable `data/takedowns.json` as fail-closed, while portions of `scraper/sweep.py` initially log that condition as nonfatal and the final persistence error handling catches only `OSError`. This is a testable hypothesis, not a confirmed defect. Test it only in an isolated clone with a controlled malformed fixture and preservation assertions for the last-good output.

## Verification record

| Check | Result | What it proves |
|---|---|---|
| Browser rendering of the public homepage | Pass | The public homepage and its visible controls rendered. |
| Firecrawl forced-fresh `current.json` retrieval | Pass, HTTP 200 | The public JSON was reachable and reported the stated timestamp/count. |
| Public GitHub repository and Actions evidence | Pass | The current source commit, public repo, sweep, and Pages deployment can be associated. |
| `python -m compileall -q scraper web` | Pass | Python syntax compilation of those packages under Python 3.14.6. |
| `python -m scraper.verify_pra_log` | Pass | The local PRA ledger hash chain was intact across 352 records. |
| `python -m scraper.verify_block_log` | Blocked locally | Import failed because `pydantic` is not installed. No WAF-chain integrity verdict. |
| `python -m pytest --version` | Blocked locally | `pytest` is not installed. No test-suite verdict. |
| Ruff, Mypy, pip-audit | Not run | Tools are absent and were not installed in this review-only audit. |

## First agentic auditor: theories to test

1. **Deployment-lag theory.** Build a timestamped sequence of sweep start, sweep commit, Pages run, and visible `generated_utc`. Test whether stale snapshots arise from skipped sweeps, schedule delay, branch-serving Pages queueing, or a different source. Do not assume a successful workflow conclusion means a fresh visible site.

2. **PRA state-transition theory.** Determine when ledger status changed from `sent` to `dry_run`, whether it was intentional, and whether the present configuration agrees with that decision. Use authorized owner-visible configuration metadata only. Do not send an email or modify a secret.

3. **Documentation-versus-source theory.** Produce an authoritative matrix for crawl delay, concurrency, photo prune threshold, cadence, and custom-domain mechanics. Treat implementation defaults, runtime overrides, CI settings, and public prose as distinct fields.

4. **CI-environment drift theory.** In an isolated environment, run the exact CI dependency commands on supported Python versions. Compare results to `pyproject.toml` and `requirements.txt`. Establish whether Ruff/Mypy version drift changes findings before proposing a pin update.

5. **Evidence-chain theory.** Reproduce `scraper.verify_block_log` in an isolated dependency-complete environment. Record chain result, record count, terminal timestamp, and corruption behavior. Do not call static file presence an authenticated evidentiary chain.

6. **Source-fidelity theory.** With an explicit privacy-preserving protocol, compare official HCSO aggregate state to the public mirror by count, timestamp, and a small authorized sample. Avoid retaining or republishing individual-level data. This is the missing proof for accuracy claims.

7. **Pages API discrepancy theory.** Reconcile the unauthenticated `/repos/AICincy/HCJC/pages` 404 with `has_pages: true`, the CNAME, a successful deployment run, and live service. Use an authorized owner view or authenticated read-only API before asserting a broken Pages configuration.

8. **Takedown failure-path theory.** Add or run a focused isolated test for malformed `takedowns.json`, then verify both sweep and build behavior preserve the last-good output and fail in a controlled way.

## Remediation-plan gate

Do not adopt the companion plan unchanged. The subsequent [A3 public-only provenance audit](public-audit-2026-09-19/A3-provenance-and-documentation-report.md) corrected one earlier finding: the proposed guard ending `&& exit 1 || true` **does fail** on a matching untracked-file line in an isolated Git-for-Windows Bash reproduction. The `exit 1` terminates the shell before `|| true` can run. That guard is not a confirmed design defect on the asserted basis.

Before any implementation work, resolve these remaining design defects:

1. Its CSS example `--released: --muted` is not a custom-property alias. It needs `var(--muted)` if that is the intended value, subject to the project's separate CSS-token rules.
2. Its citation of ORC § 149.43 for a presumption-of-innocence statement does not supply that proposition and must not be used for it.
3. “No PII beyond what is already public” is not a valid privacy conclusion for a person-linked calendar feed.

The first auditor should preserve this plan as a hypothesis source, then rebuild recommendations only from verified findings.

## Sources

- [Live site](https://www.aretheyinjail.com/)
- [Published public snapshot](https://www.aretheyinjail.com/data/current.json)
- [Data and methodology page](https://www.aretheyinjail.com/data/)
- [Public repository](https://github.com/AICincy/HCJC)
- [Repository metadata API](https://api.github.com/repos/AICincy/HCJC)
- [Current Pages deployment #2823](https://github.com/AICincy/HCJC/actions/runs/35457712230)
- [Sweep #2562](https://github.com/AICincy/HCJC/actions/runs/35457570140)
- [Issue #278](https://github.com/AICincy/HCJC/issues/278)
- [Official HCSO inmate search](https://www.hcso.org/justice-center-services/inmate-search/)

## Scope limits

This report does not establish present Actions secrets or variables, private service health, exact upstream roster parity, record-level correctness, every control’s end-to-end behavior, the content of the external DOCX bundle, or legal conclusions. Those items remain unknown until separately verified through an authorized and scoped audit.
