# JCStream Sweep Debugger
---
name: jcstream-sweep-debugger
description: "Sweep debugging and WAF/runbook skill for JCStream"
applyTo:
	- "scraper/**"
	- "data/waf_block_log.json"
	- ".github/workflows/sweep.yml"
---

Purpose
- Diagnose sweep failures, WAF blocks, and the degraded-roster guard behavior.

Use when
- "sweep", "roster frozen", "WAF", "ROSTER FROZEN", "sweep looks degraded" appears in the prompt.

What this skill does
- Inspect sweep logs, Actions run output, and `scraper/` code to locate the failure path.
- Document WAF blocks in `data/waf_block_log.json` and do not attempt evasive fixes without explicit consent.

Checks
- Run `python -m pytest -q tests/test_sweep.py` for sweep-related checks.
- Follow the Runbook steps in `audit/14_hcso_waf.md` when a WAF is suspected.

Files to inspect
- `scraper/`, `.github/workflows/sweep.yml`, `data/`, `audit/14_hcso_waf.md`.

Triggers
- "roster frozen", "WAF block", "sweep bailed", "list sweep looks degraded".
