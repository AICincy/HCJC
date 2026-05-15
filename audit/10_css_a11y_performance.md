# css - CSS Accessibility and Performance Audit

## Audit metadata
- Skill: jcstream-css-accessibility-performance
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 8 (web/static/style.css 1019, web/templates/base.html 257, web/templates/index.html 310, web/templates/inmate.html 224, web/templates/stats.html 105, web/templates/data.html 112, web/templates/_card.html 21, web/build.py 1282 cross-check only)
- Time: 2026-05-14T01:44:38Z

## Observations

- The `:focus-visible` outline is set globally at line 61 (`outline: 2px solid var(--accent); outline-offset: 2px`). I grepped for `outline: none` and `outline: 0` and found zero matches. The only override is `.back-to-top:focus-visible { outline-offset: -2px }` at line 861, which is intentional and documented in the comment above it (the 4px overshoot clips at the viewport edge).
- `--fg-dim` (#7c828f) measures 4.62 on `--bg` (passes AA), 4.39 on `--bg-soft`, 4.20 on `--surface`, and 3.80 on `--surface-hi`. The header comment claims AA, but it only holds against the page background. Two real placements drop below: `.card-inmate .id-chip` (line 493, rendered on `--surface`, ratio 4.20) and `.recent-activity .event-line time` (line 647, rendered on `--surface-hi`, ratio 3.80).
- `.tag-booked` text `--danger` on its tinted background composited over `--surface-hi` (recent-activity card context, the only place this tag is rendered per `web/templates/index.html` line 65) lands at 3.76. The same tag composited over `--bg` would land at 4.57. The surface-hi parent eats the margin.
- `.card-inmate` already has `content-visibility: auto` and `contain-intrinsic-size: auto 100px` (lines 431-432), and the comment correctly notes the tooltip is body-level so paint containment will not clip it. The `@media print` block at line 991 disables `content-visibility` for off-screen cards so they print. Both are correctly set up.
- Print rule at line 993 (`details.month, details.coms { open: true; }`) uses an invalid CSS property. `open` is an HTML attribute, not a CSS property. The expand-on-print actually works via the very next rule (`details:not([open]) > * { display: revert !important }`), so the broken line is dead code.
- `.banner` is defined twice. Line 172 sets `display: flex` plus warm-amber framing; line 923 silently overrides it with `display: block` and rewrites `.banner strong` from `var(--warn)` (line 185) to `var(--fg)` (line 926). The later rule wins, so the masthead banner is block-level, not flex, and the `<strong>` color the first block intended never paints.
- `.kpi`, `.kpis`, `.num`, and `.label` are used in `web/templates/stats.html` lines 30-36 but are not styled in `web/static/style.css`. They render as default `<div>` inline-block flow. Either the stats page is meant to look minimal and they are intentional no-ops, or this is a missing block. Worth confirming with the owner.
- Hard-coded hex outside `:root`: `#14181f` at line 56 (`.skip-link` text, equals `--bg`), `#c98a8a` and `#9ab4d3` at lines 392-393 and 540-541 (duplicate values in `.sr-tier` and `.tier-*`), `#1b212b` at lines 942 and 948 (`.cfs-map` background, near `--surface`), `#d4915c` and `#ef6b6b` at lines 958-959 (`.map-key-*`, duplicate of `--accent` and the violence/sex `--cat`). Print block at lines 988, 996-1003 uses literal greys but is scoped to `@media print` so light/dark mode is not a concern.
- `!important` count: 5 total. Line 47 (`.sr-only` position, standard pattern). Lines 990, 995, 1002 (x2), 1003 all inside `@media print` to defeat layout rules from the non-print stylesheet. Zero non-sr-only, non-print uses. Clean.
- View transitions (line 44, `@view-transition { navigation: auto }`) honor the user's reduced-motion preference per the CSS spec automatically; no override needed.

## Analysis

JCStream's stylesheet is in good shape. The owner has clearly thought about contrast (the lift comment on `--fg-dim`) and about paint cost (`content-visibility: auto` with intrinsic-size hint, the inline-size container query on `.cards`). The skill instructions warn against flagging the dark-only theme, the system font stack, and the single-bundle pattern; none of those need pushback.

The real accessibility risk is the secondary surface ladder. `--bg`, `--bg-soft`, `--surface`, and `--surface-hi` ascend in lightness, and `--fg-dim` was tuned against `--bg`. Every step up the surface ladder costs the dim tier roughly 0.2 in contrast ratio. By `--surface-hi` (the recent-activity card background and the lightbox image fallback), `--fg-dim` text is at 3.80, well under AA for body text. Two concrete instances trip this: the id-chip on every card and the timestamp inside every recent-activity event line. These are small text (0.66 and 0.68 rem, around 10 px), so AA's 4.5 threshold applies; the 3.0 threshold for large text does not.

The `.tag-booked` finding is a similar geometry. `rgba(214,90,90,.16)` was chosen so the tag sits softly inside a card. When the card background is `--bg` it composites to a color that yields 4.57 against `--danger`. When the card background is `--surface-hi` (recent-activity row) it composites to a lighter, less saturated red that yields 3.76. The fix that respects the editorial mute is to bump the tag bg alpha to ~0.22-0.24 in the recent-activity scope, not to brighten `--danger`.

The duplicate `.banner` block is a real bug. The masthead disclaimer banner gets the second definition's `display: block`, so the warm flex layout in the first block (with `align-items: flex-start` and `gap: 0.85rem`) is unused. The first definition also paints `<strong>` inside the banner as `var(--warn)`, but the second definition overrides it to `var(--fg)`. Whoever added the lower block at line 923 in a different editing session likely did not notice the earlier one. Either consolidate or remove the dead first block.

CSS variable discipline is mostly tight. The category palette at lines 512-519 hard-codes hex values, but they are mapped 1:1 to a meaning per the in-code comment, and the `--cat` indirection is what the rest of the file consumes. Hard-coded duplicates outside `:root` mostly exist in `@media print` (white/black/grey is fine there) and in the Leaflet map fallback. The two that should be variables-or-not-duplicated are the `.sr-tier` and `.tier-*` colors at lines 392-393 and 540-541, which restate `#c98a8a` and `#9ab4d3` twice each. Promoting them to `--tier-felony-fg` / `--tier-misd-fg` (and matching bg/border alphas to color-mix) would cut the four duplicates to one declaration.

`!important` use is clean: every occurrence is either in `.sr-only` (the visually-hidden pattern) or inside `@media print` where it overrides the non-print stylesheet. No specificity hacks, no `id` selectors used for styling except `#tier-tip` and `#lb` which are documented singletons.

Responsive behavior is solid. `.cards` uses `auto-fill, minmax(15.5rem, 1fr)`, so on a 320 px viewport (minus 0.85rem padding) it reflows to a single column. The container query at line 410 then re-tightens the card internals once they are in a one-column layout. Mobile media at line 1007 covers masthead padding, the inmate-hero photo unfloating, and the bio grid collapsing to a single column. The only fixed-pixel layout dimensions are `--masthead-h` (54), `--monthnav-h` (34), the 48x60 thumb, and the 40px back-to-top button. None of these are user-text containers, so the lack of `rem` is fine.

The print stylesheet has two minor issues. The `details.month, details.coms { open: true }` line at 993 is invalid CSS (no `open` property exists) and gets ignored. The expansion still works via the `display: revert` rule on the next line. Also, `a[href^="http"]::after { content: " (" attr(href) ")" }` will dump full URLs after every external link, including the masthead nav links. For an inmate detail print this may be desired (it makes the printed page a self-contained record); for the homepage roster it just clutters. Acceptable trade-off but worth a note.

## Technical notes

```text
Contrast pass (text on first available surface):
  --fg #ecedef on --bg                14.2  AA ok, AAA ok
  --fg-soft #c3c7cf on --surface       9.55 AA ok, AAA ok
  --fg-muted #939aa6 on --bg           6.28 AA ok, AAA fail (small text needs 7)
  --fg-muted on --surface-hi           5.17 AA ok
  --fg-dim #7c828f on --bg             4.62 AA ok (just)
  --fg-dim on --surface                4.20 AA FAIL  <-- .card-inmate .id-chip
  --fg-dim on --surface-hi             3.80 AA FAIL  <-- .recent-activity time
  --accent #d4915c on --bg             6.78 AA ok
  --danger #df6b6b on --bg             5.47 AA ok
  --warn #c0883a on --bg               5.78 AA ok
  --misd #6c97c4 on --bg               5.81 AA ok
  --ok #6aa572 on --bg                 6.13 AA ok
  skip-link #14181f on --accent        6.78 AA ok
```

```text
Tinted-chip pass (text on composited tint over parent bg):
  .tier-felony c98a8a on rgba(168,72,72,.20)/--bg            5.37 AA ok
  .tier-misdemeanor 9ab4d3 on rgba(79,111,149,.20)/--bg      6.87 AA ok
  .tag-booked --danger on rgba(214,90,90,.16)/--bg           4.57 AA ok
  .tag-booked --danger on rgba(214,90,90,.16)/--surface-hi   3.76 AA FAIL <-- live
  .tag-released --ok  on rgba(...)/--bg                      4.79 AA ok
  .tag-updated --warn on rgba(...)/--bg                      4.61 AA ok
```

```text
Category --cat hue on .charge text:
  on --surface (#1c2128):
    violence/sex #ef6b6b     5.38
    weapons      #e0934a     6.51
    property     #d6a85c     7.41
    theft/fraud  #5fccaa     8.25
    drugs        #c79ae0     7.03
    family       #dd8aa0     6.33
    traffic      #9aa0ac     6.16
  on --surface-hi (#232932) (recent-activity cards):
    violence/sex             4.87  (closest to floor)
    all others               5.57+
```

```text
back-to-top opacity composite:
  fg-soft #c3c7cf @ opacity 0.55 effective on --surface  3.86  AA FAIL for text
  but it is an icon-button (font-size 1.1rem, single glyph) so the 3:1 UI
  component rule applies; on :hover opacity goes to 1.0 (ratio 9.55). Border
  is var(--border-hi) so the control bounds are visible. Edge case.
```

```css
/* Hardcoded hex outside :root (line numbers): */
56:  .skip-link    color: #14181f;       /* equals var(--bg) */
392: .sr-tier.sr-felony      color: #c98a8a;  /* dup of .tier-felony */
393: .sr-tier.sr-misdemeanor color: #9ab4d3;  /* dup of .tier-misdemeanor */
540: .tier-felony            color: #c98a8a;
541: .tier-misdemeanor       color: #9ab4d3;
942: .cfs-map                background: #1b212b;
948: .cfs-map .leaflet-container background: #1b212b;
958: .map-key-cfs            background: #d4915c;  /* equals --accent */
959: .map-key-shooting       background: #ef6b6b;  /* equals violence --cat */
```

```css
/* Duplicate .banner blocks: */
/* line 172: */
.banner { display: flex; align-items: flex-start; gap: 0.85rem; ... }
.banner strong { color: var(--warn); }
/* line 923 silently overrides: */
.banner { display: block; }            /* wins */
.banner strong { color: var(--fg); }   /* wins */
```

```css
/* Invalid CSS in print block, line 993: */
details.month, details.coms { open: true; }   /* no such property */
/* The next line is what actually expands them: */
details:not([open]) > * { display: revert !important; }
```

```text
File and selector stats:
  Total lines        1019
  !important uses    5 (1 sr-only, 4 print)
  Hardcoded hex outside :root, outside print, outside category palette: 7
  Web fonts loaded   0
  @import statements 0
  Universal selector 1 (* { box-sizing: border-box })
  Duplicate selectors .banner (2x), .banner strong (2x)
  Unused selectors   none confirmed; .kpi/.kpis/.num/.label in stats.html
                     reference no CSS rule (templates use, CSS does not style)
```

```css
/* Selectors classes used in templates and inline JS that the CSS handles
   (cross-check confirmed live, not dead): */
.is-filtered-out  -> base.html toggle (line 397 CSS)
.is-empty         -> base.html toggle (line 398 CSS)
.cfs-map-failed   -> templates fallback (line 947 CSS)
.thumb-placeholder -> templates avatar fallback
.released-name    -> index.html event tag, line 72
.tier-corner      -> templates inmate card
.legal-anchor     -> templates inmate.html record-legal section
```

## Findings

### css-F1. id-chip and recent-activity time fail AA on raised surfaces - severity med, confidence high
- Selector / variable: `.card-inmate .id-chip` (line 493) and `.recent-activity .event-line time` (line 647), both use `color: var(--fg-dim)` which is 4.20 on `--surface` and 3.80 on `--surface-hi`. Body text at 0.66-0.68 rem needs AA 4.5.
- Issue: The `--fg-dim` value was calibrated against the page background. Cards sit on a lighter surface, recent-activity cards sit on a yet lighter surface. The dim tier no longer clears AA there.
- Patch: keep `--fg-dim` for use on `--bg` only; introduce a second var for raised surfaces, or bump the existing one.
```css
:root {
  --fg-dim:        #7c828f;   /* AA on --bg only */
  --fg-dim-raised: #8c92a0;   /* AA on --surface and --surface-hi (~5.0) */
}
.card-inmate .id-chip { color: var(--fg-dim-raised); }
.recent-activity .event-line time { color: var(--fg-dim-raised); }
```

### css-F2. tag-booked fails AA in recent-activity context - severity med, confidence high
- Selector / variable: `.tag-booked` (line 658), rendered inside `.recent-activity .card-inmate` which forces `background: var(--surface-hi)` (line 638). Composite contrast: 3.76.
- Issue: The tint alpha was tuned against `--bg`; on the lighter parent it loses saturation.
- Patch: nudge tag bg alpha up so contrast stays in AA on either surface.
```css
.tag-booked   { background: rgba(214,90,90,.22);  color: var(--danger); border: 1px solid rgba(214,90,90,.40); }
.tag-released { background: rgba(106,165,114,.22); color: var(--ok); border: 1px solid rgba(106,165,114,.40); }
.tag-updated  { background: rgba(192,136,58,.22); color: var(--warn); border: 1px solid rgba(192,136,58,.40); }
```

### css-F3. .banner block is duplicated and self-overriding - severity med, confidence high
- Selector / variable: `.banner` and `.banner strong` declared at lines 172, 185 and again at lines 923-926.
- Issue: The later block silently overrides `display: flex` to `display: block` and `<strong>` color from `var(--warn)` to `var(--fg)`. The intent of the first block is dead.
- Patch: pick one. If the masthead banner is supposed to be flex with amber strong-text, delete lines 923-926. If it is supposed to be a block with neutral strong-text, delete lines 172-185 and keep the later block (and remove `align-items`/`gap`).

### css-F4. Invalid `open: true` rule in print block - severity low, confidence high
- Selector / variable: `details.month, details.coms { open: true; }` at line 993.
- Issue: `open` is not a CSS property. The rule is silently ignored. Expansion works only because the next line force-displays children.
- Patch: delete line 993.

### css-F5. Tier color values duplicated between .sr-tier and .tier-* - severity low, confidence high
- Selector / variable: `#c98a8a` and `#9ab4d3` declared at lines 392-393 and again at lines 540-541.
- Issue: Two copies of the same colors. Future tuning has to touch both.
- Patch: hoist to `:root`.
```css
:root {
  --tier-felony-fg:    #c98a8a;
  --tier-misd-fg:      #9ab4d3;
  --tier-felony-bg:    rgba(168,72,72,.20);
  --tier-misd-bg:      rgba(79,111,149,.20);
}
.sr-tier.sr-felony      { background: var(--tier-felony-bg); color: var(--tier-felony-fg); }
.sr-tier.sr-misdemeanor { background: var(--tier-misd-bg);   color: var(--tier-misd-fg); }
.tier-felony            { background: var(--tier-felony-bg); color: var(--tier-felony-fg);
                          border: 1px solid color-mix(in srgb, #a84848 40%, transparent); }
.tier-misdemeanor       { background: var(--tier-misd-bg);   color: var(--tier-misd-fg);
                          border: 1px solid color-mix(in srgb, #4f6f95 40%, transparent); }
```

### css-F6. Unstyled stats classes (.kpi/.kpis/.num/.label) - severity low, confidence high
- Selector / variable: `web/templates/stats.html` lines 30-36 use `.kpis`, `.kpi`, `.num`, `.label`. None are declared in CSS.
- Issue: Either the stats page is intentionally minimal and the classes are leftover scaffolding, or a styling block was forgotten. The page still renders, but the KPI cards have no visual treatment.
- Patch: confirm intent. If a treatment is wanted:
```css
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
        gap: 0.75rem; margin: 1rem 0 1.25rem; }
.kpi  { background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 0.75rem 0.9rem; }
.kpi .num   { font-family: var(--font-serif); font-size: 1.6rem; font-weight: 700;
              color: var(--fg); font-variant-numeric: tabular-nums; line-height: 1.05; }
.kpi .label { color: var(--fg-muted); font-size: 0.78rem; margin-top: 0.2rem; }
```

### css-F7. Stray `--family` and `--danger-deep` vars appear unused - severity low, confidence med
- Selector / variable: `--family` (line 24) and `--danger-deep` (line 21) declared, no `var(--family)` or `var(--danger-deep)` usage in the file.
- Issue: Dead variables. Their values are restated in the category palette (`--family` => `#c79a6a` is close to but not the same as the `.charge-family` `--cat: #dd8aa0`, and `--danger-deep #d65a5a` is restated in the tag-booked rgba as `(214,90,90,...)`).
- Patch: verify nothing inline-imports them, then delete. Grep to confirm:
```sh
grep -nE 'var\(--family\)|var\(--danger-deep\)' web/ docs/
```

### css-F8. back-to-top opacity drops the resting state below AA - severity low, confidence med
- Selector / variable: `.back-to-top` (lines 841-857), `opacity: 0.55`. Effective fg-soft on surface ratio: 3.86.
- Issue: At rest, the icon character contrast is below AA for text. It is a UI control (the 3:1 floor applies), so it is acceptable, and hover/focus restore full contrast. Worth flagging for users who never hover (touch). The border (`--border-hi`) provides bounds.
- Patch: lift opacity to 0.7 (ratio ~4.6) or remove opacity and use a slightly dimmer color directly.
```css
.back-to-top { opacity: 0.75; }
.back-to-top:hover, .back-to-top:focus-visible { opacity: 1; }
```

## Recommendations

| Finding | Recommendation |
| --- | --- |
| css-F1 | Add `--fg-dim-raised: #8c92a0` and apply to `.card-inmate .id-chip` and `.recent-activity .event-line time`. |
| css-F2 | Bump tag-booked / tag-released / tag-updated bg alpha from .16 to .22. |
| css-F3 | Consolidate the two `.banner` blocks; decide flex+amber-strong or block+neutral-strong and delete the loser. |
| css-F4 | Delete the invalid `open: true` rule on line 993. |
| css-F5 | Hoist tier color hexes to `--tier-felony-fg` / `--tier-misd-fg` and reuse. |
| css-F6 | Either add a `.kpi` style block or document the intentional bare render. |
| css-F7 | Remove unused `--family` and `--danger-deep` from `:root` after a grep confirms no callers. |
| css-F8 | Lift `.back-to-top` resting opacity from 0.55 to 0.7-0.75. |

## Remediation plan

1. Land css-F1, css-F2, css-F8 in one patch. They are pure contrast bumps, all on existing variables or tint alphas, zero risk to layout.
2. Land css-F3 and css-F4. Delete the duplicate `.banner` block and the invalid `open` rule. Visual diff only on whichever `.banner` variant the owner did not intend.
3. Land css-F5 and css-F7. Hoist tier hexes to vars, delete dead vars. Mechanical refactor.
4. Decide css-F6 with the owner. Either ship the `.kpi` block or document why the stats page renders bare.
5. Re-run a contrast pass on `--fg-dim` against every surface that uses it (search for `var(--fg-dim)` parents) to confirm no other spot regressed.

## Cross-references

- ARIA roles, keyboard flow, screen-reader semantics, the type-ahead combobox markup, the lightbox dialog focus trap, skip-link target validity: jcstream-html-accessibility.
- Whether inline JS in `base.html` escapes inmate-name text before injecting into `.sr-item .sr-name`: jcstream-html-template-security.
- Whether the `noindex`, `Open Graph`, and `presumption of innocence` strings consumed by the `.banner` and `.record-legal` styles are consistent across templates: jcstream-html-content-governance.

## Confidence and limitations

- All contrast ratios computed with the WCAG 2.x relative-luminance formula, sRGB gamma. Composite tints computed as straight alpha over the parent background. I did not account for nested transparency (e.g. a tag inside a card inside `--bg-soft`) past one level, because the templates only nest one level in the affected cases.
- "Unused" claims for `--family` and `--danger-deep` rest on a grep of `web/` only; I did not scan inline `style` attributes in generated `docs/` HTML for variable references. The Recommendation note flags the grep to run before deleting.
- "Unstyled" claim for `.kpi`/`.kpis`/`.num`/`.label` rests on a grep of `style.css` only. I did not check `docs/` build output for an inline `<style>` block, but the build pipeline pulls the stylesheet by URL with content-hash cache-bust, so an inline override would be unusual.
- The site is read-only here; I did not curl the live page or run Lighthouse. Reported behavior is from static analysis of CSS, templates, and the build script.
- Dark theme as a default, lack of web fonts, and single-bundle stylesheet are all deliberate and not flagged per skill instructions. The content-hash cache-bust is acknowledged at `web/build.py` line 96-100 and respected.

End of report.
