# JCStream Design Deviation Report

**Spec:** `JCSTREAM_DESIGN_SPEC.md` (Brutalist Editorial, Monospace-Only, Three-Color)
**Implementation:** `AICincy/HCJC.git` @ `web/static/style.css` + `web/templates/`
**Date:** 2026-05-18
**Auditor:** Claude Opus, automated review

---

## Severity Classification

| Code | Meaning | Remediation Priority |
|------|---------|---------------------|
| **S1** | Structural: the implementation contradicts a named spec requirement | Must fix |
| **S2** | Component missing: spec-defined component has no CSS or renders unstyled | Must fix |
| **S3** | Value drift: the right element exists but token values diverge from spec | Should fix |
| **S4** | Behavioral: interaction or responsive behavior differs from spec | Should fix |
| **S5** | Cosmetic: minor visual divergence, low functional impact | Nice to fix |

---

## 1. Typography

### 1.1 Body Font Family is Sans-Serif, Not Monospace — S1

**Spec (Section 3):** "Single font family across the entire site: a monospace typeface." Body uses `font-family: 'JetBrains Mono', 'IBM Plex Mono', ...monospace`.

**Implementation (line 138):**
```css
body { font-family: var(--font-sans); }
```
`--font-sans` resolves to `"Public Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.

The implementation uses a proportional sans-serif (Public Sans / USWDS stack) for all body text. Monospace (`--font-mono`) is reserved for inline code, tier chips, timestamps, and ORC references. The spec mandates monospace everywhere with zero sans-serif body text.

**Files affected:** `style.css` line 138, `base.html` (all rendered output).

**Impact:** Foundational. The entire brutalist-editorial identity collapses when the body is proportional sans-serif. Every downstream deviation in letter-spacing, line-height, and visual density traces back to this.

---

### 1.2 Sans-Serif Fonts Shipped and Loaded — S1

**Spec (Section 3):** No sans-serif body text. No decorative fonts. Import JetBrains Mono or IBM Plex Mono.

**Implementation (lines 8-11):** Loads four weights of Public Sans (`400, 500, 600, 700`) via `@font-face`. Also ships `plex-sans-*.woff2` and `plex-mono-*.woff2` font files. The spec allows only monospace faces.

**Files affected:** `style.css` lines 8-14, `web/static/fonts/` directory.

---

### 1.3 Body Line-Height — S3

**Spec (Section 10, Note 6):** `line-height: 1.7` for body text.

**Implementation (line 140):** `line-height: 1.55`.

---

### 1.4 Body Letter-Spacing — S3

**Spec (Section 3, Body paragraph row):** `letter-spacing: 0.01em`.

**Implementation (line 141):** `letter-spacing: -0.005em` (negative tracking).

The spec calls for slightly expanded tracking. The implementation uses negative tracking, which is common for proportional sans but contradicts the monospace editorial intent.

---

### 1.5 Record Name Font and Size — S3

**Spec (Section 5.3):** Inmate name: 36px, 700 weight, uppercase, letter-spacing 0.08em, monospace.

**Implementation (lines 1626-1634):**
```css
.inmate-hero .record-name {
  font-family: var(--font-sans);     /* sans, not mono */
  font-size: clamp(20px, 3vw, 24px); /* max 24px, not 36px */
  letter-spacing: -0.025em;          /* negative, not 0.08em */
}
```

Three simultaneous deviations: wrong font family, roughly 33% smaller, and negative letter-spacing instead of positive.

---

### 1.6 Section Headings (h2) — S3

**Spec (Section 3):** h2: 20px, 700 weight, uppercase, letter-spacing 0.1em.

**Implementation (lines 472-478):**
```css
.section-h h2 {
  font-size: 18px;
  font-weight: 600;           /* 600, not 700 */
  letter-spacing: -0.02em;    /* negative, not 0.1em */
}
```

No `text-transform: uppercase` applied. Weight, size, and spacing all diverge.

---

### 1.7 Page Title Size — S3

**Spec (Section 5.1):** Page title "INMATE RECORD": 28px, 700 weight, uppercase, letter-spacing 0.12em.

**Implementation:** The `.doc-h .title` class exists in the HTML template (`inmate.html` line 43) but has **zero CSS definitions**. It renders as unstyled text inheriting body defaults (14px, Public Sans, no uppercase).

---

### 1.8 Uppercase Text Transforms Largely Missing — S1

**Spec (Section 3):** Aggressive use of `text-transform: uppercase` on site name, subtitle, nav links, breadcrumb, page title, section headings, table headers, labels, captions. CSS transforms required, not hardcoded caps in markup.

**Implementation:** `text-transform: uppercase` appears on tier chips, some stat labels, and a few scattered elements. It is absent from breadcrumb text, section headings, record name, page titles, and bio labels. The overall uppercase editorial texture is not present.

---

## 2. Color Palette

### 2.1 Accent Red Value — S3

**Spec (Section 2):** `--accent-red: #b33a3a`.

