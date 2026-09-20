# Runbook: off-platform capture of an HCSO block (second-source corroboration)

**Status: operator runbook.** The in-repo `data/waf_block_log.json` is captured
from the GitHub Actions runner. This runbook records the same denial from a
second, independent source so the evidence does not rest on the GitHub path
alone. Companion to `audit/14_hcso_waf.md` (diagnosis), `audit/16` (affidavit),
and `audit/17` (petition).

## Why

The mandamus record is strongest when the block is shown from more than one
vantage point and sealed by a neutral third party:

- The GitHub Actions runner records the denial in `data/waf_block_log.json`.
- A capture from a non-GitHub IP (residential or a VPS) shows the same public
  records served normally to an ordinary client.
- The differential (same honest User-Agent, different source IP) is the
  evidence that the block is IP-based, not a site outage.
- A Wayback "Save Page Now" snapshot adds a neutral, timestamped third-party
  copy.

This is observation and capture, not circumvention. Use your honest
User-Agent; do not route around the block.

## When to run

During a confirmed block: the homepage shows the interruption notice, the
freeze alarm has fired, or the latest `data/waf_block_log.json` entry is
`"event": "blocked"`.

## Steps

1. Confirm the GitHub path is blocked. Note the timestamp and the `block_sample`
   (status, sha256) of the latest `blocked` record in `data/waf_block_log.json`.

2. From a non-GitHub IP, capture the same endpoints the sweep hits. Save the
   full response (headers + body), then hash the body:

   ```sh
   UA='JCStream/0.1 (+https://github.com/AICincy/JCStream; off-platform capture)'
   BASE='https://www.hcso.org/justice-center-services/inmate-search'

   curl -sS -A "$UA" -D list_headers.txt  -o list_body.html  "$BASE/?last=A"
   curl -sS -A "$UA" -D detail_headers.txt -o detail_body.html "$BASE/inmate-detail/?id=<KNOWN_ID>"

   date -u +%Y-%m-%dT%H:%M:%SZ | tee capture_time_utc.txt
   sha256sum list_body.html detail_body.html | tee capture_sha256.txt
   wc -c list_body.html detail_body.html | tee capture_bytes.txt
   ```

   Record your public IP at capture time (for example `curl -sS https://api.ipify.org`).

3. Compare to the GitHub record. The runner log shows the block (HTTP 403, or an
   HTTP 200 stripped to zero rows). Your residential capture should show a normal
   HTTP 200 with a full-size body and real records. Same code and UA, different
   IP, opposite result.

4. Seal a third-party copy. Submit the roster URL to the Wayback Machine's Save
   Page Now and record the returned archive URL:

   ```sh
   curl -sS "https://web.archive.org/save/$BASE/" -D - -o /dev/null | grep -i '^content-location\|^location'
   ```

   (Or use the Save Page Now form at web.archive.org and copy the snapshot URL.)

5. Tie the blocked source to GitHub's published range. From the runner (or with
   the runner IP from the Actions log), capture the egress evidence:

   ```sh
   python -m scraper.egress_ip <runner_ip> --out data/egress_evidence.json
   ```

   The sweep does this automatically on a block when `JCSTREAM_CAPTURE_EGRESS=1`
   (set in `.github/workflows/sweep.yml`).

6. Preserve everything together: the raw response headers and bodies, the
   hashes, your IP and capture time, the Wayback URL, and the egress snapshot.
   List them as exhibits in the affidavit (`audit/16`).

## What it proves

A second, independent source shows HCSO serving the public records to an
ordinary client at the same time the GitHub Actions path is denied. That
differential, plus the neutral Wayback snapshot and the egress-range evidence,
corroborates that the block is by source IP and documents the denial from
outside this repository.

## Notes

- One capture per confirmed block is enough; the point is corroboration, not
  volume.
- Keep the captured headers verbatim (the WAF / CDN headers such as `cf-ray`
  and `server` are part of the evidence).
- Do not evade the block. This runbook only observes and records.
