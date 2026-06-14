# Audit — `security-review` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: Medium
- **Recommendation**: Keep enabled

## What it does
Completes a security review of the pending changes on the current branch.

## Fit for JCStream
JCStream's attack surface is narrow but non-trivial. There's no public auth or user input, but the scraper ingests untrusted HTML from HCSO into Jinja (autoescape is on via `select_autoescape(["html","xml"])` in `web/build.py`), parses untrusted image bytes via Pillow (`scraper/photos.py`), sends outbound SMTP with env-driven addressing (`scraper/pra.py`, `pra_base.py`), and runs in GitHub Actions with `contents: write` plus PRA SMTP secrets. A targeted security pass on diffs touching these areas would find real issues; a pass on template/CSS-only diffs would be noise.

## Realistic triggers in this project
- New scraper field rendered into a template (verify autoescape is not bypassed with `|safe`/`Markup`)
- Changes to `scraper/photos.py` or any path passing bytes to `PIL.Image.open` (decompression-bomb / malformed-image handling)
- Edits to `scraper/pra*.py` or `pra_base.send_smtp` (header injection, recipient-from-env, TLS posture, secret logging)
- Changes to `.github/workflows/sweep.yml` or `pra_daily.yml` (permissions scope, secret echoing, third-party action pinning)
- New outbound HTTP target in `scraper/client.py` or open-data feeds (SSRF surface, URL construction)
- Anything writing to `docs/` from external input (path traversal)

## Risk
Read-only review skill; no risk to invoke.

## Recommendation rationale
The scraper-to-static-site pipeline still has the classic untrusted-input concerns — HTML into templates, image bytes into Pillow, env-driven SMTP, and Actions secrets — so `security-review` is genuinely useful when diffs touch `scraper/`, `web/build.py`, or `.github/workflows/`. It's overkill for template/CSS/copy edits; the owner should invoke it selectively on the triggers above rather than every change.
