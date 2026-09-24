# Runbook: live-parity failure

**Service:** JCStream static site at `https://www.aretheyinjail.com`  
**Gate:** `.github/workflows/live-parity.yml`  
**Owner:** repository maintainer / Pages administrator  
**Policy:** alert-only. The parity workflow never deploys, rewrites `main`, or retries forever.

## 1. Triage in the first five minutes

1. Open the failed [live-parity Actions runs](https://github.com/AICincy/HCJC/actions/workflows/live-parity.yml) and copy the failing step's complete error. Record the run URL, commit SHA, UTC time, page path, and whether the JSON contract job passed.
2. Do **not** bypass the check by adding recovery mode or disabling TLS. A red probe is the intended alert.
3. Classify the first failure:
   - **TLS / timeout / DNS / HTTP 404 or 500** — availability or routing.
   - **missing marker** — live tree predates the stamp rollout or was published from the wrong artifact.
   - **malformed marker** — template or an intermediary changed the value.
   - **stale live HTML** — deployment lag or stuck Pages build.
   - **candidate regression** — checked-out tip is older than the live tree; do not publish it blindly.
   - **candidate unreadable/mismatched** — build or `data/current.json` integrity problem.

## 2. Reproduce without changing production

From a clean checkout of the same failing SHA, install the pinned requirements and run:

```bash
python scripts/verify_public_data.py
python scripts/verify_live_url_parity.py \
  --site https://www.aretheyinjail.com --timeout 10
python scripts/verify_live_html_freshness.py \
  --site https://www.aretheyinjail.com \
  --local docs --data data/current.json \
  --max-lag-hours 26 --timeout 10 \
  --fail-on-live-newer \
  --page index.html --page data/index.html --page help/index.html \
  --page stats/index.html --page transparency/index.html
```

For a direct response diagnosis, use a bounded request; never use an unbounded loop:

```bash
curl --max-time 10 --location-trusted -sS -D /tmp/jcstream.headers \
  -o /tmp/jcstream.body https://www.aretheyinjail.com/index.html
sed -n '1,25p' /tmp/jcstream.headers
grep -n 'jcstream:generated-utc\|Last updated' /tmp/jcstream.body
```

If the failure is TLS EOF or certificate verification, check DNS and the certificate chain from a second network and inspect the Pages custom-domain configuration. Do not set certificate verification off in the probe. If the domain is down, escalate to the Pages/DNS owner and leave the alert open.

## 3. Interpret freshness results

`data/current.json` is the tip source of truth. The candidate HTML must carry exactly its `generated_utc` value. Positive lag means live is older:

- `lag <= 26.0 h`: pass.
- `lag > 26.0 h`: stale deploy; inspect Pages deployment status and the last successful `sweep.yml` commit.
- negative lag: live is newer. The production workflow uses `--fail-on-live-newer` because publishing an older candidate could regress content. Re-run from a fresh tip after the live commit is present. A diagnostic run without that flag only warns.
- missing stamp: likely pre-feature or wrong artifact; confirm the built candidate has the marker and redeploy the correct Pages artifact through the normal protected path.
- malformed/offset stamp: fix the template/build source; never normalize an ambiguous offset silently.

Check source and live vintages together:

```bash
python - <<'PY'
import json
print(json.load(open('data/current.json', encoding='utf-8'))['generated_utc'])
PY
# The probe output is authoritative for live page vintages.
```

## 4. Sweep and deployment checks

1. Inspect the latest [sweep runs](https://github.com/AICincy/HCJC/actions/workflows/sweep.yml). Confirm the run built both `data/` and `docs/`, committed them, and pushed to `main`.
2. Inspect Pages deployment history. A green sweep is not proof of a green Pages deployment; correlate the commit SHA and deployment artifact.
3. If the sweep is stale or absent, use **Run workflow** on `sweep.yml` only after checking concurrency and the source tip. Do not hand-edit `docs/` or force-push generated output.
4. If the build reports corrupt JSON, missing required data, or a render exception, stop. The temp-swap build should leave the last-good `docs/` tree intact. Repair the source/data issue, run the test suite, then rerun the sweep.
5. If `web.build` reports optional tab-feed files missing, verify whether the fallback is expected. Capture the path and source error; do not call the site fresh solely because the build exited 0.

## 5. Recovery and close-out

After the root cause is corrected:

```bash
python -m pytest -q
ruff check .
mypy scraper web
python scripts/verify_public_data.py
python scripts/verify_live_html_freshness.py --site https://www.aretheyinjail.com \
  --local docs --data data/current.json --max-lag-hours 26 --timeout 10 \
  --fail-on-live-newer --page index.html --page data/index.html \
  --page help/index.html --page stats/index.html --page transparency/index.html
```

Run the parity workflow manually on the merged `main` commit. Close or annotate the alert only when:

- the JSON contract job passes;
- every sampled live page has a strict marker;
- candidate and live vintages are aligned under the chosen policy;
- the Pages deployment URL and commit are recorded; and
- the human footer is visible in a desktop and mobile browser check.

Attach the run URL, probe output, SHA-256 evidence, and any screenshot to the incident record. If TLS/HTTP failures persist, keep the alert open and escalate; there is intentionally no automatic recovery path.
