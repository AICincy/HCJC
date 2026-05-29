# JCStream Template Author
---
name: jcstream-templates
description: "Template author skill for JCStream"
applyTo:
	- "web/templates/**"
	- "web/**"
---

Purpose
- Help maintain and update Jinja templates, micro-partials, and template-related build helpers.

Use when
- "template", "inmate.html", "base.html", "Jinja", "render" appears in the prompt.

What this skill does
- Locate template usage in `web/templates/` and `web/static/` helpers in `web/build.py`.
- Recommend minimal, reversible edits; do not change site design without explicit authorization.

Checks and tests
- Run `python -m pytest -q tests/test_templates.py` when adding template logic.
- Verify `JCSTREAM_SITE_BASE_URL="" python -m web.build` if rendering changes.

Quick workflow
1. Reproduce the issue with a small example template or test.
2. Make a minimal change in the template file in `web/templates/`.
3. Run the specific tests and a local build.
4. Commit to the feature branch.

Files to inspect
- `web/templates/`, `web/_includes/`, `web/static/`, `web/build.py`

Triggers
- "render error", "template broke", "inmate page", "missing field".
