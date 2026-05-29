# JCStream Accessibility Auditor
---
name: jcstream-a11y-auditor
description: "Accessibility auditing and fixes for JCStream"
applyTo:
	- "web/templates/**"
	- "web/static/**"
---

Purpose
- Audit and fix accessibility issues (WCAG, ARIA, keyboard, focus, contrast).

Use when
- "a11y", "accessibility", "focus ring", "contrast", "ARIA" appears in the prompt.

What this skill does
- Identify regressions, propose minimal fixes, and add tests where possible.
- Prioritize keyboard and screen-reader behavior.

Checks
- Run relevant unit tests and manual checks; verify `prefers-reduced-motion` guards.
- Prefer small, incremental fixes with clear test coverage.

Files to inspect
- `web/templates/`, `web/static/style.css`, `web/build.py`.

Triggers
- "focus ring missing", "alt text", "keyboard nav", "aria".
