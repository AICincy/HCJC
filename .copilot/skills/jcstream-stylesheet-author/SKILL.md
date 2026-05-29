# JCStream Stylesheet Author
---
name: jcstream-stylesheet-author
description: "Stylesheet author skill for JCStream"
applyTo:
	- "web/static/**"
	- "web/templates/**"
---

Purpose
- Author and maintain CSS rules in `web/static/style.css` and related UI primitives.

Use when
- "stylesheet", "style.css", "F3 chip", "lightbox", "ladder", "tier color" appear in the prompt.

What this skill does
- Identify the minimal CSS change to fix visual regressions or accessibility regressions.
- Preserve `css_version` cache-bust semantics; never change the cache key approach.

Checks
- Verify visual change is scoped and progressive; prefer additive changes.
- Run local `python -m web.build` to ensure assets bundle and hash update.

Files to inspect
- `web/static/style.css`, `web/templates/base.html`, `web/static/*` assets.

Triggers
- "recolor", "print layout", "lightbox", "focus ring", "ladder grid".
