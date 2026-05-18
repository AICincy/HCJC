# Audit — jcstream-template-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-template-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-template-author.md
- **Verdict**: Yellow
- **One-line summary**: Conventions and contracts are accurate, but every cited line number has drifted and the env-globals catalog stops short of the real registration block.

## A. Drift
- SKILL.md:13 — claims `build.py:100-101` for `css_version`; actual line is `web/build.py:100` only (single statement spanning 100-101 logically, but the cite is fine). The `import hashlib as _hl` sits at `web/build.py:98` so the "lines 100-101" framing is ok-ish but undercites context.
- SKILL.md:20 — says the `data-*` attrs are set in `_card.html:5`; verified at `web/templates/_card.html:5`. OK.
- SKILL.md:25 — claims `currentFilters()` lives at `base.html:239-241`; actual definition is `web/templates/base.html:228-232`. Drift of ~10 lines.
- SKILL.md:30 — "Button: `index.html` (`<button id="view-toggle">`)"; the real markup at `web/templates/index.html:192` is `<button type="button" class="view-toggle" id="view-toggle" aria-pressed="false" hidden>`. Line number missing, attribute set understated (the `hidden` + `aria-pressed` are load-bearing — JS un-hides at `base.html:200` and toggles aria-pressed at `:206`).
- SKILL.md:31 — "JS handler: `base.html:160-178`"; actual handler block is `web/templates/base.html:197-216`. Drift of ~37 lines.
- SKILL.md:32 — "CSS: `style.css:481-516`"; verified at `web/static/style.css:481-516`. OK.
- SKILL.md:36 — "`base.html:125-135` sets `inert`"; actual `inert` open at `web/templates/base.html:125-130`, close at `:134-136`, Tab-cycler fallback at `:144-156`. The single range conflates open + close + fallback.
- SKILL.md:45 — "helpers registered in `build.py:79-126`"; registrations actually run `web/build.py:79-144` (e.g. `bond_total`, `days_in_custody`, `charges_by_chapter`, `crimes_of_month`, `orc_freq`, `codes_ohio_url`, `related_inmates`, `all_inmates_total`, `inmates_by_id`, `all_chapters` are all past line 126). Range is short by 18 lines.

## B. Coverage gaps
- `web/templates/feed.xml` exists (`web/templates/feed.xml:1-19`) and is rendered via `_render_feeds` — SKILL.md frontmatter and the body never list it, so a "fix the RSS template" prompt won't auto-route.
- The shared lightbox markup contract — `<div class="lightbox" id="lb" role="dialog" aria-modal="true">` at `web/templates/base.html:78`, plus the `data-photo` / `data-photo-cap` / `data-photo-alt` trigger contract used by `_card.html:10` and the click delegate at `base.html:157-162` — is invoked by every thumbnail but isn't documented.
- The shared tier-tooltip pattern (`#tier-tip` at `base.html:91`, `data-tip` consumed at `base.html:165-195`, written by `_card.html:7`) is a cross-template contract that only the tooltip-tweaker would otherwise discover by archaeology.
- Conditional Giscus comments block at `web/templates/inmate.html:293-318` (gated on `giscus.repo_id`) is owned by this skill but unmentioned; the `giscus` env-global at `web/build.py:90-95` is also missing from the catalog.
- The `noindex, noarchive` robots meta at `web/templates/base.html:10` is load-bearing for the ORC § 2953.32 expungement contract — worth a one-liner so it isn't accidentally removed.
- The search type-ahead dropdown at `web/templates/base.html:267-360` lazy-loads `/search.json`; if a template task touches `#search-box` markup the skill gives no warning that JS depends on the id.

## C. Trigger-phrase quality
- Current description (paraphrased): "editing or creating Jinja templates under web/templates/ — base.html, index.html, inmate.html, stats.html, statute.html, data.html, _card.html. Covers css_version, data-* filter hooks, body.is-table, lightbox inert, base.html block overrides. Trigger phrases: 'edit the inmate page', 'add a section to the homepage', 'fix template rendering'."
- Issues: `feed.xml` is missing from the file enumeration; trigger set omits the most natural phrasings — "update the footer", "tweak the masthead", "fix the lightbox", "add a filter", "table view", "RSS feed".
- Proposed rewording: add `feed.xml` to the file list and append triggers like "edit the masthead/footer", "fix the lightbox", "add a filter", "tweak the table view", "update the RSS template".

## D. Applicability
- Domain is alive and central — all eight files under `web/templates/` are rendered every 30-min build (`web/build.py:169-176`); skill should stay.

## Recommended fixes (priority order)
1. Refresh every line cite: `currentFilters` -> 228-232, view-toggle handler -> 197-216, lightbox open/close/fallback -> 125-156, env globals -> 79-144.
2. Add `feed.xml` to the owned-files list in both frontmatter and body, and add "RSS feed" trigger.
3. Document the lightbox trigger contract (`data-photo`/`-cap`/`-alt`) and the tier-tooltip `data-tip` contract — both are cross-template patterns with implicit JS dependencies.
4. Mention the conditional Giscus block and the `giscus` env-global; mention the `noindex, noarchive` meta tied to ORC § 2953.32.
5. Broaden trigger phrases (masthead, footer, filter, table view, lightbox).
