# JCStream Legal Copy Author
---
name: jcstream-legal-copy-author
description: "Legal and policy copy authoring skill for JCStream"
applyTo:
	- "web/templates/**"
	- "audit/**"
---

Purpose
- Draft and maintain legal, accessibility, and policy copy surfaced in the site (disclaimers, PRA text, interruption notices).

Use when
- "disclaimer", "PRA", "terms", "notice", "mandamus", "accessibility" appears in the prompt.

What this skill does
- Produce accurate, concise legal text and suggest placement in templates. Prefer conservative language.

Checks
- Do not alter legal copy without owner signoff for policy-sensitive wording.
- Run site build to verify placement and formatting.

Files to inspect
- `web/templates/`, `web/build.py`, `audit/` notes.

Triggers
- "update disclaimer", "PRA email", "interruption notice", "accessibility statement".
