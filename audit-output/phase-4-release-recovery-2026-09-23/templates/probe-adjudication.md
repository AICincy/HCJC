# Probe adjudication record

Produced by D5 when LIVE-D is BLOCKED or INCONCLUSIVE. One file: `probe-adjudication.md`. D5 classifies evidence quality and returns it. It never determines LIVE-D's status.

```
LIVE-D PROBE ADJUDICATION - [UTC date]

Subject: [URL or URL set probed, e.g. https://www.aretheyinjail.com/data/*.json]
Determination sought: whether the site serves the published contract

Per observation point:
  Point: [name and network, e.g. "arena sandbox, Hamilton County route" / "GitHub Actions runner"]
  Method: [curl exit / script + args / workflow run ID]
  Control request (known-good HTTPS endpoint, same host and network at same time):
    Endpoint:  Result: [status or error]
    Control usable for negative findings: [Y/N]
  Raw result against subject: [status codes, error class, bytes]
  Classification: [SITE-EVIDENCE / PATH-EVIDENCE / INCONCLUSIVE]

Concordance:
  Points agreeing: [list]
  Points conflicting: [list]
  Result: [CONCORDANT / DISCORDANT]

Emission:
  CONCORDANT + subject unreachable from two valid points: report SITE-UNREACHABLE to the C-processor
  CONCORDANT + subject reachable and contract satisfied from two valid points: report SITE-VERIFIED to the C-processor
  Any other combination: report INCONCLUSIVE, name the missing observation point, and stop
```

## Rules

1. A negative finding requires a working positive control from the same vantage point. Without it the observation is PATH-EVIDENCE about the instrument, not the site.
2. Prefer the repository's own mechanism. `live-parity.yml` runs `scripts/verify_live_url_parity.py --site https://www.aretheyinjail.com`; its per-file `URLError` handling means a TLS reset surfaces as a non-404 error and cannot be absorbed by the script's recovery mode. Trigger that workflow via `workflow_dispatch` rather than writing a new probe.
3. Never conclude from one vantage point, and never average conflicting ones. Discordance is itself a finding, and it goes to a named human.
4. D5 does not declare LIVE-D closed, blocked, or passed.
5. Keep to a handful of GET requests against the manifest. No load testing production.
6. If a log or record cannot be retrieved, say so in the record. Do not reconstruct the content.

## Situation carried into this assessment

| Time (UTC) | Point | Observation | Reading |
| :-- | :-- | :-- | :-- |
| 2026-09-22T21:54:04 | closure run, manual probe | `curl: (35) SSL_ERROR_SYSCALL`, exit 35 (`closure/production-probe.txt`) | failure, control status unrecorded |
| 2026-09-22T23:55:54 | GitHub Actions, run `35799729427` | step "Probe current production URLs" concluded `success` | HTTP-level responses reached CI; a TLS reset would have failed the step |
| 2026-09-23T03:12 | arena sandbox | `api.github.com` 200; `www.aretheyinjail.com` and `aicincy.github.io` both reset after Client Hello; TCP connect succeeded, no TLS alert returned | egress path to GitHub Pages addresses cannot support a negative finding about the site |
| 2026-09-23T03:13 | `gh api repos/AICincy/HCJC/pages` | `status=built`, `https_certificate.state=approved`, `https_enforced=true`, `protected_domain_state=verified`, cname `www.aretheyinjail.com`, cert expires 2026-12-07 | Pages-side configuration consistent with a healthy HTTPS deployment |

Unresolved by this record: the log body of run `35799729427` was not retrievable (`gh run view --log` returned EOF from `results-receiver.actions.githubusercontent.com`), so the inference rests on step conclusion plus script control flow. One more CI-side probe with a recorded control would settle LIVE-D's evidence class. That request belongs to a named human, not to D5.
