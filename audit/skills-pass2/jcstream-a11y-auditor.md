# Audit Pass 2 — jcstream-a11y-auditor

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All six pass-1 fixes landed; every cited `file:line` re-verifies and the trigger list now covers the obvious phrasings.

## Pass-1 recommendation status
1. Re-cite line numbers (tier 676-685, ladder 1235-1244, tooltip 91, sr-only h1 66, tab cycler 144-156): **Done** — `SKILL.md:20` cites `style.css:676-685` (matches `web/static/style.css:676-685`), `SKILL.md:21` cites `style.css:1235-1244` (matches `web/static/style.css:1235-1244`), `SKILL.md:36` cites `base.html:78` (lightbox at `web/templates/base.html:78`), `SKILL.md:40` cites `base.html:91` (tooltip at `web/templates/base.html:91`), `SKILL.md:50` cites `base.html:66` (sr-only h1 at `web/templates/base.html:66`), `SKILL.md:56` cites `base.html:144-156` (tab cycler at `web/templates/base.html:144-156`).
2. Soften reduced-motion claim and list unguarded transitions / `jc-pulse`: **Done** — `SKILL.md:53` states only `scroll-behavior` is guarded and enumerates `jc-pulse` keyframes at `style.css:151,153` (verified at `web/static/style.css:151,153`) plus the unguarded `transition:` rule lines.
3. Add skip-link, `<caption class="sr-only">`, `role="region"/"status"/"list"`, and `aria-describedby` to the ARIA inventory: **Done** — `SKILL.md:33` (skip link → `base.html:33`+`style.css:66-72`), `SKILL.md:38-39` (region/status), `SKILL.md:41` (`aria-describedby="tier-tip"` on `.tier-corner` → `_card.html:7`), `SKILL.md:43` (statbar role list/listitem → `stats.html:17,20`), `SKILL.md:44` (`<caption class="sr-only">` → `inmate.html:93`, `data.html:20`) — all verified.
4. Flag `outline: 0` at `style.css:464` as a focus-visibility regression: **Done** — `SKILL.md:28` calls out `web/static/style.css:464` (`outline: 0`) explicitly as a regression to fix; verified at `web/static/style.css:464`.
5. Note `--fg-dim-raised` still exists as an alias: **Done** — `SKILL.md:8` clarifies the variable is still declared at `web/static/style.css:20` as an alias to `--fg-dim`; verified at `web/static/style.css:20` (`#94a3b8`, same value).
6. Broaden trigger phrases ("a11y", "ARIA", "focus ring", "keyboard nav", "alt text", "color contrast"): **Done** — `SKILL.md:3` description now lists "accessibility audit", "a11y", "a11y review", "WCAG check", "ARIA", "ARIA check", "screen reader", "contrast issue", "color contrast", "focus ring", "keyboard nav", "alt text".

## New issues found in pass 2
- Minor: `SKILL.md:19` cites the `#6b3434` hard-coded ink at `style.css:242,955,1334,1649`. Lines 242 (`web/static/style.css:242`), 955 (`.alert` block), and 1649 (`.comment-policy` block) verify, but `:1334` is the `background: var(--warn-bg);` line inside the Cincy banner block and not itself a `#6b3434` foreground (the foreground for that block is at `:1331` via `color: var(--warn);`). Off-by-three but easy fix; doesn't change the audit value.
- Paired agent `.claude/agents/jcstream-a11y-auditor.md` was not refreshed alongside SKILL.md: `agents/...:12` still lists only the older ARIA tokens (`aria-current/aria-pressed/aria-modal/aria-live/role="dialog"/"tooltip"`), omitting the newly-inventoried `role="region"`, `role="status"`, `role="list"/"listitem"`, `<caption class="sr-only">`, and `aria-describedby`. Skill discovery still works (the SKILL.md is the source of truth), but the handoff doc is slightly behind.

## Pass-2 lens checks
- **Drift**: Clean except for the `#6b3434` line-number nit above; all other re-cites verified.
- **Coverage**: Clean — skip link, caption sr-only, region/status/list, aria-describedby, the `outline:0` regression, and the unguarded `jc-pulse`/transitions are all now documented.
- **Triggers**: Clean — description at `SKILL.md:3` covers the common phrasings flagged in pass 1.
- **Applicability**: Domain still fully alive; every cited file/line resolves and the skill remains worth keeping.
