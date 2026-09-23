# Gate D failure path (Phase 5, E3)

**Built:** 2026-09-23T03:40Z, anchored to commit `d9ba0678`.
**Gap 3 confirmed.** The architecture authorizes deployment and stops. Nothing defines what happens when the thing after Gate D fails. The record proves the concern is not theoretical: `audit/24_pages_deploy_stale_incidents.md` documents a stuck deploy that ran 110 minutes past its 90-minute alarm threshold and was resolved by waiting, with no defined owner, and `closure/README.md:116` shows LIVE-D still blocked at the time of writing.

This document defines the path. It authorizes nothing. Rollback is a human-only gate with the same structure as Gate D.

## What the repository already provides

Phase 5 does not invent detection, an incident channel, or a runbook. It routes to what exists.

| Mechanism | Where | What it catches | Latency |
| :-- | :-- | :-- | :-- |
| `verify_public_data.py` | `pages.yml` "Verify publication contract", pre-deploy | local build's published-JSON contract | pre-deploy only |
| `verify_live_url_parity.py` | `pages.yml` "Verify live URL compatibility", pre-deploy | new build against what is **currently live** | pre-deploy only |
| `scripts/verify_live_url_parity.py` | `live-parity.yml`, cron `40 4 * * 1` plus dispatch | live site serving every manifest JSON path | weekly, or on demand |
| `scraper/deploy_alert.py` | `sweep.yml` "Deploy staleness alarm", `if: always()` | live `generated_utc` lagging `main` past `DEPLOY_STALE_ALARM_MINUTES = 90`; emits `::error` and opens a deduped issue | hourly, on every sweep |
| `scraper/freeze_alert.py` | `sweep.yml` "Roster freeze alarm" | source data frozen, the opposite failure | hourly |
| `rebuild-site` workflow | `rebuild.yml`, dispatch only | republish `docs/` from current tree without scraping | on demand |

**The structural hole those mechanisms leave, stated exactly:** both `pages.yml` checks run *before* the deploy, and the pre-deploy parity check compares the new build to the *currently live* site. A build that is internally valid but wrong in a way the live site cannot detect (broken search UX, a regressed table, a bad template) passes both checks and deploys. Post-deploy correctness is then covered only by the next sweep's `deploy_alert` (staleness, not accuracy) and a weekly `live-parity`. **Nothing verifies that the newly deployed UI still works.** That is the gap E3 closes, and it is a detection gap as much as a response gap.

One further consequence: `verify_live_url_parity.py` returns 0 in recovery mode when every manifest path 404s on live, by design, so that a broken live state never blocks the deploy that would fix it. So the pre-deploy gate cannot stop a deploy into a broken production state. Post-deploy verification is the only catcher.

## Failure classes

```
CLASS 1: DEPLOYMENT-LEVEL. The Pages deployment does not land.
  Detection: pages.yml or pages-build-deployment conclusion=failure, or the live
    generated_utc lags main past 90 min (deploy_alert), or an open
    "Site deploy is stale: live roster lags main" issue.
  First read of the runbook: CLAUDE.md, "Pages deploy stuck in deployment_queued".
    GitHub-side queueing is intermittent and self-heals on the next push. The
    documented instruction is not to chase it; investigate only when the live
    Generated timestamp lags main by more than two sweep cycles.

CLASS 2: CONTENT-LEVEL. The deployment lands and post-deployment verification fails.
  Detection: none automated today. A human or a dispatched live-parity run
    observes that a Gate D verification item does not hold.
  Sub-classes:
    2a BLOCKING: a target user task fails. Search cannot reach a record, the
      roster or a record page is missing fields, the site serves a template that
      cannot be read with assistive technology, JSON is malformed.
    2b DEGRADED: site functions with a named defect. Cosmetic regression, an
      announcement that double-reads, a slow cold search.

CLASS 3: LATENT. Verification passed, the coordinator signed Gate D, and a defect
  is found later.
  Handling: a production incident on its own severity, not a gate closure failure.
  Only when the impact is blocking does it borrow the 2a path.
```

## The self-heal question, resolved rather than repeated

