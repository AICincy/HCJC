# AICINCY scope determination (Phase 5, E2)

**Assessed:** 2026-09-23T03:24Z by direct GitHub API enumeration of the organization.
**Question the brief posed:** does `AICINCY` name a second repository alongside `HCJC`, or is it the organization?
**Answer:** the organization reading is correct, and Phases 1 through 4 covered the entire CI/CD surface of that organization for this release. The scan also surfaced one org-scope item the brief's binary branch had no room for. Determination and caveat below, each from a command that was run.

## Determination

```
AICINCY SCOPE DETERMINATION
  Determination: SCOPE-CLARIFIED - single repository in release scope
  Organization: AICincy (https://github.com/AICincy)
  Repository in scope: HCJC (https://github.com/AICincy/HCJC)
  Evidence:
    - gh api repos/AICincy/AICINCY -> {"status":"404"} ; no repository of that name exists
    - CI run 35809118882 resolves under https://github.com/AICincy/HCJC/actions/runs/35809118882
    - remote origin of this checkout = https://github.com/AICincy/HCJC.git
  Second repository named AICINCY: NONE
  Effect on the Phase 1-4 architecture: NONE; the HCJC gate work is the full release scope
  Future reference rule: "AICINCY/HCJC" in this project means https://github.com/AICincy/HCJC.
    It is not shorthand for a second codebase, and it does not by itself open an audit of the
    other organization repositories.
```

Form B was not produced: there is no second repository to audit for release-gate purposes. No AICINCY Phase 1 entry prompt follows from this package.

## Why the binary branch was the wrong shape

The brief allowed two outcomes: single repository, or a second repository requiring its own Phase 1. The literal reading of the original task ("AICINCY/HCJC CI/CD workflows") has a third: *the organization as the audit target*, in which case every repo under `AICincy` with CI/CD is in scope. That reading is not hypothetical, so the org was enumerated rather than assumed.

Organization inventory, 11 repositories, checked for workflows, Pages config, and a root `CNAME`:

| Repo | Workflows | Pages | Root CNAME | In release scope |
| :-- | :-- | :-- | :-- | :-- |
| `HCJC` | 9 (ci, pages, sweep, rebuild, codeql, live-parity, archive-evidence, clerk_pra_packets, ingest_case_data, refresh_caselaw) | `built`, cname `www.aretheyinjail.com`, legacy branch source `main/docs` | none | **Yes** |
| `AAI-HCJC-v2` | **none** (`.github/workflows` returns 404; no `.github` at all) | `status=null`, `cname=null`, `build_type=workflow` | **`www.aretheyinjail.com`** | No, but see SCOPE-001 |
| `Amex` | 4 (guard-public-copy, lint-yaml, publish-release, validate-automod) | none | none | No |
| `AAI-HCJC`, `AAI-Agentic`, `AAI-Metro-PRR`, `metro-prr`, `OPRA-Codex`, `Sniffies`, `Sniffies-AAI`, `webapp-conversation` | none | none | none | No |

The org-scope reading adds exactly two CI/CD-bearing repositories to the universe: `HCJC` and `Amex`. `Amex` is an unrelated Reddit moderation project with no shared infrastructure with the jail roster site, so it does not belong in a release gate for `aretheyinjail.com`. Under either reading, the release scope is `HCJC` alone. That is the descope rationale the gap asked for, stated in the affirmative rather than left implied.

## SCOPE-001: a duplicate holds an inert claim on the production domain

`AICincy/AAI-HCJC-v2` is a copy of this project, not an unrelated repo:

| Field | Value |
| :-- | :-- |
| Created / last pushed | `2026-09-18T05:16:52Z` / `2026-09-18T05:24:02Z`, two commits (`Initial commit`, `v2`) |
| Contents | `HAMCO`, `audit`, `data`, `design`, `docs`, `docs-reference`, `scraper`, `scripts`, `tests`, `web`, plus `wiki`. A snapshot of the same tree |
| `.github` | absent, so no CI, no security scanning, no sweep |
| Root `CNAME` | contains `www.aretheyinjail.com` |
| Pages | `status=null`, `cname=null`, `html_url=https://aicincy.github.io/AAI-HCJC-v2/`, `build_type=workflow` |
| Fork? | `fork=false`; it is not linked to `HCJC` as a parent, so nothing propagates automatically |

Consequence, stated precisely: the custom domain is **registered to `HCJC`** (its Pages record holds `cname=www.aretheyinjail.com`, `protected_domain_state=verified`, certificate approved through `2026-12-07`), so `AAI-HCJC-v2` is not serving or intercepting traffic today. Its `CNAME` file is inert because that repo has no deployment workflow and no attached domain.

The residual risk is one workflow away, not zero. A `CNAME` present in an uploaded Pages artifact causes `actions/deploy-pages` to request the custom domain for that repository. Anyone who adds a Pages workflow to `AAI-HCJC-v2`, or copies `HCJC`'s `pages.yml` into it, would put two repositories in contention for `www.aretheyinjail.com`. That is a production-availability event for a live roster site, arriving from an unmonitored, unscanned, un-swept copy that has no CI to catch it.

**Determination on SCOPE-001:** `DEFERRED-TO-OWNER-DECISION`. E2 does not archive, delete, or edit a repository outside this one, and no agent in any phase should. Three options for the named owner, in the order that costs least:

1. Delete the root `CNAME` from `AAI-HCJC-v2`. Removes the domain contention path; keeps the snapshot.
2. Archive the repository on GitHub (read-only, no pushes). Also removes the CI-gap hazard.
3. Leave as is, accepting that an unmanaged copy carries a live-domain claim.

This is not a gate. It does not block Gates A through E, and no C-processor consumes it. It is recorded here so the scope question closes with a reason instead of silence, and so a future reader does not reopen it.

## Closure statement on Gap 1

Gap 1 was real: AICINCY had never been addressed or descoped in writing. It is now both. `HCJC` is the full release scope, with evidence; `AICincy/AAI-HCJC-v2` is characterized as an unmanaged snapshot with an inert production-domain claim and one owner decision attached to it. AICINCY is no longer uncharacterized.
