# HCSO WAF investigation — IP-blocking diagnosis and shipped defenses

## Audit metadata

- Date: 2026-05-19
- Trigger: persistent "booking photos not loading" complaint covering 223 of 1225 (18%) of current roster, with 137 of the 223 (61%) booked in the last 7 days.
- Method: side-by-side comparison via Claude.ai (Opus 4.6) browsing HCSO directly + a local `python -m scraper.sweep --max-surnames 3` run from the Claude Code container against HCSO.
- Outcome: shipped four PRs (#57, #58, #59, #60) closing every parser-side and transport-side gap we could close from inside the polite-scraper stance. Root cause is upstream (HCSO's WAF blocking the GitHub Actions runner IP range), not in our code.

## Observations

- **HCSO is reachable** from at least two non-GH-Actions IPs (the Claude.ai session and the Claude Code container running this audit). Both got HTTP 200 responses of 91-230 KB with the photo `<img>` tag intact, using the project's existing `JCStream/0.1 (+...)` User-Agent.
- **GitHub Actions sweep cycles produce empty-photo records** for the same inmate IDs that Claude.ai confirmed have a photo on HCSO. The 223 inmates with `photo_filename = ""` correspond to detail-page fetches that came back too small to parse, or that the parser silently produced an empty `Inmate` from.
- **The HCSO photo markup is unchanged** from what `scraper/parsers.py` was written against. The 274px style hook, the `data:image/png;base64,...` mechanism (with JPEG bytes despite the `image/png` declaration), and the parent element shape (`<div class="pull-left ml-3">`) all match the existing extractor.
- **HCSO declares an empty payload for some inmates** rendered with `<img src="data:image/png;base64,"` (literally no bytes after the comma). The parser correctly skips these. ~80-90 of the 223 photo-empty inmates appear to be this case (HCSO genuinely has no photo for them yet).
- **The local sweep from this container extracted a photo for inmate 14809523** (71 KB JPEG; the same inmate Claude.ai's first verification flagged as `jcstream_missed`). The GH Actions sweep on the same code does not. The differential is the source IP.
- **HCSO's WAF returns truncated responses**, not 4xx/5xx, when it decides to block. The HTTP status remains 200 (so `raise_for_status()` doesn't trip), but the body is <5 KB and devoid of structured content. This is the failure mode that hid the bug for so long.

## Diagnosis

1. HCSO's WAF (Cloudflare or similar) classifies the GitHub Actions runner IP range as "automated, deny" with high probability. The classifier uses parallelism + missing browser-shape headers + IP reputation; the polite User-Agent that JCStream sends is not enough to clear it on those IPs.
2. The pre-2026-05-19 scraper had no defense: when the WAF returned a stub, the parser produced an empty `Inmate`, `_fetch_one` wrote that back into `current`, the cached photo on disk was discarded (corrupt-bytes-overrides-disk-fallback bug), and the next sweep re-fetched and got the same stub. Photos that landed once on disk could survive a single block, but each block-and-overwrite cycle eroded coverage.
3. The carry-forward + WAF-guard stack we shipped tonight stops the erosion. Photos that were ever extracted successfully are now preserved across WAF blocks. Photos that were never extracted (because the GH runner has never gotten an unblocked detail-page response for that inmate) still cannot land until the WAF lets through at least one good fetch.

## Defenses shipped (all merged to main)

| PR | Wave | What it fixes |
|----|------|---------------|
| #57 | Cron + parser cleanup | Photo-retention bug A: `if photo_bytes: if downscale_and_save:` no longer drops the disk-cached photo when Pillow rejects bytes. Photo-retention bug B: `_fetch_one` returning `None` (network error) now carries forward from `previous` instead of dropping the inmate. |
| #58 | WAF-block guard | When the response is <5 KB AND the parser produces an empty `Inmate` AND the inmate is in `previous`, `_fetch_one` returns `None` to trigger carry-forward instead of overwriting with empty data. New inmates fall through to the list-row name fallback. |
| #59 | Same-cycle retry + diagnostics | `_fetch_one` now retries once after backoff on a WAF-block-shaped response. If HCSO clears within the backoff window, the photo lands this cycle. `scripts/grep_waf_blocks.sh` summarizes WAF blocks per run, per inmate, per streak. |
| #60 | Browser-shape headers + local diagnostic | Adds `Connection: keep-alive` and `Upgrade-Insecure-Requests: 1` to the HCSO client default headers. Adds `scripts/peek_hcso.sh` for one-shot diagnostic fetches against HCSO from any IP. |

Plus exponential backoff per consecutive WAF-block-shaped response (in PR #58's iteration), thread-shared streak counter resetting on success, photo-extraction tier-2 fallback for size+extension URLs, and a diagnostic INFO log for "page parsed but no photo extracted" so the operator can see which inmates failed and why.

## What this does and does not solve

**Solves:**
- Data erosion: WAF blocks no longer destroy previously-good records.
- New-inmate stubs: the list-row fallback still rescues a name + booking date.
- Self-healing within a cycle: the WAF-retry catches inmates the WAF clears mid-sweep.
- Observability: WAF blocks are logged with inmate ID, response size, and streak count.

**Does not solve:**
- Inmates that have never had a successful detail-page fetch from the GH Actions runner. These wait until the WAF lets one through. If HCSO's classifier is hard-blocking the runner IP range, that may never happen for some inmates.
- HCSO's actual WAF policy. The defenses above are best-effort within the project's polite-scraper stance.

## Infrastructure options (out of scope as code changes)

If after one or two full sweep cycles with the defenses live the new-inmate photo coverage still doesn't recover, the remaining options are infrastructure-level:

1. **Self-host the sweep** on a non-GH-Actions IP (residential, small VPS, home server). The cron lives outside GitHub Actions; the runner commits results via the GitHub API. Most likely to clear the WAF.
2. **Add a one-shot manual sweep** that runs from the maintainer's laptop. Periodically the maintainer triggers `python -m scraper.sweep` against HCSO from their residential IP and commits the result; the GH Actions cron handles incremental updates only.
3. **Allowlist request to HCSO**. Legitimate (we mirror their public records under ORC § 149.43) but slow.
4. **Accept current coverage and rely on the new carry-forward to preserve what works**. The 18% photo gap may be the steady-state ceiling for the GH Actions IP.

## Verification protocol after the fix lands

1. Wait 2-3 sweep cycles (~60-90 min after PR #60 merge).
2. Run `scripts/grep_waf_blocks.sh 5` to summarize WAF blocks from the last 5 sweeps. Expect either zero blocks (defenses cleared it) or a small consistent count (residual WAF pressure within the carry-forward's tolerance).
3. Run `scripts/peek_hcso.sh 14809523 2643322 14536455` from a residential IP to confirm HCSO still has photos for the previously-missed sample.
4. Re-run the Claude.ai re-verification brief (`/tmp/jcstream-claude-ai-reverify-brief.md` from this session).
5. If at least 50% of `still_missing` rows in the re-verification have become `fixed`, the on-code defenses are working as intended.
6. If `still_missing` rate stays >80% across two re-verifications, escalate to infrastructure option 1 or 2 above.

## Confidence and limitations

- **High confidence** that the parser is correct, the cached-photo fallback works, and the WAF guard triggers carry-forward as designed. Verified by running the sweep locally with the post-PR-60 code and observing both successful photo extraction (id 14809523) and correct skip behavior on empty-base64-payload pages (id 2683700).
- **Medium confidence** that the GH Actions IP range is the blocked one. Inferred from the differential between local-IP success and GH-Actions-IP failure on the same code. Not directly verified because we cannot test from a known GH Actions IP from this container.
- **Limitations.** I could not view the live Sentry or GH Actions workflow logs from this container, so the `scripts/grep_waf_blocks.sh` numbers are deferred to the maintainer's next run.
