# cf-migration - Cloudflare Pages Migration Runbook

## Audit metadata
- Skill: ad-hoc (migration planning request)
- Commit: 1f36e1b836555df16c5cd1d5fb15bf58e700f015
- Branch: claude/export-skill-agent-zip-gspVE
- Date: 2026-05-14
- Files scanned: _headers 64, web/build.py 1744, .github/workflows/sweep.yml 105
- Live targets probed: not re-probed (audit 11 covers current header state)
- Pytest baseline: not re-run (this is a planning document, no code change proposed)
- Cloudflare docs consulted (via Cloudflare Developer Platform MCP, 2026-05-14):
  - https://developers.cloudflare.com/pages/configuration/headers/
  - https://developers.cloudflare.com/pages/configuration/redirects/
  - https://developers.cloudflare.com/pages/configuration/serving-pages/
  - https://developers.cloudflare.com/pages/configuration/build-configuration/
  - https://developers.cloudflare.com/pages/configuration/custom-domains/
  - https://developers.cloudflare.com/pages/framework-guides/deploy-anything/
  - https://developers.cloudflare.com/pages/migrations/migrating-jekyll-from-github-pages/
  - https://developers.cloudflare.com/pages/platform/limits/
  - https://developers.cloudflare.com/pages/how-to/add-custom-http-headers/
  - https://developers.cloudflare.com/workers/static-assets/headers/
  - https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/
  - https://developers.cloudflare.com/rules/snippets/examples/security-headers/
  - https://developers.cloudflare.com/changelog/post/2026-01-23-pages-file-limit-increase/

## Premise (read first)

Audit 11 (spa-S2, spa-S4, spa-S5) flagged three HTTP-only security headers that GitHub Pages cannot serve: `X-Content-Type-Options: nosniff`, frame-ancestors / `X-Frame-Options`, and `Permissions-Policy`. A `_headers` stub already lives at the repo root (`/home/user/JCStream/_headers`) in the format Cloudflare Pages parses. It is inert today because GitHub Pages does not read it.

This runbook covers two paths to make those headers effective:

- Path A (preferred): migrate from GitHub Pages to Cloudflare Pages. Pages reads `_headers` from the build output directory and applies the rules to every static asset response. The custom domain `www.aretheyinjail.com` moves from a GitHub Pages CNAME to a Cloudflare Pages custom domain.
- Path B (fallback): keep GitHub Pages as the origin and bind a Cloudflare Worker to `www.aretheyinjail.com/*` that injects the missing headers on response. Lower migration cost, ongoing code maintenance.

Both paths preserve the 30-minute sweep cron in `.github/workflows/sweep.yml`. The cron currently commits the rebuilt `docs/` tree to the branch; under Path A, that commit triggers a Cloudflare Pages Git-integration deploy; under Path B, nothing about the build pipeline changes.

## Observations

### Current `_headers` file is valid Cloudflare Pages syntax

Per Cloudflare's headers reference (https://developers.cloudflare.com/pages/configuration/headers/), a `_headers` rule is a multi-line block: line 1 is the URL pattern, subsequent indented lines are `name: value` pairs. Splat `*` greedily matches all characters and may appear at most once per URL; named placeholders use the `:placeholder_name` form. The current file at the repo root uses these exact constructs:

```
/*
  Content-Security-Policy: ...
  Strict-Transport-Security: max-age=63072000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: ...
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
/photos/*
  Access-Control-Allow-Origin: *
  Cross-Origin-Resource-Policy: cross-origin
/static/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=31536000, immutable
/feed.xml
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=300
...
```

Each block starts in column 0 (URL) and the subsequent header lines are indented. The current file uses two-space indent; the docs example uses two-space indent. Both are accepted.

### Per-rule and per-file limits

From https://developers.cloudflare.com/pages/platform/limits/ (consulted 2026-05-14):

- Maximum 100 header rules in `_headers`. Current file has 7 blocks (`/*`, `/photos/*`, `/static/*`, `/feed.xml`, `/booked.xml`, `/released.xml`, `/search.json`, `/dispatches.json`) - all well under.
- Maximum 2000 characters per single header value. The current CSP at line 26 of `_headers` is roughly 470 characters - well under.
- Pages also has a 100-redirect-rule limit on the (unused) `_redirects` file.

### Default Cloudflare headers Pages already adds

From https://developers.cloudflare.com/pages/configuration/serving-pages/ ("Headers always added"), Cloudflare Pages already injects on every response:

```
Access-Control-Allow-Origin: *
Cf-Ray: ...
Referrer-Policy: strict-origin-when-cross-origin
Etag: ...
Content-Type: ...
X-Content-Type-Options: nosniff
Server: cloudflare
```

This is the load-bearing observation for this audit: `X-Content-Type-Options: nosniff` (spa-S2) and `Referrer-Policy: strict-origin-when-cross-origin` (spa-S3) are added automatically by Pages even with no `_headers` file. The `_headers` block at the repo root re-asserts both; on Pages, the assertion is harmless redundancy.

Pages also conditionally adds:

```
Cache-Control: public, max-age=0, must-revalidate
Cache-Control: no-transform           (if encoded)
Content-Encoding: ...                  (if encoded)
X-Robots-Tag: noindex                  (only on preview deployments)
```

The conditional `Cache-Control` overrides the existing per-rule values in `_headers` only when the rule does not set its own. Current `_headers` blocks for `/static/*`, `/feed.xml`, `/booked.xml`, `/released.xml`, `/search.json`, `/dispatches.json` all set explicit `Cache-Control`; those win.

### File-count and file-size budget

From https://developers.cloudflare.com/pages/platform/limits/:

- Free plan: 20,000 files per site, 25 MiB per file.
- Paid plan with `PAGES_WRANGLER_MAJOR_VERSION=4` env var: 100,000 files per site (per changelog 2026-01-23).

Current `docs/` tree count and size:

```
$ find /home/user/JCStream/docs -type f | wc -l
2321
$ du -sh /home/user/JCStream/docs
65M
```

2,321 files / 65 MB total, well inside the free-plan ceiling. No single file approaches 25 MiB (largest is `docs/index.html` at 1.5 MB). The roster grows over time as `docs/inmate/{id}/` directories accumulate (currently 1,211 inmate pages plus 1,084 photos), but at the current rate it would take many years to approach 20,000 files. Headroom is comfortable.

### Build configuration for a "no build" static site

From https://developers.cloudflare.com/pages/framework-guides/deploy-anything/, a static site that is already pre-built in the repo uses:

| Configuration option       | Value     |
|----------------------------|-----------|
| Production branch          | claude/export-skill-agent-zip-gspVE |
| Build command (optional)   | exit 0    |
| Build output directory     | docs      |
| Root directory             | (blank)   |

`exit 0` is the documented sentinel for "no build step required". The build container exits successfully, Pages skips the build and uploads `docs/` directly. Per https://developers.cloudflare.com/pages/configuration/build-configuration/: "Cloudflare recommends using `exit 0` as your Build command to access features such as Pages Functions". JCStream has no Pages Functions today (no `functions/` directory), so the `exit 0` recommendation is about preserving the option, not a current requirement.

### `CNAME` and `.nojekyll` artifacts are harmless on Pages

`web/build.py:673-679` writes `docs/CNAME` from the `JCSTREAM_CNAME` env var. Cloudflare Pages does not read `CNAME` (custom domains are set in the dashboard). `CNAME` is served as a 200 with `Content-Type: application/octet-stream` (Pages's default for extensionless files), occupies one file in the 20,000-file budget, and otherwise does nothing. Safe to leave as-is.

`web/build.py:199` writes `docs/.nojekyll`. Cloudflare Pages does not look for it (Pages does not run Jekyll under any circumstances). Same disposition: served as a 200, harmless, leave it.

The corollary: no `web/build.py` changes are strictly required for Path A. The migration can happen entirely in the Cloudflare dashboard plus a DNS cutover. (Optional cleanup is enumerated in the post-migration section.)

### Worker fallback (Path B) operating model

From https://developers.cloudflare.com/workers/configuration/routing/routes/ and https://developers.cloudflare.com/rules/snippets/examples/security-headers/, a Worker bound to `www.aretheyinjail.com/*` intercepts requests, calls `fetch(request)` to the origin (GitHub Pages), clones the response (it is immutable as received), and appends/overwrites response headers before returning. The same pattern is documented at https://developers.cloudflare.com/pages/how-to/add-custom-http-headers/.

This requires the apex zone `aretheyinjail.com` to be on Cloudflare (it already is, per audit 11's `Server: cloudflare` observation) and the `www` record to be proxied (orange-cloud). The Worker is bound via Settings > Domains & Routes > Add > Custom Domain or Route.

The trade-off: every request hits an additional execution layer (the Worker invokes one `fetch()` per request to the GH Pages backend). On the free Workers plan that is 100,000 invocations/day - JCStream traffic is well under that. CPU time per invocation is sub-millisecond for header injection. The Worker source is one file, but it is a separate deploy artifact that has to be kept in sync with the policy in `_headers`.

### Migration to Workers Static Assets (not relevant today)

Per https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/, Cloudflare is steering greenfield static-asset deploys toward Workers Static Assets rather than Pages. Workers Static Assets reads `_headers` from the asset directory in the same syntax (https://developers.cloudflare.com/workers/static-assets/headers/, same documentation copy as Pages). Pages is still production-grade and is not being EOL'd; the Worker route is a forward-looking option, not a current requirement. This runbook stays on Pages as the recommended path because the Git integration is the simplest fit for JCStream's existing commit-on-sweep workflow.

## Analysis

### Path A: migrate to Cloudflare Pages (recommended)

Operating model: the GitHub Actions sweep cron continues to push commits to `claude/export-skill-agent-zip-gspVE` every 30 minutes. Cloudflare Pages watches that branch via Git integration and deploys each commit to production. The custom domain `www.aretheyinjail.com` resolves to the Pages deployment.

Why preferred:

1. The `_headers` file becomes active on the next deploy with no code change in this repo (the stub is already correct).
2. Cloudflare already proxies the apex domain (per audit 11's `Server: cloudflare` and `cf-cache-status` observations), so DNS / TLS posture is unchanged from a visitor's perspective.
3. Pages free tier comfortably absorbs JCStream's footprint (2,321 files / 65 MB / no file over 25 MiB). 500 builds per month limit on free is more than the 30-min cron's ~1,440 commits per month would consume; the owner needs paid plan or a build-skipping pattern to stay inside free-tier builds. See "Risks and mitigations" below.
4. The GitHub Pages branch lifecycle (pushing to a deploy environment named `github-pages` in `.github/workflows/sweep.yml:38-40`, deploy-pages@v4 action) becomes inactive but does not need to be deleted in the same window as the cutover.

Why not preferred:

- Build-count budget. At one cron commit per 30 minutes, the sweep produces roughly 1,440 commits per month. Cloudflare Pages free tier allows 500 builds per month (https://developers.cloudflare.com/pages/platform/limits/). The owner must either (a) upgrade to the Pro plan (5,000 builds/month, currently $20/month per cloudflare.com/plans), or (b) add a build-skip rule. Pages supports "Build watch paths" (https://developers.cloudflare.com/pages/configuration/build-watch-paths/) to exclude paths that should not trigger a build, but `docs/` is the build output and excluding it would defeat the deploy entirely. The realistic free-tier pattern is "deploy on tagged release commits only", which does not match JCStream's continuous-rebuild model. Treat the Pro upgrade as part of the migration cost.

### Path B: front GitHub Pages with a Cloudflare Worker (fallback)

Operating model: the GitHub Actions sweep cron is unchanged. GH Pages serves the origin. A Worker on the `www.aretheyinjail.com/*` route intercepts every request, calls `fetch(request)` to GH Pages, and decorates the response with the missing headers before returning it to the visitor.

Why this is the cheaper migration:

1. No DNS cutover. The `www` record stays a CNAME to `aicincy.github.io` (or wherever it points today); the Worker is bound to the route, not to a new origin.
2. No build-count budget concern. The Worker has its own quota (100,000 invocations/day on free, well under JCStream's traffic).
3. The GitHub Pages workflow in `.github/workflows/sweep.yml` is untouched.
4. Rollback is one-click: detach the Worker route in the dashboard, the request flows straight to GH Pages with no header injection.

Why this is the more expensive operating posture:

1. The Worker code is a separate deploy artifact that lives outside this repo. The policy in `_headers` would then exist in two places (this repo's `_headers`, used by neither system today, and the Worker source on Cloudflare). Maintenance discipline requires either deleting `_headers` from this repo (since it would be inert again) or treating the Worker source as the canonical policy.
2. Every page view incurs a Worker invocation. Cold-start latency is single-digit milliseconds at the Cloudflare edge and is rarely material, but it is non-zero overhead that Path A avoids.
3. The GH Pages `X-GitHub-Request-Id` leak documented at audit 11 line 84 remains visible (unless the Worker explicitly deletes it on every response, which doubles the maintenance surface).

### Where the secrets live

JCStream has zero secrets that the Cloudflare side needs. The site is fully static, no third-party APIs are called from the runtime, no analytics, no Sentry-style error reporting. The only secrets in the project today are the SMTP credentials and the optional Giscus repo IDs, both of which live in the GitHub Actions environment for the sweep cron and are never read by Cloudflare. Path A and Path B both deploy with no secret configuration on the Cloudflare side.

The one optional secret pattern is the `PAGES_WRANGLER_MAJOR_VERSION=4` env var (https://developers.cloudflare.com/changelog/post/2026-01-23-pages-file-limit-increase/) to lift the file-count ceiling from 20,000 to 100,000. JCStream is at 2,321 files; this is not needed today. Worth recording in case the roster history outgrows the 20,000 ceiling in the future.

## Findings

| ID | Sev | Conf | One-line summary | Owner |
|----|-----|------|------------------|-------|
| cf-mig-1 | info | high | Current `/home/user/JCStream/_headers` is valid Cloudflare Pages syntax; no edits required before activation | site owner |
| cf-mig-2 | info | high | Cloudflare Pages adds `X-Content-Type-Options: nosniff` and `Referrer-Policy: strict-origin-when-cross-origin` by default, so the matching `_headers` lines are harmless redundancy | site owner |
| cf-mig-3 | med | high | At 30-min sweep cadence, monthly build count (about 1,440) exceeds Cloudflare Pages free-tier limit (500/month); plan upgrade or build-skip strategy is part of the migration cost | site owner |
| cf-mig-4 | low | high | `docs/CNAME` and `docs/.nojekyll` are GH-Pages-specific files that Cloudflare Pages ignores; safe to leave, optional cleanup gates on whether the owner ever fully retires GH Pages | jcstream-build-helper-author |
| cf-mig-5 | low | high | After Path A activation, the meta CSP and meta referrer in `web/templates/base.html` should be removed to keep one source of truth (per the comment in `_headers` lines 22-23) | jcstream-template-author |
| cf-mig-6 | info | high | Workers fallback (Path B) creates a second source of truth for the policy; if Path B is chosen, delete `_headers` from this repo to avoid drift between the inert file and the live Worker | site owner |

## Path A: Cloudflare Pages migration steps

These are exact dashboard steps. The owner runs them; no code change in this repo is required to start.

### A0. Pre-flight (no DNS impact)

1. Confirm the apex zone `aretheyinjail.com` is on Cloudflare. (It is, per audit 11.)
2. Confirm the `www` DNS record currently CNAMEs to `aicincy.github.io` (or the equivalent GH Pages target). Capture the current target so you can roll back.
3. In a separate browser tab, capture the current production response headers with `curl -sI https://www.aretheyinjail.com/` so the post-migration diff is verifiable.

### A1. Create the Pages project

1. Cloudflare dashboard > Workers & Pages > Create application > Pages > Import an existing Git repository.
2. Authorize the Cloudflare GitHub App on `AICincy/JCStream` (this is a separate install from the Giscus app referenced in CLAUDE.md).
3. Select `AICincy/JCStream`, branch `claude/export-skill-agent-zip-gspVE`.
4. Build settings:
   - **Framework preset**: None.
   - **Build command**: `exit 0`
   - **Build output directory**: `docs`
   - **Root directory**: leave blank (the repo root is the build context).
5. Save and Deploy. The first deploy uploads the current `docs/` tree as-is. After deploy, the project gets a `*.pages.dev` preview URL (for example `aretheyinjail.pages.dev`).
6. Verify the preview URL renders the site correctly and `curl -sI https://aretheyinjail.pages.dev/` shows the headers from `_headers`. **Do not proceed until the preview-URL diff confirms the new headers (`Content-Security-Policy`, `X-Frame-Options: DENY`, `Permissions-Policy`, `Strict-Transport-Security`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`) are present.**

### A2. Plan budget reckoning

1. Go to Pages project > Settings > Builds. Confirm the build count meter.
2. Decide between (a) upgrading to the Pro plan (5,000 builds/month) before the DNS cutover, or (b) accepting that builds will pause at 500/month on free tier (after which the production deploy holds at the last successful build until the next billing cycle, which is a degraded but not broken state).
3. If choosing (a), do the plan upgrade now, not after cutover. Plan changes take effect immediately.

### A3. Attach the custom domain

1. Pages project > Custom domains > Set up a custom domain.
2. Enter `www.aretheyinjail.com`. Cloudflare detects the apex zone is on the same account and offers automatic DNS configuration.
3. Accept the auto-config. Cloudflare deletes the GH Pages CNAME on `www` and replaces it with a `CNAME www aretheyinjail.pages.dev` proxied (orange cloud). Reference: https://developers.cloudflare.com/pages/configuration/custom-domains/.
4. Watch the certificate provisioning step. Cloudflare issues a Universal SSL cert for the hostname. Status moves through "Initializing" -> "Pending" -> "Active". Typical time: 1 to 5 minutes; SLA is up to 24 hours.
5. Once Active, `curl -sI https://www.aretheyinjail.com/` should show `Cf-Ray` and the headers from `_headers`. The GH-Pages-specific `X-GitHub-Request-Id` header should no longer appear.

### A4. Update repo to drop the meta-CSP duplication (optional, recommended)

After Path A is active, the meta CSP and meta referrer in `web/templates/base.html` (per audit 11 R0.2 / R0.3 and the comment in `_headers` lines 22-23) are duplicated by the HTTP-side policy and should be removed for single-source-of-truth. This is the cf-mig-5 finding above. Hand off to `jcstream-template-author`.

### A5. Watch the first three sweep deploys

The sweep cron pushes a commit every 30 minutes. After A3 completes, the next three pushes should each trigger a Pages deploy. Verify in the Pages project's Deployments tab that:

1. Each commit produces a new deployment.
2. Each deployment status reads "Success".
3. The production URL serves the new content within 1 to 2 minutes of deploy completion.
4. Build count meter increments as expected (one per commit).

### A6. Retire the GitHub Pages bits (optional, deferred)

These are explicit non-required steps; defer until the owner is confident Path A is stable:

1. GitHub repo > Settings > Pages > Source: switch from "GitHub Actions" to "None". This stops the `actions/deploy-pages@v4` step in `.github/workflows/sweep.yml` from doing anything. Do NOT modify `sweep.yml` per the task constraints; the step will fail silently on subsequent runs and can be cleaned up in a follow-up commit by the `jcstream-scraper-author` skill.
2. Delete the `github-pages` environment in GitHub repo > Settings > Environments.
3. Optionally remove the `docs/CNAME` write in `web/build.py:673-679` (cf-mig-4) and the `.nojekyll` write at line 199. Neither hurts on Pages; the case for removing them is "one less GH-Pages relic in the build".

## Path B: Cloudflare Worker fallback steps

Use this if Path A's build-count budget or plan-upgrade requirement is a non-starter. The Worker bypasses the budget conversation entirely.

### B0. Pre-flight

Same as A0.

### B1. Create the Worker

1. Cloudflare dashboard > Workers & Pages > Create > Hello World Worker.
2. Name: `jcstream-headers` (or any identifier).
3. Replace the starter source with the script in the "Worker source" section below.
4. Save and Deploy.

### B2. Attach to the production hostname

1. Worker > Settings > Domains & Routes > Add > Route.
2. Zone: `aretheyinjail.com`. Route: `www.aretheyinjail.com/*`.
3. Save.

Per https://developers.cloudflare.com/workers/configuration/routing/routes/, the route takes precedence over the DNS-only handling once the request reaches Cloudflare. The `www` DNS record stays a CNAME to GitHub Pages; the Worker just runs on the way out.

### B3. Verify

`curl -sI https://www.aretheyinjail.com/` should now show:

- The original GH Pages headers (`X-GitHub-Request-Id`, original `Cache-Control`, etc).
- The Worker-injected security headers on top.
- `Server: cloudflare` (unchanged).

The `X-GitHub-Request-Id` leak persists unless the Worker source deletes it explicitly. If the owner wants to strip it, add `newResponse.headers.delete('X-GitHub-Request-Id')` to the Worker before the return.

### B4. Delete `_headers` from the repo

Per cf-mig-6, `_headers` becomes a misleading source of truth once Path B is live. Either delete it or replace its contents with a comment that points to the Worker source as the canonical policy. Hand off to the owner (the file lives at the repo root, not under any skill's domain).

### Worker source

```javascript
// jcstream-headers - injects audit-11 spa-S2/S4/S5 security headers
// on responses from the GitHub Pages origin for www.aretheyinjail.com.
//
// Mirror of the policy in /_headers (which is inert under Path B). If you
// edit one, edit the other. Reference: audit/12_cloudflare_pages_migration.md.

const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'self'; object-src 'none'; " +
    "img-src 'self' data: https://*.tile.openstreetmap.org; " +
    "style-src 'self' 'unsafe-inline'; font-src 'self'; " +
    "script-src 'self' https://giscus.app; " +
    "connect-src 'self' https://giscus.app; frame-src https://giscus.app; " +
    "form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests",
  "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy":
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), " +
    "magnetometer=(), microphone=(), payment=(), usb=()",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
};

export default {
  async fetch(request) {
    const response = await fetch(request);
    const newResponse = new Response(response.body, response);
    for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
      newResponse.headers.set(name, value);
    }
    // Strip the GH Pages origin signature.
    newResponse.headers.delete("X-GitHub-Request-Id");
    return newResponse;
  },
};
```

Pattern reference: https://developers.cloudflare.com/pages/how-to/add-custom-http-headers/ and https://developers.cloudflare.com/rules/snippets/examples/security-headers/.

## Downtime and risk estimate

| Path | Cutover window | Visible downtime | Rollback path | Migration cost |
|------|----------------|------------------|---------------|----------------|
| A. Pages | DNS swap at A3 step | Up to TTL of the prior CNAME (typically 5 minutes at GH Pages defaults; 60 seconds if Cloudflare manages the record) | Restore prior `www` CNAME to GH Pages; the GH Actions deploy environment is still wired and the next sweep redeploys to GH Pages within 30 minutes | Pro plan upgrade may be required for build budget |
| B. Worker | Route activation at B2 step | None (DNS unchanged; the Worker activates on the next request match, sub-minute) | Detach the route in dashboard; requests fall through to GH Pages on the next request | Free under typical traffic; Worker source is maintained outside this repo |

Both paths preserve content during the cutover. There is no point at which the site is unreachable: Path A's DNS swap is atomic at the Cloudflare side, and Path B does not touch DNS at all.

The riskiest moment in Path A is between A1 (Pages deploy succeeds at the `*.pages.dev` preview URL) and A3 (custom domain activates). During that window the live site is still served from GH Pages and the Pages project is only reachable at its preview URL. This is intentional - it gives the owner time to verify headers on the preview URL before any visitor traffic moves. Do not skip the verification step in A1.

## Do / Don't rollback list

Do:
- Take a `curl -sI` snapshot of the current production response headers before any change so the rollback diff is verifiable.
- Capture the prior `www` DNS CNAME target before letting Cloudflare auto-configure the record at A3.
- Verify the `*.pages.dev` preview URL renders correctly and serves the new headers before doing the custom-domain step.
- Watch the first three post-cutover sweep deploys to confirm Git integration is working end-to-end.
- Choose Pro plan or build-skip strategy before the cutover, not after. Hitting the free-tier 500-build cap mid-month produces a confusing degraded state where the deploys silently stop.

Don't:
- Don't modify `_headers` based on this audit; the current syntax is valid Cloudflare Pages syntax. The only suggested edit (deleting the meta-CSP duplicates in `web/templates/base.html`) is in templates, not `_headers`, and is owned by `jcstream-template-author`.
- Don't modify `.github/workflows/sweep.yml`. The GH Pages deploy step continues to run; under Path A it simply has nothing to deploy to once GitHub Pages is set to "None" in repo settings. Cleanup of the workflow is a follow-up commit, not part of the cutover.
- Don't delete the `github-pages` environment or the GH Pages source setting in the same change window as the cutover. Leave them in place as a working rollback target for at least one full week.
- Don't delete `docs/CNAME` or `docs/.nojekyll` from the build output. They are harmless on Pages and are part of the rollback path if Path A is reversed.
- Don't run Path A and Path B simultaneously. If the Worker is bound to the route and the custom domain is also attached to a Pages project, the Worker takes precedence and the Pages headers are double-applied (some redundantly, some conflicting with the Worker's `set()` overwrite). Pick one.
- Don't run the cutover during a high-attention period. The roster is publicly viewable; a 5-minute DNS-propagation window during which different visitors see different origins is operationally normal but visually inconsistent. Off-peak hours (Cincinnati overnight) are the right slot.

## Post-migration follow-ups (hand off to other skills)

These are not part of the cutover. List them in the owner's followup queue once Path A or Path B is verified stable:

1. **Template cleanup (jcstream-template-author).** After Path A or B activation, the meta CSP and meta referrer in `web/templates/base.html` (audit 11 R0.2, R0.3) become duplicates of the HTTP-side policy. Remove them. Single source of truth.
2. **Sweep workflow cleanup (jcstream-scraper-author).** Once Path A is stable for one billing cycle and the GH Pages source is set to "None", the `actions/deploy-pages@v4` step in `.github/workflows/sweep.yml` no longer has a target. Cleanup that step.
3. **Audit 11 re-probe (a11y-auditor / ad-hoc).** Re-run the header probe `curl -sI` against `/`, `/stats/`, `/data/`, `/statute/`, `/static/style.css`, `/robots.txt`, and a 404 path. Close spa-S2, spa-S4, spa-S5 (and spa-S3 if Path A is chosen, since Pages adds Referrer-Policy by default).
4. **CSP tightening (jcstream-template-author).** Audit 11 Tier 1 (R1.1, R1.2) calls for externalizing the inline IIFEs to `/static/main.js` and `/static/map.js` and hash-pinning them in `script-src`. The `_headers` CSP currently allows `script-src 'self' https://giscus.app` but does not include `'unsafe-inline'`, which means the inline IIFEs will be blocked the moment the HTTP CSP goes live. **This is a load-bearing pre-cutover step**: either add `'unsafe-inline'` to the `_headers` CSP (matching the suggested meta-CSP in audit 11 R0.2), or land R1.1/R1.2 before activating the new policy. Otherwise the site will paint without functional JavaScript. Recommended: add `'unsafe-inline'` to the script-src in `_headers` as a pre-cutover edit, then drop it after R1.1/R1.2 lands.

## Technical notes

### Verification curl recipes

Before cutover:

```
curl -sI https://www.aretheyinjail.com/        # baseline headers
dig +short www.aretheyinjail.com               # current CNAME target
```

After Path A activation (compare against the audit 11 inventory):

```
curl -sI https://www.aretheyinjail.com/        # expect:
  # - Content-Security-Policy: ... frame-ancestors 'none' ...
  # - X-Frame-Options: DENY
  # - Permissions-Policy: accelerometer=(), ...
  # - Cross-Origin-Opener-Policy: same-origin
  # - Cross-Origin-Resource-Policy: same-origin
  # - Strict-Transport-Security: max-age=63072000; includeSubDomains
  # - (and no X-GitHub-Request-Id)
```

After Path B activation:

```
curl -sI https://www.aretheyinjail.com/        # expect same as Path A
                                                # but also still see GH Pages
                                                # quirks (Etag formats, etc)
                                                # because origin is unchanged.
```

### Where the policy edits would land in the repo

If a future tightening edits the CSP:

- Path A: edit `/home/user/JCStream/_headers` line 26 (the `/*` block's `Content-Security-Policy:` line). Commit. Next sweep deploys via Pages Git integration.
- Path B: edit the `SECURITY_HEADERS` constant in the Worker source. Redeploy via Wrangler or the dashboard. **The `_headers` file is inert under Path B; editing it has no effect**, which is why cf-mig-6 recommends deleting it under Path B.

### Why not Workers Static Assets

Per the Pages-to-Workers migration guide (https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/), Cloudflare offers a path from Pages to Workers Static Assets via `wrangler.jsonc` with an `assets.directory` binding. This is a forward-looking option, not a current requirement. JCStream is not a Wrangler project today (no `wrangler.jsonc`, no `package.json`), and adopting Wrangler would add a Node.js dependency to the build pipeline that the rest of the project does not need. Workers Static Assets reads `_headers` in the same syntax, so the policy is portable if the owner later chooses to migrate. Treat it as a deferred decision.

### Schema-consistency check on the current `_headers`

The current file declares `Cross-Origin-Resource-Policy: same-origin` in the `/*` block (line 33) and then `Cross-Origin-Resource-Policy: cross-origin` in the `/photos/*` block (line 41). Per Cloudflare's header-rule precedence, a more specific path block overrides the `/*` block for matching URLs. The `/photos/*` directive correctly relaxes CORP for the public photo tree so syndication tools can hotlink them; the global same-origin posture covers everything else. This is intentional and correct.

The `Access-Control-Allow-Origin: *` directives on `/photos/*`, `/static/*`, `/feed.xml`, `/booked.xml`, `/released.xml`, `/search.json`, and `/dispatches.json` similarly relax CORS for syndication while the global block (which omits ACAO) lets the Pages default of `Access-Control-Allow-Origin: *` (per https://developers.cloudflare.com/pages/configuration/serving-pages/) apply to root HTML responses. This is also correct - JCStream is a public-records mirror and intentional permissive CORS is the documented posture.

No syntax errors observed. No deprecated directives observed.

## What this audit explicitly does not propose

- No change to `_headers` file syntax or content. Path A activation makes the file effective as-is.
- No change to `.github/workflows/sweep.yml`. The deploy-pages@v4 step stays in place until the owner is confident in the cutover.
- No change to `web/build.py`. The `CNAME` and `.nojekyll` writes are harmless on Pages.
- No DNS pre-staging. The DNS cutover happens at A3 atomically; pre-creating records would race with the Pages auto-configuration.
- No automation. This runbook documents what the owner does in the Cloudflare dashboard; it does not propose a Terraform / IaC equivalent. The cutover is a one-time operation and not worth the IaC overhead for a single project.

## End of audit
