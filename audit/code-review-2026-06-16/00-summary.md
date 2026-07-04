# HCJC Code Review -- 2026-06-16
_aretheyinjail.com | Five-lane automated review | Lead synthesis_

## Non-negotiable constraints: status

All five reviewers confirmed the following:

| Constraint | Status |
|---|---|
| WAF evasion code present | None found. Blocks are logged only. JCSTREAM_HTTP_PROXY is documented as deliberately unset. |
| 107 empty booking photos altered or "fixed" | Not altered. Parser skips empty-payload base64 correctly. No downstream code fills them. |
| One-source principle (inmate records) | Adhered for public pages. One question item below (dispatch_correlations.json). |
| Fabricated citations | None found. ORC and FCRA citations verified accurate. Mandamus draft uses [VERIFY] tags. |
| Session IDs present in repo | Resolved: now documented in the CLAUDE.md Chain-of-Custody table and the `audit/sessions/` ledger (transcripts still unfiled). See Critical finding below. |

## Finding distribution

| Lane | Critical | High | Medium | Low | Info | Total |
|---|---|---|---|---|---|---|
| scraper-integrity | 0 | 1 | 3 | 2 | 8 | 14 |
| legal-evidentiary | 1 | 0 | 3 | 1 | 9 | 14 |
| templates-build | 0 | 3 | 5 | 5 | 3 | 16 |
| federal-docket-css | 0 | 4 | 5 | 3 | 2 | 14 |
| repo-hygiene | 0 | 2 | 3 | 3 | 4 | 12 |
| **Total** | **1** | **10** | **19** | **14** | **26** | **70** |

## Critical

### [legal-evidentiary] Court-evidence session IDs not in this repository

**Status (updated 2026-07-04): RESOLVED for the IDs, PARTIAL for transcripts.**
The session IDs are now recorded in the CLAUDE.md Chain-of-Custody table and the
`audit/sessions/` ledger, so the repository documents the location of record.
The residual open item is that the transcripts themselves are not yet filed in
`audit/sessions/` (see `audit/sessions/README.md`).

The four session IDs designated as court evidence (session_01Hbc6p9EspF6RH9ajNNb8tB, session_01MNnYgZMY5uFz9cHie3w6TY, session_019fDevbfpgmnjJP7A343T95, session_01NGMSLESEepbgV8aSn4reVG) do not appear anywhere in this repository, including CLAUDE.md. They may be held in claude.ai session history or an external transcript archive. If so, that storage location is not documented in the repo.

The risk is not that the IDs were deleted from this repo. The risk is that any court submission citing these IDs as evidence of Claude-assisted work cannot point to this repository as the location of record. The repo cannot attest to their preservation.

Action: Identify the authoritative storage location. Add a cross-reference paragraph to CLAUDE.md naming that location and the date range of each session.

## High findings (10 total)

### FCRA compliance (scraper-integrity)
Sweep cadence is 20-45 minutes effective. CLAUDE.md acknowledges it can slip past one hour during GitHub Actions congestion. No fallback mechanism accelerates removal when the cron slips. An inmate who leaves HCSO's roster could remain on the public site for 45+ minutes, exceeding FCRA 30-minute removal. Removal logic correct at normal cadence; gap is absence of monitoring alert or secondary trigger.

### Accessibility: three WCAG AA failures (templates-build)
| Finding | Location | Ratio | Threshold |
|---|---|---|---|
| --fg-muted (#6c6c6c on #F5F0EB) | Booking numbers, charge counts, filter labels at 11-12px | ~4.0:1 | 4.5:1 |
| .court-stat-primary label (rgba(255,255,255,0.78) on red/blue gradient) | Court calendar hero tile | ~2.7-2.9:1 | 3:1 (large text) |
| alt="" on booking photos in statute.html and court.html card links | Card navigation anchors | Screen reader sees no photo cue | WCAG 1.1.1 |

### Federal Docket palette: all three primary values off-spec (federal-docket-css)
| Token | Deployed | Spec | Gap |
|---|---|---|---|
| --bg | #F5F0EB | #fafafa | Warm off-white |
| --fg | #1A1A1A | #000000 | Near-black not true black |
| --accent | #B33A2A | #b30000 | Brownish-red; hue ~9 degrees off |

Additionally, .court-stat-primary and .visit-card-primary use a linear-gradient to #2c41a8 (cobalt blue). These are the two visually dominant hero tiles on the court and visit pages. Cobalt blue does not appear in the Federal Docket spec.

### CI/workflow permissions (repo-hygiene)
sweep.yml holds pages: write and id-token: write at the workflow level. Deploy-pages steps that required them are fully commented out. Current code path (commit-to-branch) needs neither. Any compromise of the sweep job gains unnecessary OIDC token capability and Pages write access.

pra_daily.yml holds contents: write on every run. The commit step is legitimate when SMTP is configured but is dead code on unconfigured repos. The write permission is idle and unnecessary in that state.

## Medium findings: top items

**dispatch_correlations.json is a cross-source public join (scraper-integrity).** scraper/correlate.py joins HCSO inmate records against Cincinnati Open Data CFS rows by inference (temporal and textual signals) and commits the output to data/dispatch_correlations.json. This file is publicly served. HCSO does not publish a dispatch correlation for any inmate. The one-source principle says publish nothing HCSO does not publish. File may need to move off the public-served path. Lead elevates this from Medium to High.

**Per-inmate detail-page WAF blocks not in the durable evidence log (legal-evidentiary).** List-page WAF blocks are committed to data/waf_block_log.json with the hash chain. Individual inmate detail-page WAF blocks are logged at WARNING level only, ephemeral in GitHub Actions. If WAF is selectively blocking specific inmate detail pages, that pattern is not in the durable evidence log.

**Empty-payload base64 photo skips generate no log entry (legal-evidentiary).** When the parser skips an empty-payload photo, it increments a counter but emits no log message. If litigation requires affirmative proof that the scraper observed a specific inmate's photo as empty on a specific sweep, the only available evidence is absence of a file. A timestamped INFO-level log entry at the skip point would provide that affirmative record.

**ruff version mismatch between ci.yml and pyproject.toml (repo-hygiene).** ci.yml installs ruff==0.15.15; pyproject.toml lists ruff==0.15.16. Lint results not reproducible between local development and CI.

**Build wipes docs/ before any render failure (templates-build).** web/build.py calls shutil.rmtree(out_dir) before rendering begins. A render exception produces total site absence until next successful sweep (up to 15 minutes), rather than stale data. Atomic swap via temp directory would eliminate this window.

## Cross-lane observations

Two findings appear independently in two lanes and reinforce each other:

- --fg-muted (#6c6c6c) on the warm cream background fails WCAG AA in both templates-build (contrast ratio) and federal-docket-css (off-spec palette). A single fix corrects both: change --fg-muted to #5c5c5c and --bg to #fafafa.
- The .court-stat-primary gradient tile fails WCAG AA on label contrast (templates-build) and uses the off-spec cobalt-blue endpoint (federal-docket-css). Flattening it to var(--accent) corrects both issues simultaneously.

## Lane reports

Individual lane reports were generated by the agent team but archived externally. This summary is the canonical reference for remediation work.
