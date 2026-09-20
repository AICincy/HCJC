# FCRA removal SLA: best-effort target and the removal-SLA warning tier

## Audit metadata

- Date: 2026-07-08
- Trigger: 2026-06-16 code review, High finding (scraper-integrity): "No
  fallback mechanism accelerates removal when the cron slips. An inmate who
  leaves HCSO's roster could remain on the public site past a 30-minute
  removal target."
- Companion to `scraper.freeze_alert` (6h freeze issue) and the historical
  `audit/22_waf_freeze_monitor.md` warning-tier proposal.

## The finding is structural, not a bug

A released inmate is dropped on the next successful sweep. The removal logic is
correct at normal cadence; the gap is the delay when cadence slips. Three facts
bound what a fix can do:

| Constraint | Consequence |
| :-- | :-- |
| Effective sweep cadence is 20-45 min; `CLAUDE.md` forbids lowering the sweep thresholds to force faster runs | The normal path cannot be safely accelerated |
| During a WAF block the degraded-roster guard deliberately holds last-good data (blocks last 24-72h) | Departed inmates stay listed for the block duration, by design (do-not-evade posture) |
| Detecting a departure requires a fresh roster fetch | A "secondary removal trigger" needs the exact WAF-blocked, expensive step, so it is no cheaper than the main sweep |

A true accelerator is therefore not viable. The realistic exposures are:

1. **WAF block** (24-72h): inmate stays until the block clears. Inherent to the
   do-not-evade posture. Disclosed by the site interruption notice and the
   hash-chained `data/waf_block_log.json`.
2. **Cron slip** (occasional GitHub Actions congestion): the sweep runs late,
   so the roster ages past normal cadence for one or two cycles, then
   self-heals on the next successful run.

## What shipped: a removal-SLA warning tier

`scraper.freeze_alert.removal_sla_warn` emits a GitHub Actions `::warning`
annotation when `roster_stale_hours` is in the window
`[REMOVAL_SLA_HOURS (1h), ROSTER_STALE_ALARM_HOURS (6h))`. It runs in the same
"Roster freeze alarm" sweep step as the existing `alert`, needs no new
workflow, and opens no issue, so it cannot spam during a multi-day WAF block.

| Roster staleness | Signal |
| :-- | :-- |
| < 1h | none (normal cadence) |
| 1h to 6h | `::warning` annotation (this change): earlier visibility of a slipped cron or a developing WAF block |
| >= 6h | `::error` annotation + deduped GitHub issue (`scraper.freeze_alert.alert`, unchanged) |

This realizes the warning-tier idea from `audit/22` GitHub-natively, at the
tighter removal-SLA threshold.

## What was deliberately NOT built

- **A 60-minute issue-opener.** It would open an issue during every early WAF
  block (which the freeze issue already covers at 6h) and needs an
  active-block check against the 11.6 MB `waf_block_log.json` every cycle. The
  annotation carries the same information without the issue churn or the read.
- **An external cron-slip watchdog.** A separate scheduled workflow could catch
  the case where the sweep cron never fires, but it is itself subject to the
  same Actions congestion, and the slip it would catch is a rare,
  self-healing transient. Disproportionate; see `audit/21_nodata_monitor.md`
  for the no-data monitor that already covers "cron never fires."

## Posture

The 30-minute removal target is best-effort at sweep cadence. When HCSO's WAF
blocks the runner, removal is delayed by design, disclosed on the site, and
recorded in the evidence log; the project does not evade the block to hit the
target. The removal-SLA warning gives sub-6h operational visibility so a
genuine cron slip surfaces before the 6h freeze issue.
