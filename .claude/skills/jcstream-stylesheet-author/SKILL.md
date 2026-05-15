---
name: jcstream-stylesheet-author
description: Use when editing web/static/style.css in the JCStream project. Covers the light-theme token system (--bg/--fg/--accent), the 10-tier .tier-F1…MM ladder palette, .ladder-* cells, body.is-table table-mode rules, content-visibility, mobile breakpoint at 720px, and the print at-rule. Trigger phrases: "restyle the cards", "fix the tier colors", "make the hero bigger", "add a CSS rule", "edit the stylesheet", "tweak the lightbox", "fix the table view", "recolor the F3 chip", "tune the print layout".
---

# JCStream stylesheet author

You own `web/static/style.css`. The current theme is the "modern utility" light direction (warm-cream surfaces, slate-blue accent, Geist/Inter + JetBrains Mono). The dark editorial theme was retired in 2026; class names persisted but values shifted.

## Token system (single source of truth)
The `:root` block at `style.css` defines every color, typography stack, and radius. **Always extend tokens here before adding a new hex.** Tokens you cannot rename without auditing the rest of the file:

| Surface | `--bg` `--bg-soft` `--surface` `--surface-hi` `--border` `--border-hi` |
| Ink     | `--fg` `--fg-soft` `--fg-muted` `--fg-dim` `--fg-dim-raised` |
| Accent  | `--accent` `--accent-hi` `--accent-bg` `--accent-bg-2` |
| Status  | `--danger` `--warn` `--warn-bg` `--ok` `--misd` |
| Tier    | `--tier-felony-fg/bg/bd`, `--tier-misd-fg/bg/bd` (the `-bd` border twins of the bg pair, `style.css`) |
| City    | `--cincy-navy` `--cincy-red` (used by CFS captions) |
| Type    | `--font-sans` `--font-serif` `--font-mono` |
| Radius  | `--radius` `--radius-sm` |
| Layout  | `--masthead-h` `--monthnav-h` |

`--font-serif` is an alias for `--font-sans` in the current theme — don't rely on a serif being available unless you add one. Several status tokens currently share hex values (`--ok` and `--misd` are both `#4f7c3a` at `style.css`; `--danger` and `--warn` are both `#b54545` at `:26-27`) — they're not independently tunable until you split them.

`@view-transition { navigation: auto; }` (`style.css`) and the `prefers-reduced-motion` smooth-scroll guard (`:59`) drive cross-page animation — don't break either.

## Ten-tier ladder palette
Tier chips at `style.css` and ladder cells (`.ladder-grid`, `.ladder-cell`, `.ladder-F1`…`.ladder-MM`) at `style.css`, inside the "Severity ladder" section that opens at `style.css`. The colors are intentional — warmer reds for F1-F3 (most severe), warm oranges/creams for F4-F5, olive/sage for M1-M3, neutral for MM. Don't recolor without auditing where each tier is also used: search results, card corner chip, ladder cells, recent-booking cards, calendar items.

## `body.is-table` table mode
Rules at `style.css` reshape `.month .card-inmate` into a 5-column grid (52-1fr-140-70-100 px). When adding card content, ensure it survives both layouts. The toggle handle is `.view-toggle[aria-pressed="true"]` at `style.css` — that's what flips `body.is-table`.

## content-visibility
Cards use `content-visibility: auto` with `contain-intrinsic-size` set (`style.css`, `:768`). Off-screen cards skip paint cost. Don't put tier tooltips *inside* `.card-inmate` — they'd be clipped by the paint container. The shared `#tier-tip` floats outside.

## Mobile breakpoint
Primary breakpoint is `@media (max-width: 720px)` (twelve occurrences across the file at `style.css, 513, 880, 1081, 1177, 1292, 1359, 1525, 1580, 1684`, plus inline ones at `:1498, :1616`; the print-mode mobile block at `:1684` is the canonical bottom anchor). Stack the hero strip, drop the brand-sub, collapse the bio grid to 1 col, etc. Prefer extending the existing 720 px block over adding a new breakpoint.

Exception: the recent-bookings photo grid `.rb-grid` ships with its own non-720 breakpoints at `style.css` (`@media (max-width: 1080px)` → 3 cols, `@media (max-width: 540px)` → 2 cols) because the 6-col photo strip needs intermediate stops. These are the only non-720 widths in the file — don't take that as license to add more.

## Print
The `@media print` block at the bottom of the file forces a paper-style render. Add print suppression for any new feature that's interactive-only — existing examples are the lightbox (`style.css`), the dispatch/CFS map, and the comments/Giscus block (suppressed at `:1665`). Any new interactive component should be added to that suppression list.

## Components you also own
- **Lightbox** (mugshot zoom, used on inmate pages): `style.css`, print-suppressed at `:1664`.
- **Recent-bookings photo stack** (`.rb-grid`, `.rb-card`): `style.css`, with its own `content-visibility` at `:768` and the non-720 breakpoints noted above.
- **Dispatch / CFS map**: `style.css`.
- **Comments / Giscus block**: `style.css`.
- **Stacked severity bar** (`.stacked-leg`): `style.css`.
- **Top-list**: `style.css`.
- **Court calendar**: `style.css`.
- **Bond box-and-whisker**: `style.css`.
- **Time-in-custody timeline**: `style.css`.
- **Stats KPIs**: `style.css`.

## Anti-patterns
- New hex literals outside `:root`. Add a token first.
- Recoloring `.tier-F2` (or any ladder cell) without checking ladder + recent-bookings + statute page.
- Adding a `box-shadow` in light theme without considering print (`@media print` zeroes most shadows).
- Using `font-serif` expecting a different family — it's an alias.

## Verify
```sh
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
```
Then open `docs/index.html`, `docs/inmate/<id>/index.html`, `docs/stats/index.html`, `docs/statute/index.html` in a browser. Toggle the card / table view on the homepage. Check the 720 px breakpoint.
