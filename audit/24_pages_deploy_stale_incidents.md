# Pages deploy staleness incidents (deploy_alert log)

Incident record for stuck GitHub Pages deploys caught by `scraper.deploy_alert`
(live `/data/current.json` lagging committed `main`). Companion to the deploy
runbook in `CLAUDE.md` ("Pages deploy stuck in deployment_queued" and the
2026-07-04 Actions-deploy experiment) and to `audit/14_hcso_waf.md` (the
opposite failure: data frozen, deploys fine).

## Audit metadata

- Date: 2026-07-23
- Trigger: closure of issue #424, the first auto-opened deploy-staleness alarm.
- Author: Claude-assisted session, verified against the GitHub API and the live
  site at close time.

## Incident 2026-07-20 (issue #424)

| Field | Value |
| :-- | :-- |
| Alarm opened | 2026-07-20T18:34:56Z by `scraper.deploy_alert` (github-actions bot) |
| Peak lag | 110 min (threshold 90 min) |
| Committed `generated_utc` at alarm | 2026-07-20T18:34:22Z |
| Live `generated_utc` at alarm | 2026-07-20T16:44:34Z |
| Root cause | GitHub-side `pages-build-deployment` failure (branch-serving path), per the known intermittent "Deployment failed, try again later" mode |
| Resolution | Self-healed: a subsequent sweep push superseded the stuck deploy, no repo change required |
| Verified recovered | 2026-07-23T15:30Z: live and committed `generated_utc` identical (`2026-07-23T15:07:18Z`, lag 0), last three `pages build and deployment` runs `success` |
| Alarm closed | 2026-07-23T15:34:08Z with evidence comment |

## Operational lesson: the open alarm is also a mute switch

`deploy_alert` dedupes by searching for an open issue with the marker title
(`_open_issue_exists`, `scraper/deploy_alert.py`). While the alarm issue stays
open, any new stale-deploy event returns `"exists"` and opens nothing. #424
sat open for ~3 days after recovery, during which a fresh incident would have
been silent. Closing the alarm promptly after recovery is part of the
remediation, not cleanup. `freeze_alert` has the same latch.

Auto-close-on-recovery is deliberately NOT implemented in V1: the V1 change
policy (HCJC2 V2 Master Spec, section 6.1) freezes V1 to emergency, security,
legal, and data-integrity repairs, and both alert modules intentionally avoid
write-side issue APIs beyond open. The requirement is filed against HCJC2
alerting instead (spec section 32.3 alert coverage; see the HCJC2 backlog
issue "Alerting: auto-close alarm issues on recovery").