The brief's first instruction is "do not trigger another deployment," on the reasoning that one failed state is recoverable and two concurrent states are not. The repository's documented remedy is the opposite: a stuck Pages deploy self-heals because the next sweep push supersedes it, and `audit/24` incident #424 closed that way with no repo change. Both are right, and the discriminator is where the fault lives:

| Fault location | Does a later push heal it? | Action |
| :-- | :-- | :-- |
| GitHub-side queueing or a transient `pages-build-deployment` rejection | **Yes**, that is the documented cure | Wait two sweep cycles. Re-run the failed job only if something urgent is blocked (`rerun_failed_jobs`) |
| Nothing committed: the deploy never fired | Yes, any push heals it | `rebuild.yml` dispatch is the designed nudge; it republishes `docs/` without scraping |
| Defect in committed source (`web/`, `data/`, a workflow) | **No.** Every later sweep regenerates `docs/` from the same bad source and re-publishes it | Revert on `main`. Waiting makes the bad state permanent |

So the instruction becomes: **do not hand-trigger a deployment while the fault is unlocated, and do not wait for a self-heal once the fault is known to be in committed source.** Locating it is the first action, not waiting and not deploying.

## Gate D failure path, executable form

```
GATE D FAILURE PATH

Trigger: a post-deployment verification item returns a non-pass, or the Pages
deployment itself fails.

STEP 0, before touching production (agent-checkable, 2 minutes):
  [ ] Confirm the failure is about the site and not the instrument. Apply Phase 4
      D5: a negative finding needs a working positive control from the same
      network. Run gh run workflow_dispatch live-parity.yml as the second
      observation point.
  [ ] Record: deployment run ID, UTC timestamp, which item failed, exact observed
      behavior, screenshot or log URL, and the observation point used.
  [ ] Read the runbook section matching the symptom, CLAUDE.md "Pages deploy"
      sections, before deciding.

STEP 1, classify: 1, 2a, 2b, or 3, per the taxonomy above.

STEP 2, notify humans. Named release authority and named HCJC maintainer, from
  the Coordinator Brief Section 6. Both are NEEDS-OWNER today, which means this
  row is the first thing a coordinator must fill in; the failure path has no
  addressable human yet.

STEP 3, route by class:
  Class 1:
    [ ] Check pages-build-deployment and pages run conclusions.
    [ ] If live content is the previous deploy: no user-facing outage. Diagnose as
        a CI incident. Do not revert; revert is not a fix for queueing.
    [ ] If live content is absent or empty (site serves no published data):
        production outage. Escalate to the owner. Outage protocol: NEEDS-OWNER,
        which for this repository means the documented behavior is that deploy_alert
        opens a deduped issue and a human re-runs or reverts. There is no separate
        runbook file, and E3 does not invent one.
    [ ] Close the alarm issue promptly after recovery. audit/24 records that an
        open alarm suppresses new alarms, so a latched issue silences the next
        incident. Closing it is remediation, not tidiness.
  Class 2a: open the Rollback Authorization Record below.
  Class 2b: open a D1-structured defect (defect-[PROD]-[ID].md), non-blocking,
    with a fix and targeted retest required before any claim of production
    correctness, and record in the Gate D sign-off row:
      GATE-D-CONDITIONAL: [defect ID] open; release is live but not fully verified.
  Class 3: severity by user impact. Blocking borrows 2a. Otherwise a D1 defect
    plus a patch through a fresh Gate D cycle, and a post-release finding line in
    the release readiness record with UTC date, defect ID, and status.
```

## Rollback Authorization Record

```
ROLLBACK AUTHORIZATION RECORD - Incident [ID]

Failure class: 1-outage | 2a
Failure description:
Evidence URL:
Observation points confirming the defect (D5 rule, minimum two):
Data staleness cost of rolling back:        <-- required, see note below
  Roster generated_utc at the bad deploy:
  Roster generated_utc at the rollback target:
  Staleness introduced (minutes/hours):
Rollback target commit (main, prior to the release merge):
Named rollback authority:
Authority UTC timestamp:
Named executor:
Rollback method: git revert of the offending commits on main (default, see rules)
Rollback completion UTC timestamp:
Post-rollback verification:
  [ ] Previous state serving at https://www.aretheyinjail.com
  [ ] /data/current.json generated_utc matches the rolled-back commit
  [ ] Search returns a result for a known active record
  [ ] No new console errors from the rollback itself
  [ ] live-parity dispatch on the rolled-back tip: success
Post-rollback verifier:
Post-rollback UTC timestamp:
```

