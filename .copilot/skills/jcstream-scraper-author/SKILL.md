# JCStream Scraper Author
---
name: jcstream-scraper-author
description: "Scraper and sweep maintenance skill for JCStream"
applyTo:
	- "scraper/**"
	- ".github/workflows/sweep.yml"
---

Purpose
- Maintain scrapers, sweep logic, and Open Data feed integrations.

Use when
- "scraper", "sweep", "HCSO", "open data", "detail watchdog" appears in the prompt.

What this skill does
- Diagnose and fix scraper failures; respect the degraded-roster guard.
- Document WAF blocks; do not bypass the guard by lowering thresholds.

Checks
- Run `python -m pytest -q tests/test_sweep.py` for sweep-related fixes.
- Verify behavior against `scraper/sweep.py` and `scraper/sweep_guards.py`.

Files to inspect
- `scraper/`, `.github/workflows/sweep.yml`, `data/`, `web/build.py`.

Triggers
- "rate-limit", "WAF", "sweep failed", "roster frozen", "detail watchdog".
