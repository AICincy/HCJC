# HCJC agentic audit team charter

**Prepared:** 2026-09-19  
**Controlling evidence baseline:** [HCJC live status-report audit](HCJC-live-status-report-audit-2026-09-19.md)  
**Purpose:** Build a bounded, evidence-governed team to test the unresolved HCJC theories without changing HCJC, its deployment, accounts, or public records.

## Decision and authority boundary

This charter creates the audit structure and report contract. It does **not** dispatch a production change, activate an account integration, authorize access to private configuration, send mail, publish a correction, or make a legal conclusion.

The 2026-09-19 status-report audit is a lead list, not permanent proof. At audit launch, A0 must make a fresh isolated clone, record the remote commit SHA and UTC audit clock, and freeze that baseline for the phase. The current local source directory, `C:\Users\jared\.codex\HCJC`, is the correct reference checkout but remains untouched. Executable source tests run only in disposable clones or worktrees.

Every audit action is read-only outside its isolated fixture or clone. No report may contain raw person-level jail data, secret values, session material, personal correspondence, or unnecessary identifiers.

## Team topology

The team has one coordinator, six specialists, and one independent adversarial reviewer. With four available execution slots, the coordinator runs at most three specialists concurrently. This keeps a slot available for evidence registration, contradiction resolution, and recovery.

| ID | Role | Specific duty | Required output | Stops when | Strict boundary |
|---|---|---|---|---|---|
| A0 | Audit coordinator and evidence registrar | Freezes the baseline, issues work cards, assigns claim IDs, maintains the evidence register, deduplicates findings, and resolves contradictions by source strength. | Baseline manifest, claim registry, dependency graph, contradiction register, report-intake decisions. | Every assigned role has one bounded theory, evidence scope, privacy boundary, and completion rule. | Does not turn majority opinion into fact, self-certify a High finding, repair HCJC, or alter production. |
| A1 | Deployment and freshness auditor | Tests the deployment-lag and Pages-discrepancy theories by correlating scheduled sweeps, commits, Pages runs, published `generated_utc`, and rendered site state. | UTC timeline across three completed scheduled cycles or a 24-hour observation ceiling, with measured deltas and a freshness verdict. | Three complete sequences are measured, or a precise observation blocker is recorded. | Public read-only evidence only. A successful workflow is not proof of a fresh or accurate public roster. |
| A2 | Source and CI reproducibility auditor | Reproduces declared CI behavior in isolated supported environments. Reconciles `pyproject.toml`, `requirements.txt`, workflow pins, tool versions, and check results. | Requirement-to-evidence matrix, dependency-drift matrix, exact commands, environment versions, exit statuses, and failure classification. | Every declared CI check is passed, failed, or specifically blocked on each supported Python version. | Does not modify dependencies, pins, workflows, lockfiles, or the active checkout. A local environment failure is not automatically a source defect. |
| A3 | Documentation and provenance auditor | Resolves source-versus-documentation drift and audits the status report, remediation plan, public issue claims, supplied DOCX material if authorized, and legal propositions against actual authorities. | Atomic source-to-claim matrix with one claim status per row, stable locators, source hierarchy, and provenance verdicts. | Each scoped claim has exactly one source status and its search scope is recorded. | “Not found” is not “fabricated.” No deletion, public correction, legal correspondence, or legal conclusion. |
| A4 | Evidence-chain and resilience auditor | Verifies WAF and PRA evidence chains in a dependency-complete disposable environment. Tests malformed takedown input and last-good-output preservation with synthetic fixtures. | Chain-integrity summary, aggregate counts and terminal timestamps, controlled-corruption matrix, failure-path matrix, and preservation result. | Every defined verifier and synthetic failure fixture runs, or a precise environment blocker is recorded. | No raw ledger records in reports. No production data rewrite, live takedown file, or remediation. An isolated test is not a live resilience claim. |
| A5 | PRA and owner-state auditor | Separates historical PRA ledger evidence from current intended mail state. Reconciles owner-authorized read-only metadata for Actions configuration, Giscus gating, and Pages configuration. | Scrubbed state-transition timeline, configuration-boundary matrix, and explicit unknowns or owner gate. | Historic state is traced and current state is directly confirmed or retained as unknown. | Requires owner-authorized read-only metadata for private state. Never reads secret values, sends email, changes secrets, enables Giscus, or changes Pages/DNS. |
| A6 | Source-fidelity and privacy auditor | Tests public-mirror timeliness and aggregate accuracy against the official HCSO source under an approved aggregate-first privacy protocol. | Privacy checklist, redaction record, aggregate comparison table with timestamps, counts, and deltas, plus limited authorized sample results if permitted. | Three protocol-compliant matched comparisons occur, or the role is human-gated. | Cannot begin person-linked comparison work without the privacy protocol and explicit authorization. Matching counts do not prove record-level accuracy. |
| AQ | Independent adversarial reviewer | Challenges every High or Critical conclusion and selected disputed Medium conclusion through a blind first review, alternate evidence route, and report-hygiene check. | Replication record, rebuttal memo, accepted/disputed finding list, and report decision: accept, return for correction, or human-gated. | Every submitted report is accepted, returned and corrected, or explicitly gated. | Cannot validate its own primary finding, silently repair another report, or accept a conclusion because multiple agents repeat it. |