**Rollback method, corrected to how this site actually serves traffic.** `gh api repos/AICincy/HCJC/pages` reports `build_type=legacy`, `source={branch: main, path: /docs}`: production is the **committed `docs/` tree on `main`**, rebuilt by GitHub on every push. `pages.yml` additionally uploads and deploys an artifact, so two mechanisms coexist.

Consequence for the record's method field: re-deploying a previous Pages artifact is **not** an equivalent option here. It would serve the old artifact until the next push to `main` regenerates `docs/` from the still-broken source, at which point the bad state returns on its own. The durable rollback is `git revert` of the offending commits on `main`, which restores both the served tree and the source that regenerates it. The brief listed the two as alternatives; in this repository only one of them holds.

**Required staleness field.** A jail roster is not a static site. Rolling back republishes an *older custody snapshot*, so users can be told someone is in custody who was released, or the reverse, with consequences for bail, visits, and court appearances. The record therefore requires the rollback's data cost, computed from two `generated_utc` values, before a human authorizes it. A stale-but-accurate roster and a fresh-but-broken UI are not the same harm, and only a named human weighs them. No agent may recommend rollback by comparing defect severity alone.

## New Gate D cycle after any rollback

A rollback restores a known state; it does not close a release. The next attempt requires all of:

- [ ] Root cause documented, with the fault location from the self-heal table
- [ ] Fix applied and evidenced (a D1 loop when a defect was the cause)
- [ ] New candidate commit with exact-SHA CI evidence; Phase 4 D4 applies immediately, since the CI run bound to `d9ba0678` stops being tip evidence the moment a behavioral commit lands
- [ ] Gates A, B, C re-evaluated against the new build by their C-processors; a fix to `web/` invalidates evidence gathered against the previous build
- [ ] Named authority re-authorization of the Gate D sequence
- [ ] Full post-deployment verification, not abbreviated

## F-01: the deploy path contradicts a documented owner decision

Found while reading `pages.yml` for the rollback mechanics, reported rather than fixed.

`CLAUDE.md`, "Pages deploy: branch-serving, and the failed Actions experiment (2026-07-04)", records an owner decision: **"Do NOT migrate to an Actions-based deploy (`.github/workflows/pages.yml` + Source = 'GitHub Actions') to 'fix' this."** The stated reason: `actions/deploy-pages` failed twice with "Deployment failed, try again later", "leaving the site unable to publish at all", so branch-serving's intermittent failure is preferred.

`.github/workflows/pages.yml` exists in the tree today with exactly that shape: a `deploy` job, `if: github.ref == 'refs/heads/main'`, using `actions/deploy-pages@v4`. It runs on every push to `main`, and `b47cf77b` at `2026-09-23T02:05:47Z` edited that job's gate rather than removing it. Pages Settings still show `build_type: legacy`, so the branch path remains the serving source and the workflow path deploys alongside it, succeeding (run `35809118858`).

Two things follow, and neither is E3's to decide:

1. Phase 5 must not design a rollback that assumes the artifact path is authoritative. The serving source is `main/docs`. This document is written that way.
2. Someone must decide whether the Actions deploy is a deliberate partial migration, an abandoned experiment that should be deleted, or a mechanism that could re-introduce the 2026-07-04 publish failure mode if Pages Settings are ever flipped to "GitHub Actions". Recommend: the named HCJC maintainer reconciles `pages.yml` with the runbook, in either direction, and records the outcome in `DECISIONS.md`.

## Completion statement

All three classes have a detection route, a first action, and a re-entry point. Rollback is a human-only gate with its own record, a corrected single valid method, and a mandatory data-staleness field. The outage protocol for a Class 1 total-outage case is named as absent and marked `NEEDS-OWNER` rather than invented, which is what the brief required of E3. E3 makes no gate determination and authorizes no action.
