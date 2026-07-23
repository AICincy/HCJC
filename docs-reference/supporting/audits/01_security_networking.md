# sec-net - Python Security and Networking Audit

## Audit metadata
- Skill: jcstream-python-security-networking
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 15
  - scraper/client.py (110 lines)
  - scraper/pra.py (118 lines)
  - scraper/pra_capias.py (127 lines)
  - scraper/pra_jms_vendor.py (132 lines)
  - scraper/cincy_open.py (56 lines)
  - scraper/cfs.py (89 lines)
  - scraper/cfs_pdi.py (78 lines)
  - scraper/incidents.py (76 lines)
  - scraper/shootings.py (76 lines)
  - scraper/sweep.py (355 lines)
  - scraper/courtclerk.py (43 lines)
  - .github/workflows/sweep.yml (105 lines)
  - .github/workflows/pra_daily.yml (45 lines)
  - .github/workflows/ci.yml (20 lines)
  - .github/workflows/ingest_case_data.yml (57 lines)
- Time: 2026-05-14T01:42:26Z

## Observations

1. `scraper/client.py:53,66` sets `verify=False` on both the `HTTPTransport` and the `httpx.Client`. The block comment at lines 45-52 explains the GitHub-runner clock-skew rationale and bounds the threat model to unauthenticated public-records traffic against `hcso.org`.
2. `scraper/cincy_open.py:53` and `scraper/cfs.py:45` instantiate `httpx.Client(...)` with no explicit `verify=` argument, so TLS verification defaults to true for `data.cincinnati-oh.gov`. Both modules read `JCSTREAM_USER_AGENT` and fall back to the bare string `"JCStream/0.1"` if it is not set, which omits the contact URL the upstream rationale relies on.
3. `scraper/client.py:24` sets `DEFAULT_CRAWL_DELAY = 0.0`, but the module docstring at lines 3-4 still says the client "Honors `Crawl-delay: 10` from robots.txt". The factory `make_client()` (line 109) reads `JCSTREAM_CRAWL_DELAY` from env and the production workflow `sweep.yml` does not set it, so the cron runs at delay 0.
4. `scraper/client.py:85-101` retries only on `response.status_code >= 500` and does not branch on 429. `Retry-After` is not consulted. The retry budget is two extra attempts at 0.5 s and 1 s; transport-level `retries=1` adds a socket-level retry.
5. The three PRA modules (`scraper/pra.py:62-80`, `scraper/pra_capias.py:69-87`, `scraper/pra_jms_vendor.py:80-98`) all branch on `port == 465` to pick `SMTP_SSL` and otherwise use plain `SMTP(...).starttls(context=ssl.create_default_context())` with a 30 s timeout. `s.login(user, password)` is only called if both are non-empty.
6. Dry-run guard in all three PRA modules is `if not from_addr or not _env("JCSTREAM_PRA_SMTP_HOST")`. The dry-run log line emits `to`, `subject`, and the message body, but never the SMTP user, password, host, or port (lines 91-92 / 98-99 / 109-110 across the three files).
7. The recipient address comes from env (`JCSTREAM_PRA_TO_CAPIAS_EMAIL`, `JCSTREAM_PRA_TO_PHOTOS_EMAIL`, `JCSTREAM_PRA_TO_JMS_EMAIL`) and is sourced from GitHub Actions secrets in `.github/workflows/pra_daily.yml:33,44`. No PRA module accepts a recipient from a scraped record or issue body.
8. `scraper/sweep.py:129` and `scraper/sweep.py:226` both create `ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY)` (32) and share a single `HcsoClient` instance. `client.py:58-59` sizes the pool as `max_connections=concurrency*2`, `max_keepalive_connections=concurrency`, matching the executor.
9. `scraper/incidents.py:32-40` and `scraper/shootings.py:32-40` catch broad `Exception` inside a `for` loop, swallowing arbitrary errors (including transient `httpx` errors) and falling through to an unfiltered query if every filter raises. The unfiltered fallback can pull up to 5000 / 1000 rows.
10. `.github/workflows/sweep.yml:50-52` sets `JCSTREAM_USER_AGENT` to a string that does not match the in-code `DEFAULT_UA`. The workflow sends `"JCStream/0.1 (+https://github.com/AICincy/JCStream)"` while `client.py:20-23` defines `"JCStream/0.1 (+https://github.com/AICincy/JCStream; Hamilton County OH public-records mirror; honors robots.txt)"`. The workflow value wins at runtime.