## First auditor and launch sequence

**First dispatch: A1, the deployment and freshness auditor.** Its neutral question is: *Across three complete scheduled cycles, what measured interval separates sweep start, source commit, Pages completion, public `generated_utc`, and the rendered public timestamp?*

This starts with public non-invasive evidence and determines whether later freshness concerns belong to the scraper, scheduler, Pages queue, branch-serving configuration, or the observation method. It does not assume the roster is wrong.

| Phase | Roles | Work | Gate to advance |
|---|---|---|---|
| 0. Custody setup | A0 | Fresh isolated baseline, source manifest, claim registry, work cards, privacy rules, and evidence ledger. | Baseline SHA and UTC are frozen. Each role has a falsifiable question and stop condition. |
| 1. Independent first-pass evidence | A1, A2, A3 in parallel | Public deployment timeline, CI reproducibility, and provenance/source drift. | A0 reconciles source identity and prevents cross-role conclusions from contaminating first passes. |
| 2. Controlled deeper verification | A4, A5 | Isolated ledger and failure-path testing. Owner-state review only if read-only access is authorized. | A0 classifies results as direct evidence, environment limitation, or unresolved. |
| 3. Privacy-gated fidelity review | A6 | Aggregate-first official-source comparison. | A6 begins only after an explicit privacy and retention protocol is approved. |
| 4. Adversarial review and packet assembly | AQ, A0 | Independent replication, contradiction handling, report acceptance, and final audit packet. | All reports are accepted, corrected and rechecked, or surfaced as human-gated. |

The audit uses waves, not a free-form swarm. No duplicate investigator is launched unless the second assignment is an intentional independent verification pass.

## Mandatory auditor work card

Before each assignment, A0 issues this complete work card:

```text
Role ID:
Claim ID:
Neutral, falsifiable proposition:
Why it matters:
Frozen baseline and target identity:
UTC observation window:
Allowed evidence and access level:
Forbidden actions:
Acceptance criteria:
Falsifier:
Evidence required:
Privacy and retention boundary:
Human-only gate:
Stop condition:
```

The card carries the question, not the anticipated answer. Primary auditors do not receive another auditor's conclusion before their initial evidence packet is complete.

## Common report contract

Every auditor report must contain:

