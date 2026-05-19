# Audit Pass 2 — jcstream-design-interpreter

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All six pass-1 fixes landed cleanly with accurate `file:line` citations and no new drift.

## Pass-1 recommendation status
1. Replace invented helper names with real `env.globals`: **Done** — SKILL.md:23 now lists `bond_context`, `display_date`, `timeline_markers`, `primary_charge`, `primary_chapter`, `primary_tier`, `recent_booked_inmates`, `similar_by_statute`, `tier_counts`, `avatar_initials`, `card_data`, `approx_age`, all matching `web/build.py:103-127`.
2. Add "Project primitives a port must preserve" section: **Done** — SKILL.md:34-41 covers lightbox+inert (`base.html:78-150` confirmed, dialog at base.html:78), view-toggle (`base.html:197-216` confirmed at base.html:198-216), `data-*` filter hooks (`_card.html:5` confirmed, attrs verbatim), `css_version` cache-bust (`build.py:96-101` matches build.py:100), and base.html override blocks (matches base.html:6, 32, 66, 67).
3. Correct font note (Inter + JetBrains Mono only): **Done** — SKILL.md:30 explicitly says "the project fetches **only Inter + JetBrains Mono**" and notes Geist is fallback-only in `style.css:51-53` (confirmed by grep — Geist appears only in `--font-sans`/`--font-serif`/`--font-mono` fallback chains).
4. Mark `.ut-*` mapping as historical: **Done** — SKILL.md:21 leads with "historical worked example", SKILL.md:43 heading is "Reference mapping (historical worked example…)", explicitly noting "those selectors no longer exist in the live CSS (only a stray `.ut-muted` remains at `style.css:1061`)" — confirmed by grep.
5. Add `jcstream-legal-copy-author` to paired agent handoff: **Done** — `agents/jcstream-design-interpreter.md:21` adds "FCRA banner / disclaimer / removal-protocol footer copy → **jcstream-legal-copy-author**".
6. Broaden trigger phrases: **Done** — SKILL.md:3 now includes "build from this mockup", "convert this JSX", "redesign the homepage from this", "redesign … from this spec", "here's a Figma/PNG/screenshot of the new …", "based on this PNG".

## New issues found in pass 2
- Minor citation slip: SKILL.md:38 cites view-toggle at "`base.html:197-216`" but `#view-toggle` button is actually rendered in `index.html:192` (toggle script body is in `base.html:198-216`). Pass-1 had the same dual cite; not a regression, just imprecise. Skim-level only.
- SKILL.md:23 cites `build.py:103-130`; actual helper registrations span `build.py:103-127` with no gap, so the range is one or two lines wider than strictly needed but not wrong.

## Pass-2 lens checks
- **Drift**: Clean — every cited symbol (`bond_context`, `card_data`, `primary_chapter`, `css_version`, `data-photo`/`data-photo-cap`/`data-photo-alt`, `body.is-table`, `jcs-view`, `inert`) verified in source.
- **Coverage**: Clean — the five primitives added in SKILL.md:34-41 close the gaps pass-1 flagged; legal-copy handoff is now wired into the paired agent.
- **Triggers**: Clean — short forms ("convert this JSX", "build from this mockup", "based on this PNG", "redesign … from this spec") are present in SKILL.md:3 description, matching ambient phrasings pass-1 worried about.
- **Applicability**: Live — `.ut-muted` residue and the `style.css:2` "Modern utility theme" header still signal an active port surface; skill stays relevant for the next design intake.