**Implementation (line 30):** `--accent: #b30000` ("federal red").

Both are dark reds, but `#b30000` is a pure red with no blue, while `#b33a3a` is warmer with blue and green components. Visible difference in side-by-side rendering.

---

### 2.2 Felony Tier Badge Colors — S3

**Spec (Section 5.2):** Filled red background `--accent-red` (#b33a3a), white text.

**Implementation (line 43):** `--tier-felony-bg: #c43e2c` (brighter, more orange-shifted red). The spec's single felony color has been expanded into a 10-tier graduated palette (F1 through MM) on lines 801-811, which is not in the spec.

---

### 2.3 Header Background — S1

**Spec (Section 2, 4.1):** `--bg-header: #1a1a1a` (dark bar).

**Implementation (line 155):** `.masthead { background: var(--bg); }` which resolves to `#fafafa`. The header is light/white, not dark.

This inverts the spec's foundational visual hierarchy. The spec defines a dark masthead with white text. The implementation uses a light masthead with dark text.

---

### 2.4 Disclaimer Background Missing — S3

**Spec (Section 2):** `--bg-disclaimer: #fdf5e6` (old lace/cream).

**Implementation:** No `--bg-disclaimer` token exists. The disclaimer/alert box uses `background: transparent` with no cream/old-lace coloring (lines 1636-1641).

---

### 2.5 Dark Mode Not in Spec — S5

**Implementation (lines 79-107):** Full `prefers-color-scheme: dark` media query with inverted palette. The spec makes no mention of dark mode. Not a conflict, but unspecified scope.

---

### 2.6 Additional Colors Beyond Three-Color Palette — S3

**Spec (Section 1):** "Three-color palette: black, white, red. Nothing else."

**Implementation:** Introduces greens (`--ok: #4f7c3a`), navy (`--cincy-navy: #00205B`), multiple warm accent tones (`--accent-bg: #fff0e5`), warn tones (`--warn-bg: #fbeded`), and a full chapter-based category color palette (lines 767-774) with 8+ distinct hues.

---

## 3. Layout Structure

### 3.1 Masthead Layout — S1

**Spec (Section 4.1):** Left: site name + subtitle stacked. Center-left: population count. Right: nav links, horizontal, evenly spaced. Full-width dark bar.

**Implementation (lines 161-169):**
```css
.masthead-inner {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
}
```
Center: site name (brand centered). Left area: government seal images. Right: single hamburger toggle. The nav links are inside a `<details>` disclosure panel, not displayed inline. Population count is a bordered chip element, not inline text with a pipe separator.

The header also includes two seal images (`hcjc-seal.png`, `coc-seal.png`) linked to Facebook pages. The spec says "No icons" and specifies no seal images.

---

### 3.2 Content Container Styling — S3

**Spec (Section 4.2):** White card on warm gray body (`#f7f6f3`). `max-width: 1200px`. 1px `--border-light` outline. Padding: `32px 40px`.

**Implementation (lines 336-341):**
```css
.page {
  max-width: 1280px;    /* 1280, not 1200 */
  padding: 16px 20px 24px;  /* half the spec padding */
}
```
No visible card/outline wrapper exists. Content sits directly on the page background.

---

### 3.3 Content Card Not Implemented — S2

**Spec (Section 4.2):** Explicit white card container with slight border. No shadow.

**Implementation:** No `.doc-wrap` or equivalent wrapper has border or background styling. The content flows directly on `var(--bg)`. The card metaphor from the spec does not exist.

---

## 4. Components: Missing or Unstyled

### 4.1 Public Record Stamp — S2

**Spec (Section 4.4):** Top-right corner, red border box, ~2deg rotation, "PUBLIC RECORD · ORC § 149.43", 12px uppercase bold red text, 2px solid red border, padding 6px 12px.

**Implementation:** `<div class="public-record-stamp">` exists in `inmate.html` line 39 but has **zero CSS definitions**. The class `public-record-stamp` does not appear anywhere in `style.css`. Renders as unstyled inline text.

---

### 4.2 Page Title Block (doc-h) — S2

**Spec (Section 5.1):** Centered title block with source attribution (11px), page title (28px bold), subtitle (12px), double red rule separator.

**Implementation:** `<header class="doc-h doc-h-center">` with children `.filing-id`, `.title`, `.sub` exist in `inmate.html` lines 41-45. None of these classes (`doc-h`, `doc-h-center`, `doc-h-stack`, `filing-id`) have CSS definitions. Renders as unstyled stacked text.

---

### 4.3 Double Red Rule (Section Divider) — S2

**Spec (Section 5.1, 10.7):** "Signature element." Two 1px red lines separated by 2-3px gap. Appears below every page title.

**Implementation:** No double-rule CSS exists. The masthead uses `border-bottom: 4px double var(--border-hi)` (line 157) which creates a double black/dark border on the header, but this is not the spec's red double rule, and it does not appear below page titles.

---

### 4.4 Legal Disclaimer Box — S1

**Spec (Section 5.4):** Dashed red border (3px dashed `--border-red`), cream background (`--bg-disclaimer`), prominent multi-line text with "ARREST IS NOT CONVICTION" in red bold uppercase, "LEGALLY PRESUMED INNOCENT" in red bold uppercase.

**Implementation (lines 1635-1658):**
```css
.inmate-hero .alert {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--fg-muted);
}
```
Rendered as plain gray muted text with a CSS-generated prefix `"Presumed innocent — "`. No box, no border, no cream background, no red emphasis text. The component's visual weight is reduced from a prominent legal notice to a de-emphasized footnote.

---

### 4.5 Booking Photo Treatment — S3

**Spec (Section 5.5):** Left column ~280px fixed. Photo is grayscale. Label above: "EXHIBIT A - BOOKING" (uppercase, bold, 12px). Caption below: "BOOKING PHOTO · ORC § 149.43" (11px, muted).

**Implementation (lines 1660-1690):** Photo width 120px (less than half spec). No grayscale filter. No "EXHIBIT A" label above the photo. Caption is overlaid on the photo with backdrop-blur, not positioned below. Caption text: "Booking photo · ORC § 149.43" (matches content but not presentation).

---

### 4.6 Data Table (Bio) Structure — S3

**Spec (Section 5.6):** Two-column key-value table. No outer border. Rows separated by 1px solid light border. Label column ~200px, uppercase, 500 weight. Value column, 400 weight.

**Implementation (lines 1717-1766):** Uses `<dl class="bio">` with a 3-column CSS grid (`grid-template-columns: repeat(3, 1fr)`). This creates a horizontal flow of dt/dd pairs rather than the spec's vertical two-column table. Labels are not uppercase. No row borders visible (transparent background, no border rule).

---

### 4.7 Inline Code Boxes — S2

**Spec (Section 5.6, note):** Inmate # and booking # inside bordered boxes: `border: 1px solid --border-light, padding: 2px 6px, background: #f9f9f9`.

**Implementation (lines 1758-1764):** `<code>` elements inside `.bio dd` are styled with accent-red color and monospace font but have no border, no background, and no box treatment. They appear as inline red text.

---

### 4.8 Scroll-to-Top Button — S3

**Spec (Section 5.9):** Dark circle (`--bg-header`), white up-arrow icon, ~40px diameter.

**Implementation (lines 2227-2246):**
```css
.back-to-top {
  background: var(--surface);  /* white, not dark */
  border: 1px solid var(--border);
  color: var(--fg-soft);       /* dark text, not white */
  width: 44px; height: 44px;
  border-radius: 50%;
  box-shadow: 0 4px 12px -4px rgba(15,23,42,0.1);
}
```
Colors inverted from spec (white background instead of dark). Has a box shadow (spec says no shadows anywhere). Size close (44 vs ~40).

---

### 4.9 Data Page Section Headings — S2

**Spec (Section 6.4):** "FILES" heading: 18px bold uppercase, letter-spacing 0.1em, preceded by thin rule, followed by double red rule.

**Implementation:** `<h2 class="sect-h">` exists in `data.html` but `.sect-h` has **zero CSS definitions**. Renders as unstyled `<h2>`.

---

### 4.10 Data Page Key-Value Fields — S2

**Implementation:** `<div class="fields">` with children `.k` and `.v` in `data.html` lines 21-34. Neither `.fields`, `.k`, nor `.v` have CSS definitions. Renders as unstyled divs.

---

### 4.11 Page Lede Text — S2

**Implementation:** `<p class="page-lede">` in `data.html` line 18. No CSS definition exists for `.page-lede`. Renders with default body styling.

---

## 5. Interactive Elements

### 5.1 Nav Links — S1

**Spec (Section 7.2):** White text on dark background. Hover: underline or opacity change. Displayed horizontally, right-aligned.

**Implementation (lines 204-216):** `.nav-link` uses dark text on light background, 6px border-radius pills, background hover state (`background: var(--bg-soft)`). Links are stacked inside a dropdown drawer on all viewport sizes, not displayed inline.

---

### 5.2 Link Hover States — S3

**Spec (Section 7.1):** Default: no underline. Hover: underline. Visited: same or darker red, not purple.

**Implementation (lines 149-150):** `a:hover { text-decoration: underline; }` matches. However `.breadcrumb a:hover` suppresses underline in favor of a background color change (line 1598), and `.nav-link:hover` uses background + no underline (line 216). Mixed behavior.

---

### 5.3 Table Row Hover — S3

**Spec (Section 7.4):** Subtle background shift to `#fafafa`.

**Implementation (line 2808):** `table.charges tbody tr:hover { background: var(--accent-bg); }` resolves to `#fff0e5` (warm orange tint, not neutral gray).

---

## 6. Responsive Behavior

### 6.1 Mobile Nav — S3

**Spec (Section 8):** "Header nav collapses to hamburger or stacks."

**Implementation:** Uses a `<details>/<summary>` disclosure pattern. On desktop, the `<details>` is forced open via `display: contents`, showing links inline. On mobile (<720px), it collapses to a hamburger icon. This partially matches but the desktop rendering is still not a horizontal inline bar as specified; it's a dropdown.

---

### 6.2 Inmate Page Two-Column Layout — S3

**Spec (Section 5.5, 8):** Desktop: photo left (~280px), data right. Mobile: photo above data.

**Implementation (lines 1609-1611):** `grid-template-columns: 120px 1fr`. Photo column is 120px, less than half the spec's 280px. Mobile stacking is implemented.

---

## 7. Spec "What This Is Not" Violations

### 7.1 Shadows Present — S3

**Spec (Section 10, Note 1, Section 12):** "No shadows anywhere. The entire site is flat."

**Implementation:** `--shadow-hover: 0 2px 8px rgba(15,23,42,0.08)` (line 56). Box shadows on `.kpi:hover`, `.search-results`, `.nav-drawer`, `.caselaw-row:hover`, `.back-to-top`, and the tier tooltip. At least 6 elements use shadows.

---

### 7.2 Border-Radius on Non-Badge Elements — S3

**Spec (Section 10, Note 2):** "No border-radius on cards or containers. Only on pill badges (4px)."

**Implementation:** `border-radius: 6px` on breadcrumb links, nav links, thumbnails, photo containers. `border-radius: 8px` on search results dropdown and filter inputs. `border-radius: 50%` on back-to-top button. The `--radius` variables are set to `0` but many elements use hardcoded radius values.

---

### 7.3 Icons and Seal Images Present — S3

**Spec (Section 10, Note 3):** "No icons. The only graphical elements are the booking photo and the scroll-to-top arrow."

**Implementation:** SVG hamburger icon in nav toggle (base.html lines 73-77). Two government seal PNG images in the masthead (`hcjc-seal.png`, `coc-seal.png`). Green dot indicator on the population counter. Disclosure triangle characters (`▾`) on collapsible sections.

---

### 7.4 Gradients Present — S3

**Spec (Section 2):** "No gradients."

**Implementation (line 3119):** `background: linear-gradient(90deg, var(--accent) 0%, var(--accent-hi) 100%)` on `.statbar-fill`.

---

### 7.5 Dashboard Elements Present — S3

**Spec (Section 12):** "Not a dashboard. No charts, no sparklines, no widgets."

**Implementation:** Sparkline SVG charts (`.sparkline`, `.spark-svg`), KPI stat cards (`.kpi`), stat bars with animated fills (`.statbar`), trend pills with up/down indicators, and a Leaflet map. These are primarily on the stats and index pages, not the inmate detail page, but the spec defines the entire site.

---

## 8. Features in Implementation Not Covered by Spec

These are not "deviations" per se but are worth noting as scope differences.

| Feature | Location | Notes |
|---------|----------|-------|
| Dark mode | `style.css` lines 79-107 | Full inverted palette |
| 10-tier charge ladder (F1-MM) | `style.css` lines 800-812 | Spec defines only felony/misdemeanor binary |
| Category color palette (8 hues) | `style.css` lines 767-774 | Spec is three-color only |
| Lightbox photo viewer | `base.html` lines 122-130 | Not in spec |
| Table/card view toggle | `style.css` lines 599-636 | Not in spec |
| Month-chip sticky nav | `style.css` lines 299-333 | Not in spec |
| Leaflet dispatch map | `web/static/map.js` | Not in spec |
| Giscus comments | `inmate.html` (further in template) | Not in spec |
| Recent-bookings photo grid | `style.css` lines 882-941 | Not in spec |
| Court calendar pages | `court.html`, `courts.html` | Not in spec |

---

## Summary: Remediation Priority

### Must Fix (S1 + S2) — 14 items

1. Body font-family: switch from Public Sans to monospace stack
2. Remove/stop loading sans-serif font files
3. Header background: change from light to dark (`#1a1a1a`)
4. Header nav: render horizontally inline on desktop, white text on dark
5. Legal disclaimer: add dashed red border, cream background, prominent red text
6. Uppercase transforms: apply broadly per spec typography table
7. Add CSS for `.public-record-stamp` (rotated red border badge)
8. Add CSS for `.doc-h`, `.doc-h-center`, `.filing-id`, `.title`, `.sub` (page title block)
9. Add CSS for double red rule section divider
10. Add CSS for `.sect-h` (data page section headings)
11. Add CSS for `.fields`, `.k`, `.v` (data page key-value layout)
12. Add CSS for `.page-lede` (data page intro text)
13. Add inline code box styling for inmate/booking numbers
14. Convert bio layout from 3-column grid to 2-column key-value table

### Should Fix (S3 + S4) — 16 items

1. Accent red: `#b30000` to `#b33a3a`
2. Body line-height: `1.55` to `1.7`
3. Body letter-spacing: `-0.005em` to `0.01em`
4. Record name: 20-24px to 36px, add uppercase + positive tracking
5. Section h2: add uppercase, increase letter-spacing, weight 700
6. Content max-width: `1280px` to `1200px`
7. Content padding: `16px 20px` to `32px 40px`
8. Add content card wrapper with 1px border
9. Booking photo: 120px to ~280px, add grayscale filter, add "EXHIBIT A" label
10. Scroll-to-top: invert colors (dark background, white arrow), remove shadow
11. Table hover: neutral gray instead of warm accent tint
12. Remove shadows from all elements
13. Remove hardcoded border-radius from non-badge elements
14. Remove gradients
15. Remove seal images from masthead
16. Disclaimer background token: add `--bg-disclaimer: #fdf5e6`

---

*End of report. 30 items identified across 8 categories.*
