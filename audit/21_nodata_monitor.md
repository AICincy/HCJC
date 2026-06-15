# No-data monitor: detect a missed sweep (absence of sweep_start)

## Audit metadata

- Date: 2026-05-22
- Trigger: runbook bottleneck #6 (a GitHub Actions cron skip would go undetected).
- Companion to monitor 19947564 (WAF-block persistence) and `scraper/ddlog.py`.

## What this catches that 19947564 does not

| Failure | sweep_start emitted? | sweep_complete emitted? | waf_block emitted? | Caught by 19947564 | Caught by this monitor |
|---------|----------------------|--------------------------|--------------------|--------------------|------------------------|
| HCSO WAF blocks the runner | yes | yes (`status` blocked) | yes | yes | no |
| Cron never fires / runner never starts | no | no | no | no | yes |
| Sweep crashes before any emit | no | no | no | no | yes |

19947564 keys on the presence of `waf_block`. When the cron itself does not run, nothing is emitted, so a block monitor stays silent. This monitor keys on the absence of `sweep_start`.

## Cadence math (sets the window)

- Workflow cron is `*/15 * * * *` with a 20-minute skip gate; effective cadence is 20-45 minutes, and during incidents the next run can slip past the hour (see CLAUDE.md).
- A 60-minute window would false-positive on a single legitimately-slipped cron. Use a 90-minute window: under normal operation at least one `sweep_start` lands every 45 minutes, so 90 minutes always covers one, while a genuine "cron stopped" condition produces zero across 90 minutes.

## Monitor definition (Datadog log monitor)

- Name: `JCStream: no sweep_start (cron may be down)`
- Type: Log monitor (count)
- Query:

```
logs("service:jcstream @event:sweep_start").index("*").rollup("count").last("90m") < 1
```

- Alert threshold: `< 1` (zero `sweep_start` events in the trailing 90 minutes).
- No warning threshold (binary condition: a sweep either started or it did not).
- Notify on no-data: yes. This monitor's entire purpose is the no-data case, so do not let Datadog suppress it as "no data."
- Evaluation: the query already rolls up a count, so it returns 0 rather than no-data when the index is reachable but empty.
- Priority: P3 (a stalled mirror, same posture as 19947564).
- Tags: `service:jcstream`, `repo:AICincy/HCJC`, `kind:availability`.
- Recipients: replace the placeholder with the real notifier before publishing (email, Slack, or PagerDuty), same as 19947564.

### Message

```
{{#is_alert}}
No `sweep_start` events from JCStream in the last 90 minutes.
The GitHub Actions sweep cron (*/15 with a 20-min skip gate) appears to have
stopped firing, or the runner is failing before any telemetry is emitted.

This is distinct from a WAF block: when HCSO blocks the runner the sweep still
runs and emits sweep_start + sweep_complete + waf_block, so monitor 19947564
covers that. Zero sweep_start means the job itself is not running.

Check: GitHub Actions runs for .github/workflows/sweep.yml, then DD_API_KEY
presence in the job env. Runbook triage: audit/14_hcso_waf.md (rule out a block
first), then the Actions logs.
{{/is_alert}}
{{#is_recovery}}
sweep_start telemetry resumed.
{{/is_recovery}}
```

## Before publishing

1. Confirm `DD_SITE` (the monitor lives in the same Datadog org as 19947564 / dashboard `bd7-ibi-kjq`).
2. Set the recipient handle in the message.
3. Let it observe for one normal day to confirm it stays green at the real cadence, then tune the window only if a legitimate slip trips it.
4. Cross-link it from dashboard `bd7-ibi-kjq` so both availability and block signals sit together.

## Local cross-check

`python -m scripts.summarize_telemetry` reads the durable block log offline and
reports current block state and roster staleness. It does not see Datadog, so it
cannot detect a missed cron; that gap is exactly what this monitor fills.