## Analysis

The TLS posture (Obs 1) is correctly scoped: the rationale comment ties `verify=False` to one host, one threat model, and a documented prior outage (clock skew on GH runners against Let's Encrypt notBefore). I am explicitly not flagging this. What I am flagging is that no code in the repo localizes the disablement to `hcso.org`. The same client object would accept any base URL the env passes in (`JCSTREAM_BASE_URL`), so the rationale is a deployment invariant, not a code one. That is acceptable for a single-purpose client, but documenting it on the `HcsoClient` class (not just at the `verify=False` line) would make the invariant survive future refactors.

Obs 2 highlights that the Cincinnati Socrata path uses a different trust boundary. `data.cincinnati-oh.gov` is a Tyler / Socrata-hosted government dataset endpoint, TLS verification is on by default (httpx default), and that is correct. The remaining concern there is the User-Agent fallback to `"JCStream/0.1"` with no contact URL; if the workflow env var is dropped or renamed, Socrata sees an unidentifiable client. Open-data hosts tolerate that, but the politeness contract is the only social control JCStream relies on (Obs 8), and the fallback strips it.

Obs 3 is a docstring-versus-behavior drift. The docstring claims robots.txt compliance with `Crawl-delay: 10`; the default is 0 and the workflow does not override it. Per the skill brief, raising the default to 10 would blow the sweep budget and should be rejected. The correct fix is updating the docstring to match the parallelism-is-the-limiter reality (already stated on the comment at line 24) and the User-Agent string at line 22, which advertises "honors robots.txt". The UA string overstates compliance to the upstream operator.

Obs 4 is acknowledged in the skill brief as a conscious limitation. A 429 surge from HCSO would propagate up to `_sweep_list` (sweep.py:217-223), be caught as a generic `Exception`, and roll into `n_failed`. If the surge is broad enough to push past 10 percent, the degraded-sweep guard rejects the cycle, so the system fails closed. The only sharp edge is that bursting 32 concurrent requests through `make_client()` after a 429 will likely escalate, not relax, the rate limit. Adding 429 to the retry branch with a capped `Retry-After` honor (say 30 s) would help, but the wall-clock budget is real; I keep this as a low-severity find.

Obs 5 and 6 cover the SMTP transport. All three PRA modules use the same pattern, all three pick `SMTP_SSL` on port 465 and `STARTTLS` on everything else, all three use `ssl.create_default_context()` (which gets default trust roots and is up to date with Python 3.12 defaults), and all three set `timeout=30`. No plain SMTP send exists. Dry-run mode does not log secrets. This is clean.

Obs 7 is the question the skill brief flags as potentially high-severity: can untrusted input override the recipient? It cannot. All three PRA recipients come from env vars sourced from GitHub Actions secrets, and the body templates are static (`pra.py:31-46`, `pra_capias.py:33-53`, `pra_jms_vendor.py:37-63`) with only `{since}` and `{until}` interpolation, both of which are RFC 3339 strings derived from `datetime.now(timezone.utc).strftime(...)`. No header injection surface. No CRLF reachable from outside the workflow.

Obs 9 is a moderate concern about the open-data fallbacks. If the Socrata schema changes and every `where` clause throws, the fallback runs an unfiltered query that can return up to 5000 rows for incidents and 1000 rows for shootings. The intent is graceful degradation, but the unfiltered pull is unbounded relative to the `where`-scoped pull (which is `> '{since}'`). For a private Socrata token deployment this would also burn the budget; for the anonymous tier it is just larger payloads. The bare `except Exception` is overly broad and would also silently swallow `KeyboardInterrupt`-not-quite-equivalent typo bugs or `httpx.ConnectError` that the operator probably wants to see.

Obs 10 is a small drift that costs the contact URL the `client.py` rationale leans on. The workflow's UA still contains a contact URL, but it does not include the "honors robots.txt" claim, which is arguably better given Obs 3. Reconciling these strings in one place (load `DEFAULT_UA` from the module, set `JCSTREAM_USER_AGENT` only when overriding) avoids the drift.

## Technical notes

```python
# scraper/client.py:24 vs docstring:3-4
# Docstring claims "Honors `Crawl-delay: 10` from robots.txt"; default is 0.0
DEFAULT_CRAWL_DELAY = 0.0  # seconds - parallelism is the limiter, not delay.
# DEFAULT_UA also asserts "honors robots.txt" but the cron does not.
```

```python
# scraper/client.py:85-101 - retry loop only covers 5xx, not 429.
for attempt in range(2):
    if response.status_code < 500:
        break
    time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s
    response = self._client.get(path, params=params)
response.raise_for_status()
```

```python
# scraper/cincy_open.py:53 (also cfs.py:45)
# verify defaults to True (good). UA falls back to "JCStream/0.1" with no contact URL.
ua = os.environ.get("JCSTREAM_USER_AGENT", "JCStream/0.1")
with httpx.Client(timeout=30.0, headers={"User-Agent": ua}) as client:
```

```python
# scraper/pra*.py SMTP path - consistent across all three modules.
ctx = ssl.create_default_context()
if port == 465:
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
        if user and password: s.login(user, password)
        s.send_message(msg)
else:
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls(context=ctx)
        if user and password: s.login(user, password)
        s.send_message(msg)
```

```python
# scraper/incidents.py:32-40 - broad except + unfiltered fallback.
for where in where_candidates:
    try:
        rows = query(DATASET_ID, where=where, ...)
        return rows
    except Exception as e:
        log.debug("incidents filter %r failed: %s", where, e)
log.warning("incidents pull failed all filters; falling back to unfiltered")
return query(DATASET_ID, limit=limit)  # up to 5000 rows
```

```yaml
# .github/workflows/sweep.yml:50-52
# UA from workflow does NOT match DEFAULT_UA in client.py.
JCSTREAM_USER_AGENT: >-
  JCStream/0.1 (+https://github.com/AICincy/JCStream)
```

```python
# scraper/sweep.py:226 - 32-way executor sharing one HcsoClient.
with ThreadPoolExecutor(max_workers=DEFAULT_CONCURRENCY) as pool:
    for rows in pool.map(fetch_one, surnames):
        ...
# client.py:58-59 sizes connection pool accordingly:
# max_connections=concurrency*2, max_keepalive_connections=concurrency
```

## Findings

### sec-net-F1 - Docstring and User-Agent overstate robots.txt compliance
- Severity: low
- Confidence: high
- File: scraper/client.py:3-6, 22, 24
- Issue: The module docstring says it honors `Crawl-delay: 10` and the `DEFAULT_UA` advertises "honors robots.txt", but `DEFAULT_CRAWL_DELAY` is 0.0 and the cron does not override it. The doc and UA represent a claim to the upstream operator that the code does not implement.
- Impact: If HCSO checks UA strings against observed request cadence, the apparent inconsistency invites a complaint. Reputational, not technical.

### sec-net-F2 - Cincinnati Socrata clients lose contact-URL UA on env miss
- Severity: low
- Confidence: high
- Files: scraper/cincy_open.py:51, scraper/cfs.py:43
- Issue: Both modules read `JCSTREAM_USER_AGENT` and fall back to the bare string `"JCStream/0.1"` if it is missing. The sweep workflow sets it, but ad hoc local runs, the PRA workflow, and any future workflow that drops the env var will hit Socrata with an unidentifiable client.
- Impact: Socrata has lax UA policy, so blocking risk is minimal. The cost is identity drift across workflows and a polite-by-default property that depends on env, not code.

### sec-net-F3 - 429 not in retry envelope; no Retry-After honored
- Severity: low
- Confidence: med
- File: scraper/client.py:95-99
- Issue: Retry triggers only on `>= 500`. A 429 surge from HCSO is treated as a hard failure and rolls into `n_failed` for the sweep guard. The transport-level `retries=1` does not help here either (it covers connection errors, not 429).
- Impact: A short HCSO rate-limit window trips the degraded-sweep guard and skips a cycle. System fails closed, so impact is operational (missed sweep) not correctness.

### sec-net-F4 - Broad `except Exception` + unfiltered fallback on incidents/shootings
- Severity: low
- Confidence: high
- Files: scraper/incidents.py:32-40, scraper/shootings.py:32-40
- Issue: Both pulls iterate filter candidates inside `try/except Exception` and, if every filter raises, run a final unfiltered `query(DATASET_ID, limit=limit)` of up to 5000 / 1000 rows. The bare `except` also swallows transient `httpx.ConnectError` that the operator likely wants to see.
- Impact: On a transient outage, the unfiltered fallback can pull a much larger payload than intended and surface stale data. Both modules are `continue-on-error: true` in the workflow, so a failure is non-fatal, but the silent fallback hides genuine schema regressions.

### sec-net-F5 - `verify=False` rationale is documented at the call site, not at the class
- Severity: low
- Confidence: med
- File: scraper/client.py:31-67
- Issue: The TLS-disable rationale is sound for `hcso.org` only, but the `HcsoClient` accepts an arbitrary `base_url` (env-overridable). A future env-driven repoint to a non-HCSO host would silently inherit `verify=False`.
- Impact: Today this is theoretical; the class name and the workflow both pin it to HCSO. The lift is a one-line class-level docstring assertion.

### sec-net-F6 - Sweep workflow UA string drifts from module DEFAULT_UA
- Severity: low
- Confidence: high
- File: .github/workflows/sweep.yml:50-52 versus scraper/client.py:20-23
- Issue: The workflow injects a shorter UA that omits the "honors robots.txt" tail. Two sources of truth for the UA string invite future drift.
- Impact: Cosmetic; both still contain the contact URL.

## Recommendations

### sec-net-F1 - Reconcile docstring and UA to match observed behavior
- File: scraper/client.py
- Function: module docstring + `DEFAULT_UA`
- Before/after:
  - Before: docstring "Honors `Crawl-delay: 10` from robots.txt with a per-host token bucket"; UA "...; honors robots.txt)"
  - After: docstring "Polite parallel HTTP client for hcso.org. Identifies itself in the User-Agent. Parallelism (DEFAULT_CONCURRENCY=32) is the limiter; the crawl-delay token bucket is wired up but defaults to 0.0 for the 30-minute cron budget. Retries once on transient 5xx; does NOT attempt to evade WAFs, rate limits, or CAPTCHAs."; UA drops the "honors robots.txt" tail or replaces it with "parallelism-limited, contact via repo".
- Expected test impact: zero. UA string is only asserted by hand; no test pins it.

### sec-net-F2 - Centralize UA fallback to the module DEFAULT_UA
- Files: scraper/cincy_open.py, scraper/cfs.py
- Function: `query()`, `pull_recent()`
- Before/after:
  - Before: `ua = os.environ.get("JCSTREAM_USER_AGENT", "JCStream/0.1")`
  - After: `from .client import DEFAULT_UA; ua = os.environ.get("JCSTREAM_USER_AGENT", DEFAULT_UA)`
- Expected test impact: zero if tests do not pin the UA string. A quick grep should confirm.

### sec-net-F3 - Add 429 to the retry branch with a capped Retry-After
- File: scraper/client.py
- Function: `HcsoClient.get`
- Before/after:
  - Before: `if response.status_code < 500: break`
  - After: branch on `status_code >= 500 or status_code == 429`; on 429, read `Retry-After` header, cap at 30 seconds, sleep, then retry once. Keep the existing 5xx backoff for non-429.
- Rollback: revert the loop body. If a misbehaving upstream returns chronic 429 with no Retry-After, the cron budget could lengthen; cap and attempt count contain this. The skill brief explicitly endorses this fix scope.
- Expected test impact: add one unit test that monkey-patches the client and asserts a 429 path retries once.

### sec-net-F4 - Narrow the exception scope on Socrata filter retries
- Files: scraper/incidents.py:32-40, scraper/shootings.py:32-40
- Function: `pull_recent()`
- Before/after:
  - Before: `except Exception as e: log.debug(...)`
  - After: `except httpx.HTTPStatusError as e:` (only swallow Socrata "bad column" responses, which surface as 400). Let `httpx.RequestError` and friends propagate to the workflow logs. Consider gating the unfiltered fallback behind a flag or capping `limit` to a much smaller number when the fallback fires.
- Expected test impact: any test that fakes an `httpx.RequestError` may need updating. None observed in scope.

### sec-net-F5 - Pin the verify=False rationale to the class
- File: scraper/client.py
- Function: `HcsoClient` class docstring
- Before/after: add a short class docstring stating "TLS verification is intentionally disabled because this client is bound to hcso.org public-records endpoints (no auth, no PII). Repointing base_url to any other host without restoring verify=True is a security regression."
- Expected test impact: none.

### sec-net-F6 - Source the workflow UA from the module
- File: .github/workflows/sweep.yml:50-52
- Function: env block of the `HCSO inmate sweep` step
- Before/after: drop the explicit `JCSTREAM_USER_AGENT` env override; let `make_client()` use `DEFAULT_UA`. If the workflow wants to add a build-tag suffix, do it in a one-line Python snippet that imports `DEFAULT_UA` and appends.
- Expected test impact: none.

## Remediation plan

- Step 1: Reconcile UA + docstring drift
- Touches: scraper/client.py, scraper/cincy_open.py, scraper/cfs.py, .github/workflows/sweep.yml
- Verification: `python -m pytest -q` and `grep -rn "JCStream/0.1" scraper .github/workflows`
- Expected duration: S
- Rollback: `git checkout` the four files

- Step 2: Add 429 to retry envelope with capped Retry-After
- Touches: scraper/client.py, tests/test_client.py (or equivalent)
- Verification: `python -m pytest -q`, plus the new unit test for 429 retry
- Expected duration: S
- Rollback: revert the retry-loop change; the prior 5xx-only branch is unchanged

- Step 3: Narrow except scope on Socrata fallback pulls
- Touches: scraper/incidents.py, scraper/shootings.py
- Verification: `python -m pytest -q` plus a manual `python -m scraper.shootings --days 1 -v` smoke
- Expected duration: S
- Rollback: re-broaden `except Exception` in two spots

- Step 4: Add class-level invariant docstring to HcsoClient
- Touches: scraper/client.py
- Verification: `python -m pytest -q`
- Expected duration: S
- Rollback: trivial

## Cross-references

- "Sweep degraded-roster guard and photo-prune cap interact with retry behavior changes; coordinate any 429 retry tweak with sweep reliability defaults" -> jcstream-python-sweep-reliability
- "`scraper/ingest_issue.py` consumes `ISSUE_BODY` from a `issues: opened/edited/reopened` workflow trigger and commits to `data/`; untrusted input boundary for the case-data path lives in data-integrity scope" -> jcstream-python-data-integrity
- "`scraper/courtclerk.py` builds URLs that interpolate `last`, `first`, `dob`, `case_number`; if any caller passes these into HTML attributes without escaping, that is a template concern" -> jcstream-html-template-security
- "Broad `except Exception` swallowing `httpx.RequestError` is also an architecture / error-envelope question across modules" -> jcstream-python-architecture

## Confidence and limitations

- Read in full: scraper/client.py, scraper/pra.py, scraper/pra_capias.py, scraper/pra_jms_vendor.py, scraper/cincy_open.py, scraper/cfs.py, scraper/cfs_pdi.py, scraper/incidents.py, scraper/shootings.py, scraper/sweep.py, scraper/courtclerk.py, all four `.github/workflows/*.yml` files.
- Sampled: `scraper/ingest_issue.py` (only the `ISSUE_BODY` env intake to confirm it is not a PRA recipient injection vector).
- Skipped: `scraper/parsers.py`, `scraper/store.py`, `scraper/models.py`, `scraper/photos.py`, `scraper/orc.py`, `scraper/match.py`, `web/build.py`, all templates - out of skill scope (parser robustness, data integrity, template security).
- Assumptions that could be wrong:
  - The GitHub Actions secret `JCSTREAM_PRA_SMTP_PASS` is never echoed by the runner. GitHub masks secrets in logs by default; if a custom step ever did `echo "$JCSTREAM_PRA_SMTP_PASS"` it would still be masked, but that is GitHub's behavior, not code I verified end-to-end.
  - HCSO's current cert chain behavior. The `verify=False` rationale is taken as documented (unverified - live source out of scope).
  - Socrata behavior under the bare `JCStream/0.1` UA. Their throttling rules are not pinned to UA strings as far as I know (unverified - live source out of scope).
- Findings would not materially change with live-site access; everything here is observable from code and workflow YAML. Live access would only let me confirm or falsify the 429-frequency assumption behind F3.

End of report.
