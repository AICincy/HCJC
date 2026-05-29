# JCStream ORC Curator
---
name: jcstream-orc-curator
description: "ORC mapping and explainer curation skill for JCStream"
applyTo:
	- "scraper/orc.py"
	- "data/orc_offenses.json"
---

Purpose
- Curate Ohio Revised Code mappings, degrees, and explainers used by the site.

Use when
- "ORC", "orc_offenses.json", "degree", "tier", "explainer" appears in the prompt.

What this skill does
- Inspect `scraper/orc.py` and `data/orc_offenses.json` to resolve unmapped codes.
- Propose vetted human-readable explainers and degree mappings.

Checks
- Do not alter canonical `orc_offenses.json` without a paired review; prefer curated suggestions.
- Run `python -m pytest -q tests/test_orc.py` for changes affecting mapping logic.

Files to inspect
- `scraper/orc.py`, `data/orc_offenses.json`, `web/build.py` (explainers loader).

Triggers
- "fix ORC tier/degree", "add explainer", "code shows ?/unknown".
