# WAF freeze monitor: detect sustained HCSO WAF block via roster staleness

> **NOT IMPLEMENTED (2026-07-04).** JCStream does not use Datadog. The Datadog
> monitor described below (and the `scraper/ddlog.py` / `DD_*` env it assumes,
> including any claim that `DD_API_KEY` is set in `sweep.yml`) was never built
> and is not present in the repo. Treat this as a historical proposal only. The
> live roster-freeze alarm is `scraper.freeze_alert` (GitHub Issues), and
> stuck-deploy detection is `scraper.deploy_alert`.

## Audit metadata

- Date: 2026-05-28
- Trigger: Task Brief item "flag Datadog monitor to owner" (WAF posture A).
- Companion to monitor `audit/21_nodata_monitor.md` (no sweep_start) and the
  `scraper.freeze_alert` GitHub Issues alarm.

## What this catches

| Failure | freeze_alert catches? | This monitor catches? |
|---------|----------------------|----------------------|
| WAF blocks runner, roster stale >6h | yes (GitHub Issue) | yes (Datadog alert) |
| WAF blocks runner, roster stale <6h | no (below threshold) | yes (warning at 3h) |
| Cron never fires | no | no (use audit/21) |
| Sweep runs but data unchanged (non-WAF) | yes | yes |

`scraper.freeze_alert` opens a GitHub Issue when `roster_stale_hours >= 6`.
This monitor provides a Datadog-native alert with a warning tier at 3h and a
critical tier at 6h, giving earlier visibility and integration with on-call
routing.

## Signal source

The sweep emits a `sweep_complete` log event with `roster_stale_hours` as a
numeric attribute. When the roster is fresh, `roster_stale_hours` is near zero.
When WAF-blocked, it climbs monotonically until recovery.

If `roster_stale_hours` is not yet a parsed facet, create one:
- Path: `@roster_stale_hours`
- Type: measure (double)
- Group: `jcstream`

## Monitor definition (Datadog log monitor)

- Name: `JCStream: roster frozen (HCSO WAF block likely)`
- Type: Log monitor (metric value)
- Query:

```
logs("service:jcstream @event:sweep_complete").index("*").rollup("max", "@roster_stale_hours").last("90m") >= 6
```

- Critical threshold: `>= 6` (matches `ROSTER_STALE_ALARM_HOURS` in `sweep_guards.py`).
- Warning threshold: `>= 3` (early heads-up before the full alarm fires).
- Notify on no-data: no (the audit/21 monitor covers the no-data case).
- Priority: P3 (stale mirror, not a site outage; site serves last-good data).
- Tags: `service:jcstream`, `repo:AICincy/HCJC`, `kind:availability`, `cause:waf`.
- Recipients: same handle as monitor 19947564 and audit/21.

### Message

```
{{#is_alert}}
JCStream roster has been frozen for {{value}} hours (threshold: 6h).
The HCSO WAF is likely blocking the GitHub Actions runner IP. The sweep
continues running and the site serves last-good data, but the roster is stale.

Posture (2026-05-28): document the block, do not evade.
- Each blocked cycle is logged to data/waf_block_log.json (hash-chained).
- The site shows an interruption notice automatically.
- JCSTREAM_HTTP_PROXY is deliberately unset while the mandamus record builds.

Triage:
1. Check recent Actions runs: grep for "list sweep looks degraded" or "ROSTER FROZEN".
2. Review data/waf_block_log.json for the block timeline.
3. If the block persists >72h and mandamus posture changes, set JCSTREAM_HTTP_PROXY.

Runbook: CLAUDE.md "Runbook: roster frozen" section.
{{/is_alert}}
{{#is_warning}}
Roster staleness rising: {{value}} hours since last update. WAF block may be
starting. No action needed yet; the 6h threshold triggers the full alarm.
{{/is_warning}}
{{#is_recovery}}
Roster freshness restored. WAF block has rotated or been resolved.
{{/is_recovery}}
```

## Alternative: GitHub Actions-only (no Datadog)

If Datadog is not yet ingesting sweep telemetry, the existing
`scraper.freeze_alert` provides equivalent coverage via GitHub Issues (fires at
6h). The gap is: no warning tier, no on-call integration, and no dashboard
correlation with the no-data monitor. Adding this Datadog monitor closes those
gaps.

## Before publishing

1. Confirm `DD_API_KEY` is set in the sweep workflow env (already referenced in `sweep.yml`).
2. Confirm `@roster_stale_hours` is a parsed facet in the `jcstream` service logs.
3. Set the recipient handle in the message (email, Slack, or PagerDuty).
4. Add to dashboard `bd7-ibi-kjq` alongside 19947564 and the no-data monitor.
5. Let it observe for one WAF block cycle to confirm thresholds are calibrated.
