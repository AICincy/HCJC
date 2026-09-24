--- CLAUDE.md (original - STALE)
+++ CLAUDE.md (corrected - 2026-09-24)
@@ -137,14 +137,31 @@
   three dedicated parsers plus the six-feed registry in `open_data_feeds.py`).
 - Build locally: `JCSTREAM_SITE_BASE_URL="" python -m web.build`
-- Force a sweep now instead of waiting for the cron: dispatch `sweep.yml`.
-  `POST https://api.github.com/repos/AICincy/HCJC/actions/workflows/sweep.yml/dispatches`
-  with body `{"ref":"main"}` and the token from `git credential fill` (gh CLI
-  is not installed on the owner's machine; expect HTTP 204). The 20-minute
-  skip-gate still applies: the run no-ops if `current.json` is younger than
-  20 minutes. Verified working 2026-07-05.
+- Force a sweep now instead of waiting for the cron: dispatch `sweep.yml`.
+  
+  **Option A** (if token has `actions:write` scope):
+  ```bash
+  gh workflow run sweep.yml -r main
+  ```
+  
+  **Option B** (via GitHub UI, no token required; recommended):
+  1. Go to https://github.com/AICincy/HCJC/actions/workflows/sweep.yml
+  2. Click "Run workflow" → Branch: main → Run
+  3. Watch the job start within 30s
+  
+  The 20-minute skip-gate still applies: the run no-ops if `current.json` is 
+  younger than 20 minutes. If Option A returns 403 (Forbidden), your token 
+  lacks `actions:write` scope; use Option B (UI) instead. **After a merge, 
+  GitHub revokes the session token** (no remote ops available in closed 
+  sessions); use a new session for Option A or Option B via GitHub web UI.
+  
+  Verified: UI dispatch works always (owner-initiated); CLI dispatch 
+  conditional on token scope (verified 2026-09-24).
+
 - Tests: `python -m pytest -q` (must stay green; >=464 tests as of 2026-07-09, suite grows).
+
 - `backend/` is the **only** component that talks to Supabase, and the only
   place a Supabase credential is read. It is Node (`@supabase/server`),
   independent of the Python pipeline. Run it with `npm ci && npm start` from

@@ -310,16 +327,28 @@
 
 #### If Deployment Lags > 90 min
 
+**Note**: Do NOT use `git push -f` (force-push). It rewrites history and 
+doesn't fix the GitHub Pages webhook issue. Instead, trigger the next sweep 
+or check GitHub status as shown below.
+
 1. Check https://github.com/AICincy/HCJC/actions
 2. Look for `pages-build-deployment` workflow
-3. If missing: Webhook misconfigured → re-run `sweep.yml`:
+3. If missing: Webhook misconfigured → trigger next sweep:
+   - **Wait for hourly cron** (automatic; sweep runs at top of the hour)
+   - **OR dispatch manually via UI** (owner only):
+     https://github.com/AICincy/HCJC/actions/workflows/sweep.yml → "Run workflow"
+   - **OR via CLI** (if token has `actions:write`):
    ```bash
    gh workflow run sweep.yml -r main
    ```
-4. If stuck: Build timed out → cancel it, re-run
-5. If failed: Check logs → fix issue, commit, re-run sweep
+
+4. If stuck > 120s: Build likely timed out or queued
+   - Do NOT cancel + force-push (loses history)
+   - Wait 10+ min (queues self-heal)
+   - If still stuck: Check runbook below
+
+5. If failed: Check logs → fix issue → commit via normal PR → wait for sweep
+
 6. Full runbook: `runbooks/live-parity-failure.md`
+
 7. Verify live:
    ```bash
    curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc
