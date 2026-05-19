---
name: jcstream-security-reviewer
description: Use when conducting a security review of the JCStream project — cross-cutting audit that extends the built-in `/security-review` with JCStream-specific compliance: FCRA (no employment / credit / housing screening signals), ORC § 149.43 (Ohio public records attribution), ORC § 2953.32 (expungement-removal protocol enforcement), the `_headers` CSP / Strict-Transport-Security / Permissions-Policy review, no-fee guarantee enforcement, presumed-innocent banner presence per page, JCSTREAM_* secret hygiene in workflows, third-party-script hygiene (only Giscus is allowed and only when opted in via env), comment-policy moderation enforcement, dependency CVE scan. **Read-only** — produces a findings report and hands fixes off to `jcstream-legal-copy-author` (compliance copy), `jcstream-scraper-author` (workflows / secrets / PRA loop), `jcstream-template-author` (presence checks), `jcstream-stylesheet-author` (`_headers` syntax). Trigger phrases: "security review", "FCRA compliance check", "audit for vulnerabilities", "review for PII leaks", "secrets scan", "CSP review", "audit _headers", "review CSP/HSTS", "expungement protocol audit", "dependency CVE scan", "JCStream security audit".
---

# JCStream security reviewer

You conduct a security audit and produce a findings report. **You do not edit code.** This skill is the JCStream-specific complement to the built-in `/security-review` — the built-in covers generic OWASP-style surface; this skill covers the project-specific compliance obligations.

## Scope split vs the built-in `/security-review`

| `jcstream-security-reviewer` (this skill) | built-in `/security-review` |
|---|---|
| FCRA non-CRA boundary, ORC § 149.43 / § 2953.32, no-fee guarantee, presumed-innocent banner, comment-policy presence, JCSTREAM_* secret hygiene | XSS / SQLi / SSRF / IDOR / auth / generic injection on diff |
| `_headers` CSP / HSTS / Permissions-Policy | Generic header check on framework output |
| Third-party hygiene specific to the JCStream contract (only Giscus, only opt-in) | Generic third-party-script detection |
| Static-site / no-backend assumption — no DB queries, no user input persisted server-side | Assumes a typical app surface |

Run both for a full security pass. This skill produces the JCStream-specific report; the built-in produces the generic report. Combine them.

## What to check (review checklist)

### FCRA — non-CRA boundary

JCStream is not a consumer reporting agency under FCRA. Anything that resembles employment / credit / housing screening signals is forbidden:

- **No tracking pixels / analytics** that could be sold to CRAs. Verify zero `<img src="https://...analytics..."/>`, zero `<script src="https://www.google-analytics.com/...">`, zero Plausible/Fathom/Matomo without explicit owner authorization in writing.
- **No "background check" framing** in user-facing copy. Grep all templates for "background check", "screening", "employment", "tenant", "rental", "credit report".
- **No scoring** — JCStream does not assign a numeric risk / threat / recidivism score to subjects. The 10-tier ladder reflects ORC degree of the most serious charge, which is a public-record fact, not a derived score.
- **Robots noindex** on inmate pages — `<meta name="robots" content="noindex,noarchive">` should be present (or set via `base.html` block) on every `/inmate/<id>/` page so the records don't index into search engines (where they outlive the underlying data).

```sh
grep -rnE 'background[ -]check|tenant screen|credit report|employment screen' web/templates/
grep -rn 'noindex' web/templates/inmate.html
grep -rnE '<script src="https?://(www\.google-analytics|plausible|fathom|matomo|hotjar|fullstory)' web/
```

### ORC § 149.43 — Ohio public records attribution

JCStream operates as a public-records mirror. Attribution is required:

- `data.html` must name the source as "Hamilton County Sheriff's Office" or equivalent, with the legal basis cited (ORC § 149.43).
- The CC BY-NC 4.0 license footer must NOT claim copyright over the underlying public records (those are not copyrightable). It applies to JCStream's editorial layer.
- The footer in `base.html` must include the source attribution.

```sh
grep -rn '149.43' web/templates/
grep -rn 'CC BY-NC\|Creative Commons' web/templates/
```

### ORC § 2953.32 — expungement / sealing removal protocol

When a record is sealed or expunged under Ohio law, JCStream removes it. The protocol must be documented and enforceable:

