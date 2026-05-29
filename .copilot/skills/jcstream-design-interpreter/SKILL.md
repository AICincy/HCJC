# JCStream Design Interpreter
---
name: jcstream-design-interpreter
description: "Design-to-implementation guidance skill for JCStream"
applyTo:
	- "web/templates/**"
	- "web/static/**"
---

Purpose
- Translate design mocks and assets into faithful, accessible template/CSS changes.

Use when
- "redesign", "mockup", "Figma", "screenshot", "convert JSX" appears in the prompt.

What this skill does
- Produce minimal implementation plans that preserve project primitives (lightbox, view-toggle, css_version).
- Do not change global layout without explicit authorization.

Checks
- Verify templates and CSS build cleanly; run `python -m web.build` after changes.

Files to inspect
- `web/templates/`, `web/static/style.css`, `web/build.py`.

Triggers
- "convert this mockup", "build from this mockup", "redesign the homepage".
