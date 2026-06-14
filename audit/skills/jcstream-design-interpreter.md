# Audit — jcstream-design-interpreter

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-design-interpreter/SKILL.md
- **Paired agent**: .claude/agents/jcstream-design-interpreter.md
- **Verdict**: Yellow
- **One-line summary**: Output contract and mapping table verify cleanly, but the playbook invents helper names, overstates the loaded fonts, and omits three active porting primitives (lightbox/inert, view-toggle, data-* filter hooks).

## A. Drift
- **Invented helper names.** SKILL.md:23 cites "(`fmtAge`, `daysSince`, `bondContext`, …)" as data-need examples. None exist in `web/build.py`; actual `env.globals` are `bond_context`, `display_date`, `timeline_markers`, `primary_charge`, `recent_booked_inmates`, `similar_by_statute`, etc. (`web/build.py:103-116`). Reads as JSX camelCase that survived the port; misleading as a project reference.
- **Font claim overstated.** SKILL.md:30 says "the project uses Geist/Inter + JetBrains Mono via Google Fonts (preconnected in `base.html`)". `base.html:22-24` only preconnects/loads `Inter` + `JetBrains+Mono`; `Geist`/`Geist Mono` appear only as CSS fallbacks (`style.css:51-53`) and are never fetched. A new design relying on Geist would silently fall through to Inter.
- **`.ut-*` mapping table reads as current state.** SKILL.md:21,34-50 still phrase "the modern-utility direction we ported" as ongoing. Grep across `web/` finds zero `.ut-*` selectors except a stray `.ut-muted` at `style.css:1061`. The table is fine as a worked example but should be marked historical.

## B. Coverage gaps
- **Lightbox + `inert` focus management** (`base.html:78-150`, `style.css:1364-1397`): one shared `<div class="lightbox" role="dialog" aria-modal="true" hidden>`, JS swaps the image, siblings get `inert`, Tab-cycler fallback. Any image-detail design must reuse this dialog rather than create a parallel one.
- **View-toggle pattern** (`index.html:192`, `base.html:197-213`, `style.css:478-482`): `body.is-table` flip with `aria-pressed` + `localStorage`. A roster-listing redesign that drops the toggle button or omits the table-mode CSS branch silently regresses the site.
- **`data-*` filter hooks** (`_card.html:5`, `index.html:176-189`, `base.html:222-241`): client-side filter bar keys off `data-tier`/`data-chap`/`data-name`/`data-search` + `data-filter`. New card markup without these attributes breaks search.
- **`css_version` cache-bust** (`web/build.py:100`): sha256 of style.css contents — CLAUDE.md:44-45 explicitly warns not to key it off the data timestamp. Worth one playbook line so a port doesn't invent a parallel scheme.
- **`base.html` override blocks** (`base.html` defines `title`, `body_class`, `sr_h1`, `content`): a design port should extend these, not duplicate `<head>`. Not mentioned.
- **Paired agent missing legal-copy handoff** (`agents/jcstream-design-interpreter.md:16-20`): redesigns touching the FCRA banner / disclaimer / removal protocol footer should route to `jcstream-legal-copy-author`.

## C. Trigger-phrase quality
- Current description (paraphrased): fires on Figma export, JSX mockup, screenshot, design zip, or hand-drawn spec; lists "port this design", "implement the mockup", "translate the Figma", "from this screenshot".
- Issues: coverage is reasonable but misses common short forms — "redesign the homepage from this", "build from this mockup", "here's a screenshot of the new …", "convert this JSX". "From this screenshot" alone is a weak match for ambient phrasings like "based on this PNG".
- Proposed rewording: append "build from this mockup", "convert this JSX", "redesign … from this spec", "here's a Figma/PNG/screenshot of the new …" to the trigger examples.

## D. Applicability
- Live — the active stylesheet still calls itself "Modern utility theme" (`style.css:2`), the `.ut-*` mapping table is the residue of a real port, and design work cycles regularly; keep the skill, do not retire.

## Recommended fixes (priority order)
1. Replace `fmtAge`/`daysSince`/`bondContext` with real helper names from `web/build.py:103-116` (`bond_context`, `display_date`, `timeline_markers`, etc.).
2. Add a "Project primitives a port must preserve" section: lightbox+inert (`base.html:78-150`), view-toggle (`base.html:197-213`), `data-*` filter attributes (`_card.html:5`), `css_version` cache-bust (`build.py:100`), `base.html` override blocks.
3. Correct the font note at SKILL.md:30 — only Inter + JetBrains Mono are fetched; Geist is a fallback only.
4. Reword the `.ut-*` mapping preamble so the table reads as a historical worked example rather than the current selector inventory.
5. Add `jcstream-legal-copy-author` to the paired agent's downstream handoff list.
6. Broaden trigger phrases per section C.