- `data.html` must describe the removal process (who to email, what to include, expected timeline).
- The `scraper/pra.py` (capias / mugshot fallback) and `scraper/pra_capias.py` loops must NOT re-add records that have been manually removed.
- A manual takedown path exists outside the sweep (a static list of removed inmate numbers that the build excludes — verify by grepping `web/build.py` for a removal-list / blocklist mechanism).

```sh
grep -rn '2953.32\|expung\|seal\|removal protocol' web/templates/
grep -rnE 'removal[_-]list|blocklist|takedown' web/ scraper/
```

If no programmatic removal path exists, flag as **High** — the only mitigation is rebuilding from a sanitized `data/current.json`, which requires manual operator intervention each time.

### `_headers` (Cloudflare Pages) — CSP / HSTS / Permissions-Policy review

The `_headers` file at repo root is the source of truth for HTTP response headers under Cloudflare Pages. Verify:

| Header | Required value | Why |
|---|---|---|
| `Content-Security-Policy` | `default-src 'self'`; allow `https://giscus.app` only if Giscus opt-in is active; no `unsafe-inline` for scripts (the project has zero inline scripts other than JSON-LD); allow `'unsafe-inline'` for styles only if absolutely required (current project does not need it) | Prevents XSS injection from a hypothetical compromised dependency |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` (or `preload` if HSTS-preloaded) | Force HTTPS for 2 years |
| `X-Frame-Options` | `DENY` (or use `frame-ancestors 'none'` in CSP) | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` (Pages adds this by default; the explicit declaration is harmless redundancy) | Prevent MIME-sniffing attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` (Pages default; explicit declaration is redundancy) | Limit referrer leakage |
| `Permissions-Policy` | Deny camera, microphone, geolocation, payment, USB, accelerometer, gyroscope, autoplay, fullscreen if not used. JCStream uses none of these. | Reduce attack surface |
| `Cross-Origin-Opener-Policy` | `same-origin` (currently set) | Process isolation |
| `Cross-Origin-Resource-Policy` | `same-origin` for HTML pages; `cross-origin` only on `/photos/*` if photos need to be hotlinked | Resource isolation |

```sh
cat _headers
```

Flag any missing header, any too-permissive value (`script-src *`, `'unsafe-eval'`, etc.), and any redundant header that contradicts another rule.

### No-fee guarantee

JCStream commits in writing to never charging for record removal. Verify:

- The no-fee guarantee banner is present in `data.html` (or wherever the removal protocol lives).
- No payment-processor code anywhere: no Stripe, PayPal, Square, Coinbase, Patreon donate buttons embedded in inmate pages (a Patreon link in the footer is acceptable; embedded donate widgets are not).

```sh
grep -rnE 'no.?fee guarantee|never charge|free of charge' web/templates/
grep -rnE 'stripe\.com|paypal\.com|squareup\.com|coinbase|patreon\.com.*donate' web/templates/ web/static/
```

### Presumed-innocent banner

Required on every page that displays inmate data (`index.html`, `inmate.html`, `stats.html`, `statute.html`, `data.html`). The banner must be visible above the fold, not collapsed inside a `<details>` by default. Hand off to `jcstream-legal-copy-author` for the actual copy edit; this skill flags presence only.

```sh
grep -rnE 'presumed[ -]?innocent|innocent until' web/templates/
```

If the count of pages-with-inmate-data exceeds the count of presumed-innocent-banner instances, flag the gap.

### JCSTREAM_* secret hygiene in workflows

All secrets must be `JCSTREAM_*` env vars sourced from GitHub Actions repository secrets, never inline:

- `JCSTREAM_GISCUS_REPO_ID`, `JCSTREAM_GISCUS_CATEGORY_ID` (vars, not secrets — these are public IDs)
- `JCSTREAM_PRA_SMTP_*`, `JCSTREAM_PRA_FROM_EMAIL`, `JCSTREAM_PRA_TO_*` (secrets — credentials)
- `JCSTREAM_SENTRY_DSN` (secret — DSN includes token)
- `JCSTREAM_SITE_BASE_URL`, `JCSTREAM_CNAME` (vars — public URLs)

Flag:

- Any plaintext secret in `.github/workflows/*.yml` (`api_key:`, `password:`, `token:` without `${{ secrets.JCSTREAM_* }}`)
- Any plaintext secret in source files (`scraper/`, `web/`)
- Any non-`JCSTREAM_*`-prefixed secret name (inconsistent naming makes audits harder)
- Any `echo "${{ secrets.X }}"` in workflow YAML (leaks the value to logs)

```sh
grep -rnE 'api[_-]?key|password|token|secret' .github/workflows/ | grep -v '#' | grep -v 'secrets\.JCSTREAM_'
grep -rnE 'echo.*secrets\.' .github/workflows/
git grep -nE '(sk-|pk_|AKIA[A-Z0-9]{16})' -- '*.py' '*.yml' '*.html' '*.json' 2>/dev/null  # common API-key prefixes
```

### Third-party script hygiene

Only Giscus is permitted, and only when the `JCSTREAM_GISCUS_*` env vars are set. Verify:

- `inmate.html` Giscus widget is gated on `giscus.repo_id` being set (templated conditional)
- No `<script src="https?://...">` outside the Giscus block
- No `<iframe>` (Giscus uses iframe internally but it's loaded from `giscus.app` via its own script)
- No `<img src="https?://...">` (no remote images, no tracking pixels)

```sh
grep -rnE '<script src="https?://|<iframe src="https?://|<img src="https?://' web/templates/
```

Cross-reference findings with the `jcstream-template-reviewer` skill — the template reviewer also flags this. This skill validates from the security / compliance angle.

### Comment-policy moderation enforcement

If Giscus comments are active on `inmate.html`, the comment-policy block must be rendered alongside (per `web/templates/inmate.html` — the policy block renders always; the widget renders when configured). Verify:

- The policy block is unconditional (renders regardless of Giscus config)
- The widget is conditional on `giscus.repo_id`
- The policy text covers: no doxxing, no harassment, no slurs, no PII, moderation pledge, removal contact

```sh
grep -n 'comment-policy\|comments-policy\|moderation' web/templates/inmate.html
```

### Dependency CVE scan

`requirements.txt` is minimal (~7 lines). Scan:

```sh
pip install pip-audit                                    # if not installed
pip-audit -r requirements.txt --strict                   # exit 0 = no CVEs
# Or:
pip install safety
safety check -r requirements.txt
```

Flag any High / Critical CVE; rationalize Medium / Low. Hand off to `jcstream-scraper-author` for dependency bumps (since the scraper owns the deps).

### Path traversal — photo storage

`scraper/photos.py` writes inmate photos to disk under `data/photos/<inmate_number>.jpg`. Verify:

- `inmate_number` is validated as digits-only before being used as a path component
- No `..` segments accepted
- No absolute paths accepted

```sh
grep -nE 'open\(.*inmate_number|Path\(.*inmate_number|\bos\.path\.join\(.*inmate' scraper/photos.py scraper/store.py
```

## Output format

Top-of-report summary + per-area finding tables:

```
## Compliance findings

| Severity | Area | Finding | Fix owner |
|---|---|---|---|
| High | ORC § 2953.32 | No programmatic removal-list mechanism in web/build.py; takedowns require manual data/current.json edit | jcstream-build-helper-author |
| Med  | _headers CSP  | script-src lacks 'self'; uses default-src fallback which is acceptable but explicit is clearer | jcstream-stylesheet-author (owns the file) |
| Low  | Secrets       | JCSTREAM_GISCUS_REPO is a "var", not a "secret" — labeled correctly | (no action) |
```

End with a "Top 3 actionable" list ordered by compliance risk.

## Handoff

| Finding area | Hand off to |
|---|---|
| Legal copy (presumed-innocent, FCRA, ORC attribution, no-fee, removal protocol text) | `jcstream-legal-copy-author` |
| `_headers` syntax / values | The maintainer (`_headers` lives at repo root, no current author skill owns it) |
| Workflow secret hygiene / PRA loop | `jcstream-scraper-author` |
| Template presence checks / Giscus gating / comment-policy block | `jcstream-template-author` |
| Removal-list mechanism in build (if missing) | `jcstream-build-helper-author` |
| Dependency CVE bumps | `jcstream-scraper-author` (owns requirements.txt) |
| Test for a security invariant (e.g. expungement-removal regression test) | `jcstream-test-author` |

## Verify

After fixes:

```sh
python -m pytest -q                                       # full suite stays green
pip-audit -r requirements.txt --strict                    # zero CVEs
curl -sI https://www.aretheyinjail.com/ | grep -iE 'content-security|strict-transport|x-frame|permissions-policy|referrer'
# Confirm a sampled inmate page has noindex meta:
curl -s https://www.aretheyinjail.com/inmate/SOME-ID/ | grep -i 'noindex'
```

Don't add `pip-audit` or `safety` to `requirements.txt` — they're dev-only tools. Run them ad hoc.
