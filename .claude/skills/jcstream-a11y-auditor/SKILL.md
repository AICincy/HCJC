---
name: jcstream-a11y-auditor
description: Use when auditing JCStream for accessibility — WCAG AA color contrast on the light theme, ARIA correctness (aria-current/aria-pressed/aria-modal/role=…), keyboard navigation, focus ring, tab order, alt text, screen-reader-only content, reduced-motion. The new light theme retired the dark theme's hand-tuned contrast tokens, so contrast must be verified empirically rather than assumed from tokens. Trigger phrases: "accessibility audit", "a11y", "a11y review", "WCAG check", "ARIA", "ARIA check", "screen reader", "contrast issue", "color contrast", "focus ring", "keyboard nav", "alt text".
---

# JCStream a11y auditor

You audit `web/templates/*.html` + `web/static/style.css` for WCAG 2.1 AA compliance. The dark→light theme swap retired the dark-theme `--fg-dim-raised` *tuning* (the variable still exists at `web/static/style.css`, now an alias to `--fg-dim` — don't grep-and-miss it), so **don't infer contrast safety from token names; measure each color pair on real surfaces.**

## Surfaces to verify
For each surface (background) × ink (foreground) pair:

| Background | Inks used on it |
|---|---|
| `--bg` (#fafaf8) | `--fg`, `--fg-soft`, `--fg-muted`, `--fg-dim` |
| `--surface` (#fff) | `--fg`, `--fg-soft`, `--fg-muted`, `--fg-dim`, `--accent` |
| `--bg-soft` (#f4f3ef) | `--fg`, `--fg-muted` |
| `--accent-bg` (#eef0fc) | `--accent`, `--fg` |
| `--warn-bg` (#fbeded) | `--warn` (#b54545), `#6b3434` (hard-coded ink reused on `.alert p`, the Cincy alert banners, and the comment-policy block — `style.css`) |
| Tier chip backgrounds (10) | Tier ink colors paired in `style.css` (`tier-F1`…`tier-MM`) |
| Ladder cell backgrounds (10) | Ladder ink colors paired in `style.css` (`ladder-F1`…`ladder-MM`) |

For each pair: target **4.5:1 (body text)** or **3.0:1 (large text ≥18px regular or 14px bold)**.

## Tools
- **`pa11y` or `axe-core` CLI** for automated checks. Headless against `docs/index.html`, `docs/inmate/<id>/index.html`, `docs/stats/index.html`, `docs/statute/index.html`.
- **WebAIM contrast checker** (manual) for spot-checks of specific pairs.
- **Browser devtools** for keyboard-only traversal: Tab through every page, ensure focus ring is visible. Only two rules currently set a real focus ring (`web/static/style.css` `outline-offset: -2px` on `.back-to-top`, and `web/static/style.css` `outline: 2px solid var(--accent)` on the about-jcstream summary). Filter inputs explicitly strip the focus outline at `web/static/style.css` (`outline: 0` with only a `box-shadow` ring) — flag this as a focus-visibility regression to fix.

## ARIA inventory (already correct — keep it that way)
| Element | Attribute | Where |
|---|---|---|
| Skip link | `<a class="skip-link" href="#main">` (WCAG 2.4.1) | `base.html` + styled `style.css` |
| Active severity-ladder cell | `aria-current="true"` | `inmate.html`, `statute.html` |
| Card/Table view toggle | `aria-pressed` | `index.html` (button) + `base.html` JS sets it |
| Lightbox dialog | `role="dialog" aria-modal="true" aria-label="Booking photo"` | `base.html` |
| Search results combobox | `aria-autocomplete="list" aria-expanded aria-controls` | `index.html`, `base.html` JS |
| Search-results panel | `role="region" aria-label="Search results"` | `index.html` |
| Empty-filter state | `role="status"` | `index.html` |
| Tier tooltip | `role="tooltip"` | `base.html` |
| Tier badge → tooltip wiring | `aria-describedby="tier-tip"` on `.tier-corner` | `_card.html` |
| Filter status | `aria-live="polite"` on `.filter-count` | `index.html` |
| Statbar group / item | `role="list"` + `role="listitem"` | `stats.html` |
| Charges / files table semantics | `<caption class="sr-only">…</caption>` | `inmate.html`, `data.html` |
| Section-h pills | `aria-hidden="true"` where decorative | various |

When adding interactive state, mirror the pattern.

## Screen-reader-only h1
`base.html` has `{% block sr_h1 %}<h1 class="sr-only">JCStream — …</h1>{% endblock %}` rendered ONLY on the homepage (overridden to empty on detail pages). Don't remove — it gives screen readers a page-level landmark before the visible heading.

## Reduced motion
`html { scroll-behavior: smooth; }` is wrapped in `@media (prefers-reduced-motion: no-preference)` (`style.css`), and a project-wide `@media (prefers-reduced-motion: reduce)` reset at `style.css` zeroes `transition` and `animation` on every element (`*, *::before, *::after`) plus the `::view-transition-old/new/group(*)` pseudo-elements — so all `jc-pulse` keyframes and `transition:` rules are already globally suppressed for reduced-motion users. **Do not flag individual `transition:` lines as gaps**; the cascade already handles them. Flag only new motion that bypasses normal CSS (e.g. JS-driven animations, `requestAnimationFrame` loops, or motion declared inline in templates) — those need an explicit `matchMedia('(prefers-reduced-motion: reduce)')` check.

## Keyboard traps to watch
- Lightbox tab cycle (`base.html`) — must wrap when `inert` not supported.
- Filter dropdown + search results combobox — ESC closes both.
- Tier tooltip — pointer-events:none so it can't steal focus.

## Anti-patterns
- `<div onclick="…">` instead of `<button>` or `<a>` — kills keyboard access.
- `aria-label` on a `<div>` that has visible text — labels override the text.
- Color-only state ("the active tab is bluer") — pair with weight, underline, or icon.
- `tabindex="0"` on a non-interactive element.

## Verify
```sh
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
npx pa11y docs/index.html docs/inmate/<id>/index.html docs/stats/index.html docs/statute/index.html
# Or with axe:
npx @axe-core/cli docs/index.html
```
Document failures with file:line, recommended fix, and WCAG criterion (e.g. "1.4.3 Contrast (Minimum) — `--fg-dim` on `--surface` measures 2.9:1, fails AA at 14px").
