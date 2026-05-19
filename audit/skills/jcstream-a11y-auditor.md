# Audit — jcstream-a11y-auditor

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-a11y-auditor/SKILL.md
- **Paired agent**: .claude/agents/jcstream-a11y-auditor.md
- **Verdict**: Yellow
- **One-line summary**: Concept and ARIA inventory are accurate, but several `file:line` cites have drifted and a few notable patterns (skip-link, outline:0 on filter inputs, unguarded transitions/animation) are missing.

## A. Drift
- **Tier-chip line range wrong.** SKILL says "`style.css:677-686`"; tier-F1..MM rules actually span `web/static/style.css:676-685` (off-by-one and missing `tier-M3` at line 683). Note `tier-M3` is at 683 between `tier-M2` (682) and `tier-M4` (684).
- **Ladder line range is a placeholder, not a range.** SKILL says "`style.css:1008-area`"; ladder colors are `web/static/style.css:1235-1244`.
- **base.html line refs are off.**
  - SKILL: "Lightbox dialog … `base.html:78`" — correct (`web/templates/base.html:78`).
  - SKILL: "Tier tooltip … `base.html:80`" — actually `web/templates/base.html:91`.
  - SKILL: "sr-only h1 … `base.html:55`" — actually `web/templates/base.html:66`.
  - SKILL: "Lightbox tab cycle (`base.html:135-149`)" — actually `web/templates/base.html:144-156`.
- **Reduced-motion claim is overstated.** SKILL: "Sparkline / spark-card transitions don't run when the user opts out." Only `scroll-behavior` is guarded at `web/static/style.css:59`; the `jc-pulse` keyframes (`style.css:151,153`) and many `transition:` rules (`style.css:70,168,397,475,573,767,1150,1224,1486,1511`) have no `prefers-reduced-motion` guard.
- **Token table omits `--fg-dim-raised`.** SKILL says it was "retired (now equal to `--fg-dim`)"; it's still declared at `web/static/style.css:20` (value `#94a3b8`, identical to `--fg-dim`). The variable persists; only its tuning was retired.
- **Focus-ring claim partly stale.** SKILL: "current outline at 2px, accent color." Only two rules match (`web/static/style.css:1431,1634`); filter inputs explicitly strip focus with `outline: 0` at `web/static/style.css:464` — a legit a11y concern not flagged.

## B. Coverage gaps
- **Skip link** at `web/templates/base.html:33` + `web/static/style.css:66-72` — central WCAG 2.4.1 affordance, never mentioned.
- **`<caption class="sr-only">` table semantics** at `web/templates/inmate.html:93` and `web/templates/data.html:20` — sr-only is mentioned only for the homepage h1.
- **`aria-describedby` + tooltip wiring** at `web/templates/_card.html:7` (`aria-describedby="tier-tip"`) — not in the ARIA inventory.
- **`role="region" aria-label="Search results"`** at `web/templates/index.html:190` and **`role="status"` empty-state** at `web/templates/index.html:198` — not enumerated.
- **`role="list"/"listitem"` on statbars** at `web/templates/stats.html:17,20,75-78,166-172` — undocumented pattern.
- **Color-only focus removal on filter controls** (`web/static/style.css:464`) — exactly the anti-pattern the skill should flag.
- **`#6b3434` hard-coded ink on `--warn-bg`** also reused at `style.css:242,1334-1649` (alert + Cincy banners), not just `.alert p` as the table implies.

## C. Trigger-phrase quality
- Current description (paraphrased): "WCAG AA contrast on light theme; ARIA correctness (aria-current/aria-pressed/aria-modal); keyboard nav; sr-only; reduced-motion. Triggers: 'accessibility audit', 'WCAG check', 'screen reader', 'contrast issue'."
- Issues: Misses common phrasings: "a11y", "ARIA", "keyboard navigation", "focus ring", "tab order", "color contrast", "alt text", "role=…".
- Proposed rewording: add to triggers "a11y review", "ARIA check", "focus ring", "keyboard nav", "alt text", "color contrast" and the strings `"a11y"` / `"ARIA"`.

## D. Applicability
Domain is fully alive — every cited file is owned, ARIA patterns are present, and the audits/ tree already contains sibling reports; keep the skill.

## Recommended fixes (priority order)
1. Re-cite line numbers: tier 676-685, ladder 1235-1244, tooltip 91, sr-only h1 66, tab cycler 144-156.
2. Soften the reduced-motion claim — only `scroll-behavior` is guarded; list the unguarded transitions/`jc-pulse` as gaps to fix.
3. Add skip-link, `<caption class="sr-only">`, `role="region"/"status"/"list"`, and `aria-describedby` to the ARIA inventory.
4. Flag `outline: 0` at `style.css:464` as an existing focus-visibility regression.
5. Note that `--fg-dim-raised` still exists (alias to `--fg-dim`) so audits don't grep-and-miss it.
6. Broaden trigger phrases to include "a11y", "ARIA", "focus ring", "keyboard nav", "alt text", "color contrast".
