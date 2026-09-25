# Security Policy

## Supported Versions

Active versions receiving security updates:

| Version | Status | Notes |
| ------- | ------ | ----- |
| 0.1.0+ | Actively maintained | Current development branch; all security patches applied to main |

The project uses continuous deployment; once a fix lands in `main`, it deploys
within the next sweep cycle (typically within 45 minutes). No legacy versions
are maintained.

## Security Architecture

### Evidence and Integrity

The project implements several security controls for public-records handling:

- **Append-only evidence log** (`data/waf_block_log.json`): SHA-256 hash-chain
  prevents silent tampering with firewall block records. Chain is verified on
  every CI run.
- **Deterministic builds**: Consecutive builds with identical inputs produce
  byte-identical output. Verified via `diff -qr` in CI.
- **No database on request path**: Published site reads version-controlled JSON
  only. No runtime secrets, no third-party APIs on the public site.
- **Architectural isolation**: Supabase access isolated to `backend/` service;
  Python pipeline has zero Supabase dependencies. Enforced by
  `tests/test_architectural_compliance.py`.

### Secrets Management

- GitHub Actions credentials are short-lived (revoked post-merge).
- No secrets committed to the repository (verified in CI via `git-secrets`).
- `backend/.env` is not version-controlled (`.gitignore` enforced).
- Local development uses `.env.example` as template only.

### Dependencies

- All production dependencies pinned to exact versions in `requirements.txt` and
  `pyproject.toml` (kept synchronized).
- Development dependencies (ruff, mypy, pytest) versioned separately in
  `pyproject.toml`.
- `pip-audit` runs in CI to flag transitive dependency vulnerabilities.

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

Instead:

1. Email the repository owner with:
   - Description of the vulnerability
   - Affected component(s) and version(s)
   - Steps to reproduce (if applicable)
   - Proposed fix (if you have one)

2. Allow 7 days for initial response and triage.

3. Once patched and deployed, we will:
   - Credit the reporter in the commit (if desired)
   - Publish an advisory once the fix is live
   - Include details in this file under "Resolved Issues"

## Known Limitations

### Data Accuracy

- Source data is the HCSO inmate roster and Cincinnati Open Data feeds.
- Parsing failures are rare but possible; detail-page names use 5-tier fallback
  (see `CLAUDE.md` for full list).
- Photo extraction validates JPEG headers but cannot guarantee image quality or
  completeness.

### Availability

- Sweeps are scheduled twice per hour at :07 and :37 UTC (best-effort);
  GitHub Actions delivery can still drop or delay runs, including multi-hour
  gaps during incidents.
- Site may lag up to 45 minutes behind live bookings during normal operation.
- WAF throttling is documented and logged, never evaded (no proxy rotation).

### Privacy and FCRA Compliance

- This site does NOT furnish consumer reports as defined in 15 U.S.C. 1681a.
- Do not use this data for employment, credit, insurance, housing, or tenant
  screening decisions.
- All pages carry `noindex, noarchive` robots directives; social preview cards
  are site-level only.
- Corrections and sealing/expungement removals are free via GitHub issues.

## Verified Security Practices (2026-09-24)

- ✅ Zero credentials in Python pipeline
- ✅ No hardcoded secrets or API keys
- ✅ Supabase isolation to Node backend only
- ✅ Append-only evidence log with hash-chain verification
- ✅ No third-party trackers on public site
- ✅ No unvalidated user input accepted
- ✅ HTTPS enforced via GitHub Pages custom domain
- ✅ Tests isolated; no production data written during CI
- ✅ `git-secrets` pre-commit checks enabled
- ✅ Dependency pins synchronized across `requirements.txt` and `pyproject.toml`

## Support

For security questions or concerns about this project's compliance with ORC
149.43 (Public Records Act), open an issue at
https://github.com/AICincy/HCJC/issues (all inquiries are free; no fee applies).