1. A one-sentence audit question and defined completion condition.
2. Frozen SHA, repository or target identity, UTC observation window, access level, interpreter and dependency versions where relevant.
3. A `requirement or risk -> observable behavior -> evidence -> result -> gap` matrix.
4. Exact command, test method, response status, exit status, or stable source locator for each material result.
5. An evidence grade and a separate audit verdict for each material claim.
6. Atomic claim rows with one permitted claim-source status, not blended prose.
7. Failure classification, known gaps, blocked routes, and actions deliberately not taken.
8. A smallest safe next test or remediation direction, without implementing it.
9. A compact execution trail with observable action, UTC result, and non-sensitive note only.

Each claim row uses exactly one source-audit status:

| Source-audit status | Required basis |
|---|---|
| `verified` | Exact or faithful source support with stable source locator. |
| `verified in broader bundle` | Supporting source is outside the narrow packet but inside the authorized broader scope, with locator and scope note. |
| `conflicting` | Side-by-side claim and source language establish a material contradiction. |
| `not found in searched sources` | The complete searched scope is named. It does not establish falsehood. |
| `manual review needed` | Every safe extraction route attempted is stated and the remaining ambiguity is real. |

Each technical result separately uses one audit verdict: `Pass`, `Partial`, `Fail`, or `Inconclusive`. Claim-source status and technical verdict answer different questions and never substitute for one another.

## Evidence strength and permitted conclusions

| Grade | Evidence type | What it can establish |
|---|---|---|
| A | Fresh direct observation in the required environment with UTC time, target identity, and reproducible observation. | Current behavior within the observed scope. |
| B | Executed public-boundary behavior or owner-authorized read-only metadata tied to the frozen baseline. | Operational behavior or configuration state within the observed scope. |
| C | Independent contract or integration evidence in an identified isolated environment. | Controlled integration behavior, not public production health. |
| D | Unit, property, or controlled failure-injection result. | Behavior of the tested component or fixture. |
| E | Static source, configuration, workflow, or artifact inspection at the frozen commit. | Implementation or configuration existence, not runtime execution. |
| F | Documentation, historical issue text, prior report, or unsupported assertion. | A lead or hypothesis only. |
| X | Private, inaccessible, conflicting, or otherwise unobservable state. | Nothing beyond `Unknown` or a human gate. |

For a High or Critical finding, require either one Grade A or B reproduction plus independent corroboration, or two independent direct paths that converge. A Medium finding requires Grade C or stronger. Grade D through F material is a theory, documentation-drift observation, or test target, not an operational defect.

The team may never infer current secret presence, current variable state, owner intent, live roster accuracy, or successful external delivery from static source, historical artifacts, or a previous report.

## Quality assurance and independence controls

| Control | Required practice | Assurance effect |
|---|---|---|
| Frozen baseline | A0 refreshes and records a remote SHA before each audit phase. No fetch, rebase, or source mutation inside that phase. | Prevents cached or moving repository state from becoming evidence. |
| Isolated execution | Source tests use disposable clones or worktrees and synthetic fixtures. Each report records its environment and post-test diff. | Prevents test output from contaminating the active checkout or another auditor's result. |
| Blind first pass | Primary auditor gets the claim and evidence rules, not an expected conclusion. | Reduces confirmation bias and consensus-by-copying. |
| Independent replication | AQ uses a different auditor and an alternate route where possible: browser versus direct fetch, public workflow versus published artifact, source locator versus isolated execution. | Tests whether a conclusion survives independent observation. |
| Reproduction packet | Each material result identifies baseline, inputs or non-identifying hash, exact steps, environment, outputs, cleanup method, and limits. | Makes a claim testable instead of merely persuasive. |
| Failure classification | Every failed check is classified as implementation defect, test defect, environment limitation, flaky result, pre-existing failure, or unresolved. | Stops environment gaps from becoming product verdicts. |
| Evidence hierarchy | Direct observation outranks public-boundary behavior; public-boundary behavior outranks isolated integration; integration outranks static source; static source outranks prose. | Prevents weak evidence from being upgraded by repetition or vote. |
| Report intake | A0 accepts, returns, or human-gates every report before it reaches synthesis. | Keeps unsupported certainty out of the final packet. |
| Adversarial gate | AQ challenges High, Critical, and outcome-changing claims. | Makes challenge a required stage, not an optional opinion. |
| Privacy review | A0 rejects identifiers, raw person-level data, secret values, and unnecessary screenshots or logs. | Preserves the project’s public-records and privacy boundary. |

