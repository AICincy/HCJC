# JCStream Build Helper Author
---
name: jcstream-build-helper-author
description: "Build helper and Jinja globals skill for JCStream"
applyTo:
	- "web/build.py"
	- "web/templates/**"
---

Purpose
- Maintain build helpers, Jinja `env.globals`, and the static site build (`web/build.py`).

Use when
- "build.py", "env.globals", "css_version", "build" appear in the prompt.

What this skill does
- Add or update Jinja globals and build-time helpers with tests.
- Keep changes minimal and well-cited in source locations.

Checks
- Run `JCSTREAM_SITE_BASE_URL="" python -m web.build` after changes.
- Run the subset of tests referenced by the modified helper.

Files to inspect
- `web/build.py`, `web/templates/`, `web/static/`.

Triggers
- "register a Jinja global", "compute bond/tier", "css_version".
