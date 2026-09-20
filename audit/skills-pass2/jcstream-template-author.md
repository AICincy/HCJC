# Audit Pass 2 — jcstream-template-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 fixes landed; line cites verify on the live files and the new contracts (feed.xml, lightbox/tier `data-*`, Giscus, `noindex,noarchive`) are documented.

## Pass-1 recommendation status
1. Refresh every line cite (currentFilters 228-232, view-toggle handler 197-216, lightbox open/close/fallback 125-156, env globals 79-144): **Done** — SKILL.md:25 cites `base.html:228-232` (verified `web/templates/base.html:228-232`); SKILL.md:30 cites `base.html:197-216` (verified `web/templates/base.html:197-216`); SKILL.md:43 cites `:125-130`, `:134-136`, `:144-156` (verified `web/templates/base.html:125-130`, `:134-136`, `:144-156`); SKILL.md:61 cites `web/build.py:79-144` (verified `web/build.py:79-144`).
2. Add `feed.xml` to owned-files list + RSS trigger: **Done** — SKILL.md:3 lists `feed.xml` in description and "update the RSS template" trigger; SKILL.md:8 names it explicitly and credits `_render_feeds` at `web/build.py:173` (verified `web/build.py:173`).
3. Document lightbox `data-*` contract + tier-tooltip `data-tip` contract: **Done** — SKILL.md:36-41 spells out `data-photo`/`-cap`/`-alt` and points at the delegated handler `base.html:157-162` (verified `web/templates/base.html:157-162`) and producer `_card.html:10` (verified `web/templates/_card.html:10`); SKILL.md:45-46 documents `#tier-tip` at `base.html:91` (verified `web/templates/base.html:91`), JS at `:165-195` (verified `web/templates/base.html:165-195`), producer `_card.html:7` (verified `web/templates/_card.html:7`).
4. Mention conditional Giscus block + `giscus` env-global + `noindex,noarchive` meta: **Done** — SKILL.md:63 cites `giscus` global at `web/build.py:90-95` (verified `web/build.py:90-95`) and the conditional block at `web/templates/inmate.html:293-323` (verified `web/templates/inmate.html:293-323`); SKILL.md:48-49 documents the `noindex, noarchive` meta at `base.html:10` (verified `web/templates/base.html:10`) and ties it to ORC § 2953.32.
5. Broaden triggers (masthead, footer, filter, table view, lightbox): **Done** — SKILL.md:3 description appends "edit the masthead/footer", "fix the lightbox", "add a filter", "tweak the table view", "update the RSS template".

## New issues found in pass 2
- Paired agent `/.claude/agents/jcstream-template-author.md:3` description still omits `feed.xml` from the file enumeration and lacks the new contracts (lightbox/tier-tooltip `data-*`, Giscus, `noindex,noarchive`). Cosmetic since the SKILL.md is the source of truth, but the two are now slightly out of sync.
- Minor: SKILL.md:13 says cache-bust is set by `web/build.py:98-101`; the assignment is at lines 100-101 with `import hashlib` and `_css = …` at 98-99. The range is inclusive and reasonable, but technically only 100-101 are the `css_version` line. Not worth flagging again.

## Pass-2 lens checks
- **Drift**: Clean. Every cite I sampled (`web/templates/base.html:10, 78, 91, 125-130, 134-136, 144-156, 157-162, 165-195, 197-216, 228-232`; `web/templates/_card.html:5, 7, 10`; `web/templates/index.html:192`; `web/build.py:79-144, 90-95, 100-101, 173`; `web/templates/inmate.html:293-323`) matches reality.
- **Coverage**: Clean for the SKILL.md side. Agent .md trails (see new issues).
- **Triggers**: Clean. The description now matches the most common phrasings in CLAUDE.md-style task wording.
- **Applicability**: Domain remains central — all eight template files still render every 30-min build (`web/build.py:169-176`); skill should stay.