AQ specifically tests for stale timestamps, caches, wrong branch or clone, source existence mistaken for runtime behavior, private state inferred from historic artifacts, cancelled or partial workflows hidden by a success claim, invalid test oracles, unsafe fixtures, scope creep, and remediation proposals disguised as audit conclusions.

## Report rejection rules

A0 returns a report for correction if it:

- lacks a frozen baseline, target identity, UTC observation time, or relevant environment identity;
- calls a live fact `verified`, `healthy`, `current`, or `fabricated` based only on source, workflow prose, a historical issue, or another report;
- treats source silence as a contradiction or `not found` as fabrication;
- infers current private configuration, secrets, or intent without owner-authorized direct evidence;
- omits a failed command, repeats a check until green without recording the earlier result, or treats an environment limitation as a product pass or failure;
- contains raw person-level jail data, credentials, personal-session material, unredacted ledgers, or unnecessary identifiers;
- conflates static configuration, isolated behavior, public deployment behavior, and private production state;
- resolves a material contradiction by majority opinion rather than evidence strength;
- performs or proposes a remediation outside the assigned audit scope; or
- lacks independent review for a High or Critical conclusion.

## Retry, preservation, and anti-churn rule

Before repeating a measurement, test, review, or retrieval, A0 checks whether accepted evidence already covers the same frozen SHA, target, requirement, evaluator, and environment. Equivalent accepted evidence is reused. A new execution requires a typed reason such as a changed baseline, changed target, changed environment, transient execution failure, or corrupted prior evidence.

Auditors do not retry until green. They record the initial result and the reason for any permitted alternate route or repaired rerun. If a phase receives a second adversarial result that fails its stated acceptance criteria, A0 stops that phase, preserves its evidence and unresolved items, and does not carry the phase forward as settled. The next audit phase may continue only when it does not depend on the unresolved conclusion or after the user changes scope.

## Human-only gates

| Gate | Required before proceeding | Not authorized by this charter |
|---|---|---|
| Private Actions, Pages, or Giscus state | Owner-authorized, read-only metadata view. | Secret values, changes to settings, enabling services, or account ownership actions. |
| PRA current delivery state | Owner confirmation of intended state and authorized read-only configuration metadata. | Sending test mail, configuring SMTP, altering secrets, or contacting recipients. |
| Official-source fidelity comparison | A written aggregate-first privacy and retention protocol plus explicit authorization. | Retaining or publishing person-linked comparison material or treating a count match as record-level proof. |
| Legal or public claims | Primary authority review and the user's instruction for the final use. | Legal conclusion, public correction, demand, or external correspondence. |
| Remediation | An accepted audit packet and a separate, specific implementation request. | Automatic code, workflow, data, deployment, or documentation changes. |

## Final synthesis packet and discussion

Once all reports are accepted, corrected and rechecked, or properly human-gated, A0 assembles one decision packet:

1. Frozen-baseline and source manifest.
2. Accepted auditor reports and their reproduction packets.
3. Claim and evidence register with grades and source status.
4. Contradiction register and unresolved-claim list.
5. Redaction and privacy record.
6. Adversarial replication results.
7. Ranked decisions with evidence, uncertainty, risk of acting or not acting, and the exact owner decision needed.

At that point, the review with you is an open decision discussion, not an automatic remediation handoff. We will discuss each decision on its actual evidence, its remaining uncertainty, and the consequence of acting or leaving it unchanged. Nothing external happens unless you separately authorize it.
