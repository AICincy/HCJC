# spa-structural - Structural Audit: Document, Style, and Script Strata

## Audit metadata
- Skill: ad-hoc (structural deconstruction request)
- Commit: 24165142c (data+site: sweep 2026-05-14T22:31Z)
- Branch: claude/refactor-spa-structure-WUjPh
- Date: 2026-05-14
- Files scanned: web/templates/base.html 310, web/templates/index.html 409, web/templates/inmate.html 363, web/templates/stats.html 211, web/templates/statute.html 123, web/templates/data.html 115, web/templates/_card.html 21, web/static/style.css 1838, web/build.py 1744
- Live targets probed: https://www.aretheyinjail.com/ (200), /stats/, /data/, /statute/, /static/style.css, /robots.txt, plus a 404 path for header diffing
- Pytest baseline: not re-run (no code changes proposed inline)

## Premise correction (read first)

The task framed JCStream as a Single-Page Application. It is not. JCStream is a server-prebuilt static document tree: Jinja templates compiled to flat HTML in `docs/` at every sweep, served by GitHub Pages behind Cloudflare. There is no client-side router, no hydration step, no bundler. Most "SPA tuning" advice (route code-splitting, hydration cost, bundle size budgets, virtual-DOM reconciliation) does not apply. The findings below treat the site as what it is: a pre-rendered static site with a thin progressive-enhancement script layer.

This distinction matters because three things you would normally audit on a SPA are non-issues here, and one thing you would not normally focus on is the primary risk:

1. Non-issues: bundle size, hydration mismatch, route-change spinners.
2. Primary risk: HTTP response headers from GitHub Pages, which the site does not control today and which constitute the actual Zero-Trust deficit.

## Observations

### Document layer (HTML / Jinja)

- Templates extend a single `base.html` (web/templates/base.html, 310 lines). One `<main id="main" class="page">` wraps content (line 62). The `<a class="skip-link" href="#main">` at line 33 targets it correctly.
- `<html lang="en">` is set at base.html:2. `<meta charset="utf-8">` and viewport meta at lines 4-5. `noindex, noarchive` robots meta at line 10 (intentional, per ORC 2953.32 sealing protocol).
- Inline scripts in templates: one IIFE in base.html (lines 93-308, 216 lines), one IIFE in index.html (lines 301-406, 106 lines), one JSON-LD `<script type="application/ld+json">` in inmate.html (lines 18-33), one optional Giscus `<script src="https://giscus.app/client.js" async>` in inmate.html (lines 342-355, gated on `giscus.repo_id`).
- One external CSS request: Google Fonts at base.html:24 (`fonts.googleapis.com/css2?family=Inter:...&family=JetBrains+Mono:...&display=swap`). Preconnect hints to `fonts.googleapis.com` and `fonts.gstatic.com` are set with `crossorigin` at lines 22-23.
- One internal CSS request: `/static/style.css?v={{ css_version }}` at base.html:25. `css_version` is the first 10 hex chars of `sha256(style.css)` (web/build.py:101) so the URL changes only when bytes change. Live response confirms: `?v=67bdd07ce3`.
- Built homepage weight: 1,598,365 bytes uncompressed, 200,943 bytes gzipped on the wire (1.5 MB vs 196 KB). HCSO roster history fans out into months of inline cards; this is by design and is partially mitigated by `content-visibility: auto` (style.css cross-references in audit 10).
- Two `<script>` block sites in index.html: the filter/lightbox/search IIFE inherited via base.html, plus a separate Leaflet lazy-loader IIFE at index.html:301-406 gated on `{% if map_points %}`.

### Style layer (CSS)

- Single stylesheet, web/static/style.css, 1,838 lines, 59,275 bytes uncompressed, served as `text/css; charset=utf-8`.
- 537 rule blocks (rough count via `^[^/].*\{`). 17 `@media` queries. 9 `!important` declarations total (sample includes the `body.is-table` table-mode overrides at lines 507-508 and `.sr-only` at line 73). One universal selector block (`* { box-sizing: border-box }` at line 56) plus the reduced-motion `*, *::before, *::after { transition: none !important; ... }` block at lines 60-65.
- Deepest selector found: `body.is-table .month .card-inmate > .tier.tier-corner` (style.css:513), 4 combinators. No selectors exceed 5 combinators. No `id` selectors used for styling general layout (only the documented singletons `#tier-tip`, `#lb` per audit 10).
- Light-theme tokens declared in `:root` at lines 8-54. Dark theme was retired (CLAUDE.md, audit 10). Token palette discipline: contrast on `--fg-dim`/`--bg-soft`/`--surface-hi` was already flagged as fail-AA in audit 10 (css-F1, css-F2). Those findings are still live on this commit; not re-litigated here.
- `prefers-reduced-motion: reduce` at lines 60-66 zeroes transitions, animations, and the auto-generated view-transition pseudo-element animations (the `::view-transition-*` block is the documented pattern for suppressing `@view-transition: navigation: auto` at line 59).

### Script layer (Vanilla JS)

- Total custom JS, hand-counted: ~322 lines, all inline, all wrapped in IIFE (`(function () { ... })();`) so nothing leaks to `window`.
- Module 1, base.html:93-308. Five sub-features:
  1. Hash-to-details opener: when a fragment matches an id inside a `<details>`, the details opens and the target scrolls. Wired on `hashchange`, page load, and clicks on `a[href^="#"]`.
  2. Lightbox: opens on click of any `[data-photo]`, uses `aria-modal="true"`, sets `inert` on every other `document.body` child, and has a Tab-cycler fallback for browsers without `inert`. Escape closes. Focus restoration to `lastFocus` on close.
  3. Tier-badge tooltip: pointer/focus-driven. Tooltip body is `#tier-tip role="tooltip"` at the body level (not inside cards) so card-level `content-visibility: auto` paint containment does not clip it. `pointer-events: none` so it never steals the mouse.
  4. Roster view toggle: `body.is-table` flip, persisted in `localStorage['jcs-view']`. Sets `aria-pressed` and the visible label.
  5. Filter bar: cards snapshot taken once, then `.is-filtered-out` class toggled per card on input. Weeks/months collapse when all their cards filter out.
  6. Search dropdown: `search.json` fetched lazily on first focus, type-ahead matches against `name + charge + #id`, capped at 20 hits. Sets `aria-expanded` on the input.
- Module 2, index.html:301-406. Map lazy-loader: IntersectionObserver with `rootMargin: '600px 0px'` triggers Leaflet load. Leaflet 1.9.4 pinned with SRI hash `sha256-20nQCchB9co0qIjJ/8oJjpZSlrckbW6c8r9XSqHjvmo=`, served from unpkg with jsdelivr fallback. On all failures, the `.cfs-map` div is replaced with a one-line muted note pointing to the lists below.
- Module 3, inmate.html JSON-LD: pure data, no behavior.
- Module 4, inmate.html Giscus: only emitted when `giscus.repo_id` is non-empty (the env-driven feature flag documented in CLAUDE.md). Currently disabled in production.
- Console-error surface: every `fetch().then().catch()` is closed (search.json catch at base.html:276, dispatches.json catch at index.html:397, Leaflet onerror waterfall at index.html:337). No `console.log` calls in the inline modules; no `console.error` either, but the visible failure UX (the muted `.cfs-map-failed` note) substitutes.

### Render path

The critical path on cold load is:
1. HTML arrives (gzip 196 KB on the homepage).
2. Preconnect to `fonts.googleapis.com` + `fonts.gstatic.com` opens early. These are configured with `crossorigin` so the actual font fetch can reuse the connection.
3. Two CSS requests fire in parallel: Google Fonts and `/static/style.css`. Both are render-blocking.
4. `font-display: swap` is requested in the Google Fonts URL, so text paints in the fallback face immediately and swaps in Inter when ready. This mitigates FOIT but accepts a brief FOUT.
5. No render-blocking JS. The inline scripts are at the end of `<body>`, parsed and executed after the DOM is built.

### HTTP / network surface

Header probe across `/`, `/stats/`, `/data/`, `/statute/`, `/static/style.css`, `/robots.txt`, and a 404 path:

- Present on all 200 responses:
  - `Strict-Transport-Security: max-age=31556952` (about 365 days, no `includeSubDomains`, no `preload`)
  - `Content-Type` correct everywhere
  - `Vary: Accept-Encoding`
  - `Cache-Control: max-age=600` on root
  - `Server: cloudflare`
- Missing on 200 responses:
  - `Content-Security-Policy`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options` or CSP `frame-ancestors`
  - `Referrer-Policy`
  - `Permissions-Policy`
  - `Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy`, `Cross-Origin-Resource-Policy`
- Present on the 404 page only: `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'`. This is GitHub Pages' built-in 404.html policy, not a site-wide policy. It does not protect 200 responses.
- Signature leaks:
  - `X-GitHub-Request-Id: ...` on every response identifies the origin as GitHub Pages. Removable only by migrating off GitHub Pages.
  - `Server: cloudflare` identifies the CDN. Expected; not a vulnerability.
  - `Access-Control-Allow-Origin: *` is set on GitHub Pages by default. For a public-records mirror this is intentional and harmless (no authenticated endpoints exist), but worth documenting.
- HSTS lifetime: 31,556,952 s is just under one year (1 year = 31,536,000). The `preload` flag is absent, which is the correct call until the owner is ready to commit to no HTTP-only subdomains forever.

### Responsive and adaptive layer

- One viewport meta declared at base.html:5. No `user-scalable=no`, no `maximum-scale`. Good.
- Single mobile breakpoint at `@media (max-width: 720px)`. This breakpoint is referenced 11 times across the stylesheet (masthead density, nav-hint hiding, table-mode columns collapsing to 3-track grid, id-chip hiding, hero photo unfloating, bio grid collapsing). Two cards `.cards` use `auto-fill, minmax(15.5rem, 1fr)` so they reflow to a single column on narrow viewports without a media query (style.css line where `.cards` is defined; container-query-style intrinsic responsive layout).
- `.month-nav` is sticky under the masthead (`position: sticky; top: var(--masthead-h)` at style.css:201-204) and horizontally scrolls (`overflow-x: auto` at line 209). On a touch viewport this gives a chip rail that does not stack.
- Adaptive typography is minimal. Body is 14 px (style.css:84). The mobile breakpoint drops `.masthead .nav-link` from 14 px to 13 px (style.css:1826). No fluid `clamp()` is used; type does not scale with viewport width between breakpoints. For an information-dense roster page this is a defensible call (predictable line lengths), but worth noting.
- WCAG 2.2 SC 2.5.8 (target size, 24 by 24 px minimum) was spot-checked at the live size of interactive elements:
  - `.nav-link` 14 px text + 8/14 px padding -> ~30 by 42 px. Pass.
  - `.view-toggle` declares `height: 36px` at style.css:482. Pass.
  - `.lightbox-close` is `36x36 px` at style.css:1529. Pass.
  - `.back-to-top` is `40x40 px` at style.css:1547-1548. Pass.
  - `.filter-bar select` and search are `height: 36px` at style.css:463. Pass.
  - `.month-nav .chip` is `padding: 4px 10px` with `font-size: 12px` -> ~26 by 26 px. Borderline; the 6 px gap (style.css:207) puts adjacent chips inside the WCAG 2.2 spacing exception, so this passes by spec but is the closest call on the page.
  - `.tier.tier-corner` button on the card is about 20 by 28 px (style.css:663-680 and 700-705). Below the 24 by 24 minimum. The card is positioned-absolute inside the card so it does not benefit from the inline-text exception. FAILS SC 2.5.8.
  - `.id-chip` link inside cards is 11 px text with line-height yielding about 16 px height (style.css:641-648). FAILS SC 2.5.8.

### WCAG 2.2 AA empirical contrast (jcstream-a11y-auditor pass, 2026-05-14)

The light theme retired the dark theme's hand-tuned contrast tokens (per CLAUDE.md). Empirical contrast measurements show several sites of use now fall under AA. The most consequential surprise is the focus-ring regression: `.filter-bar select:focus` and `input[type="search"]:focus` strip `outline` to zero and substitute a `box-shadow: 0 0 0 3px var(--accent-bg)` ring (style.css:472-477). `--accent-bg` is `#eef0fc` on `--bg` `#fafaf8`; the ratio measures 1.05:1. The visible focus indicator is effectively invisible. SC 2.4.7 (Focus Visible) fails.

Numerical contrast failures observed against the current commit:

| Site | Style.css | Color pair | Ratio | SC | Status |
|------|-----------|-----------|-------|----|--------|
| `.filter-bar select:focus` ring | 472-477 | `--accent-bg` on `--bg` | 1.05:1 | 1.4.11 / 2.4.7 | FAIL |
| `.tier-F3` chip | 688 | white on `#d96b46` | 3.42:1 | 1.4.3 (10.5 px bold) | FAIL |
| `.card-inmate .id-chip` | 644 | `--fg-dim` `#94a3b8` on `--surface` | 2.56:1 | 1.4.3 (11 px) | FAIL |
| `.card-inmate .charge .ct-count` | 637 | same | 2.56:1 | 1.4.3 | FAIL |
| `.coms-more` | 439 | same | 2.56:1 | 1.4.3 | FAIL |
| `.spark-ticks` | 314 | same | 2.56:1 | 1.4.3 | FAIL |
| `.cfs time` | 877 | same | 2.56:1 | 1.4.3 | FAIL |
| `.rb-meta` | 817 | same | 2.56:1 | 1.4.3 | FAIL |
| `.masthead .nav-hint` | 187 | `--fg-dim` on `--bg-soft` | 2.31:1 | 1.4.3 | FAIL |
| `.thumb.thumb-placeholder` initials | 606 | same | 2.31:1 | 1.4.3 | FAIL |
| `.rb-meta-sep` middot | 818 | `--border-hi` `#d4cfc4` on white | 1.55:1 | 1.4.1 / 1.4.3 | FAIL |
| `.tier-MM` | 695 | `#64748b` on `#f4f3ef` | 4.29:1 | 1.4.3 (10.5 px bold) | FAIL |
| `.tag-released` | 854 | `#4f7c3a` on composited tint | 4.21:1 | 1.4.3 (10 px bold) | FAIL |
| `.trend-pill.is-up` | 324 | red on tint | 4.33:1 | 1.4.3 (12 px bold) | FAIL (narrow) |

Note that audit 10 already filed `css-F1` against `--fg-dim` measuring 4.20-4.62:1 across surfaces. The token value has since been changed (audit 10 measured `#7c828f`; current source is `#94a3b8`), making the failure worse and broadening the affected call sites. The current value flunks every surface in the palette, not just `--surface-hi`.

Two non-contrast SC 2.2 items also flagged:
- SC 2.5.8 (Target Size, Minimum): `.tier.tier-corner` and `.id-chip` link as enumerated above. FAIL.
- SC 1.1.1 (Non-text Content): `.rb-card` mugshots at index.html:89 (and the similar block in inmate.html:275 for similar-inmates) use `alt=""` while the parent `<a>` carries no `aria-label`. The card has a `<h4 class="rb-name">` adjacent, which makes a defensible "alt='' is decorative" argument under the WAI image-decision-tree, but the rb-card geometry places the photo as the leftmost glance with no equivalent alt text in the link's accessible name (the link name comes from concatenating child text). Recommend `alt="Booking photo of {{ inm.full_name }}"` or move the name into the `<a>`'s `aria-label`. The detail-page hero photo at inmate.html:43 uses `alt="HCSO booking photo of {{ inmate.full_name }}"` correctly.

One SC 2.4.11 (Focus Not Obscured, Minimum) consideration: sticky masthead (118 px) + sticky month-nav rail creates a ~160 px obscured band at the top of the viewport. A focused element inside an open `<details class="month">` reached via `#m-...` fragment lands beneath the sticky stack. Per agent's read, the obscure is partial not total, so the SC passes (the AA criterion is "entirely hidden"). The AAA criterion 2.4.12 (Focus Not Obscured, Enhanced) does not pass cleanly; AA is the project target so this is informational.

The reduced-motion contract (style.css:60-66) is correct. ARIA inventory is correct: `aria-current="true"` (inmate.html:220, statute.html:68), `aria-pressed` (view-toggle JS), `role="dialog" aria-modal="true"` (lightbox), `role="tooltip"` (tier-tip), `aria-live="polite"` on the filter count (index.html), sr-only h1 only on homepage.

## Analysis

### What is well-architected

The progressive-enhancement contract is the strongest thing about JCStream's client layer. Every interactive feature has a no-JS path: the lightbox falls through to the photo's `href`, the filter bar's controls are `hidden` until JS un-hides them (`bar.hidden = false` at base.html:221), the search dropdown is opt-in, the Leaflet map degrades to a list below. Disabling JavaScript does not break the site; it only removes affordances. This is a non-trivial discipline to maintain, and the inline-IIFE pattern (no module loader, no globals) keeps it within reach.

The lightbox is correctly built. `role="dialog"`, `aria-modal="true"`, `aria-label`, and `hidden` are all on the dialog (base.html:78). On open, focus is captured to `.lightbox-close`; on close, focus is returned to `lastFocus`. The `inert` attribute is applied to every other `document.body` child so screen readers do not read the background; for browsers without `inert` support, a Tab-cycler fallback at base.html:145-156 keeps focus inside the dialog. This implementation directly closes the a11y-F1 finding from audit 07 (the lightbox-focus-trap defect on the prior commit).

CSS variable discipline is tight. Hex outside `:root` is rare (audit 10 enumerated the exceptions: the print at-rule, the Leaflet map fallback, the duplicated `#c98a8a`/`#9ab4d3` in `.sr-tier` and `.tier-*`). `!important` use is restricted to `.sr-only` and the print at-rule (with the `body.is-table` exception flagged here). The retired dark theme was cleanly removed rather than carrying parallel token sets.

Content-hash cache-busting on the stylesheet is correct (web/build.py:101). The URL changes only when `style.css` bytes change. The earlier audit warned against keying off the data timestamp (which would bust the cache every 30 minutes); the current key is content-derived and stable across sweeps that do not touch CSS.

### What constitutes the real risk

The site has no `Content-Security-Policy` on its actual content responses. The 404 page has one because GitHub Pages ships a default 404.html with a hard-coded CSP meta tag; this does not protect any 200 response. Without a CSP:

- Any inline-script injection that bypasses Jinja's autoescape would execute unconstrained.
- A future third-party include (analytics, alternative comment system, image hosting) has no allow-list to violate.
- `frame-ancestors` is absent, so the site can be iframed by anyone. Clickjacking risk is low (no authenticated forms exist) but the protection is free if a policy is added.

GitHub Pages does not support custom HTTP response headers. The realistic options are:

1. **CSP meta tag inside `<head>`.** Covers `script-src`, `style-src`, `img-src`, `font-src`, `connect-src`, `frame-src`, `default-src`, `base-uri`, `form-action`, `object-src`. Does not cover `frame-ancestors` (must be an HTTP header) or `X-Frame-Options`. Cheapest path; deliverable in one template edit.

2. **Cloudflare Worker fronting the apex.** The site already sits behind Cloudflare (the `Server: cloudflare` and `cf-cache-status: DYNAMIC` headers confirm a Cloudflare proxy is in front of `_via: 1.1 varnish` -> Fastly -> GitHub Pages). A Worker bound to the route can inject headers without changing origin. Operationally, this is a Cloudflare-account change, not a code change in this repo. Out of scope for a build-time fix.

3. **Migrate to Cloudflare Pages.** `_headers` file gives full control. Larger change; the deployment workflow shifts from GitHub Pages to Cloudflare Pages.

For inline scripts to be compatible with a meaningful `script-src`, one of two routes is needed:

- Keep `'unsafe-inline'`. Practical but defeats most of the value of CSP for script.
- Externalize the three inline IIFEs to `/static/main.js` and `/static/map.js`, then hash them with SHA-256 and include the hash in `script-src`. This makes the policy meaningfully tight. Cost: one additional cacheable static asset per page (the JS becomes cross-page-cacheable, partially offsetting the extra request). Build hook needs to compute the hash and inject it into the meta tag, the same way `css_version` is already computed.

### Render-path inefficiencies

Two render-blocking dependencies block first paint: the Google Fonts CSS and the site stylesheet. `display=swap` keeps text painted in the fallback face during the swap window, so the perceived bottleneck is shorter than the wire-time would suggest. Two practical reductions exist:

1. **Self-host Inter and JetBrains Mono.** Replace the `fonts.googleapis.com` URL with two `@font-face` blocks in `style.css` pointing to `/static/fonts/inter-*.woff2` and `/static/fonts/jetbrains-mono-*.woff2`. Drops the cross-origin CSS fetch, drops the two preconnects, removes the third-party privacy exposure. Adds about 200 KB to the `web/static/` tree (woff2 subset for Latin + Latin-Ext). Build pipeline grows a one-time `web/static/fonts/` directory; sweep does not need to touch it.

2. **The font-family stack lists `"Geist"` first, but Geist is never loaded.** style.css:51-53 declare `--font-sans`, `--font-serif`, `--font-mono` with `"Geist"` and `"Geist Mono"` as the leading entry, but the Google Fonts URL at base.html:24 only requests Inter and JetBrains Mono. Every text element walks the fallback chain past a face that will never resolve. The fix is either to add Geist to the fonts request (it is on Google Fonts) or to remove it from the stack. Behaviorally this is a no-op today because the fallback works; it is wasted descriptor walking and a misleading source-of-truth.

### Script-layer microcosts

- `Array.prototype.forEach.call(document.body.children, ...)` is called twice on every lightbox open and close (base.html:127, 134) to toggle `inert`. On the homepage `document.body` has under 10 direct children. Negligible. Not worth changing.
- The filter-bar implementation snapshots cards once and uses class toggles instead of `display: none` (base.html:225, 242). `.is-filtered-out` is applied with CSS `display: none` (style.css search confirms). This is the right pattern; the DOM is never restructured during filter input.
- The search index `idx` is the entire `search.json` parsed into memory after first focus. For the current roster size (about 700 to 1,100 inmates on a typical day) this is a few hundred KB of JSON, well within budget. If the roster grew an order of magnitude, the type-ahead loop at base.html:282-285 (`for (var i = 0; i < idx.length && hits.length < 20; ...)`) would still be fine because of the early-exit at 20 hits.

### Responsive depth-of-field

The single 720 px breakpoint is austere by modern standards but well-chosen for an information-dense data site. The lack of fluid typography is consistent with the editorial intent: short fixed line lengths read better for record-list scanning than dynamic scaling. Worth noting rather than changing.

The `.cards` grid using `repeat(auto-fill, minmax(15.5rem, 1fr))` is what gives the layout its smooth reflow without media queries. This pattern is correctly applied throughout (cards, rb-grid, stat-card) and is the dominant responsive mechanism. The breakpoint exists only to handle the bits that intrinsic layout cannot express (hiding chrome, collapsing the masthead).

### What audit 11 does not re-litigate

Audit 10 (css_a11y_performance) already covers `--fg-dim` AA failures on `--surface-hi`, the duplicated `.banner` block, the dead `open: true` print declaration, and the hard-coded hex strays. Audit 07 (html-accessibility) already covers the JSON-LD escaping and combobox-pattern gaps. Audit 01 (security_networking) covers PRA-loop SMTP and the noindex/noarchive contract. Findings from those reports remain open; this report cross-references them rather than restating them.

## Findings

| ID | Sev | Conf | One-line summary | Owner skill |
|----|-----|------|------------------|-------------|
| spa-A1 | high | high | `.filter-bar select:focus` and `input[type="search"]:focus` replace `outline` with a `box-shadow: 0 0 0 3px var(--accent-bg)` ring measuring 1.05:1 on `--bg`; focus indicator is effectively invisible (style.css:472-477). FAILS WCAG 2.2 SC 2.4.7 and SC 1.4.11 | jcstream-stylesheet-author |
| spa-A2 | high | high | `--fg-dim` `#94a3b8` text fails AA on every palette surface (2.31-2.56:1) across nine call sites including `.id-chip`, `.rb-meta`, `.cfs time`, `.spark-ticks`, `.nav-hint`, `.thumb-placeholder` initials. Regression from audit 10's css-F1, which measured the prior `#7c828f` value | jcstream-stylesheet-author |
| spa-A3 | high | high | `.tier-F3` chip white-on-`#d96b46` measures 3.42:1 at 10.5 px bold; AA threshold is 4.5:1 (does not qualify as "large text"). Sole 10-tier-ladder chip that fails (style.css:688) | jcstream-stylesheet-author |
| spa-A4 | med | high | `.tier-MM` `#64748b` on `#f4f3ef` measures 4.29:1 at 10.5 px bold; `.tag-released` `#4f7c3a` on tint 4.21:1 at 10 px bold; `.trend-pill.is-up` 4.33:1 narrow fail. All three are small bold and require AA 4.5:1 | jcstream-stylesheet-author |
| spa-A5 | med | high | `.rb-meta-sep` middot uses `--border-hi` `#d4cfc4` on white measuring 1.55:1; functionally invisible separator (style.css:818). FAILS SC 1.4.3, compounds SC 1.4.1 because color is the only separator | jcstream-stylesheet-author |
| spa-A6 | med | high | `.tier.tier-corner` button is about 20 by 28 px; `.id-chip` link about 16 px tall. Both below WCAG 2.2 SC 2.5.8 24 by 24 minimum and not inline-text-exempt (positioned absolute / chip context) | jcstream-stylesheet-author |
| spa-A7 | med | high | `.rb-card` mugshot at index.html:89 uses `alt=""` with no `aria-label` on the parent `<a>`; the photo is the leftmost glance and orphan-decorative under SC 1.1.1. Detail-page hero photo at inmate.html:43 is correct | jcstream-template-author |
| spa-S1 | high | high | No `Content-Security-Policy` on 200 responses; 404 page has one (GitHub Pages default) which does not protect content responses | jcstream-template-author |
| spa-S2 | med | high | No `X-Content-Type-Options: nosniff` on any response; mime-confusion attack surface is non-zero for the `/static/` tree | jcstream-template-author |
| spa-S3 | med | high | No `Referrer-Policy` declared; default behavior in modern browsers is OK but not asserted in HTML or HTTP | jcstream-template-author |
| spa-S4 | med | high | No `frame-ancestors` directive and no `X-Frame-Options`; site is iframeable by any origin | jcstream-template-author |
| spa-S5 | med | high | No `Permissions-Policy`; future feature-policy regressions cannot be detected at the boundary | jcstream-template-author |
| spa-P1 | low | high | `--font-sans`, `--font-serif`, `--font-mono` lead with `"Geist"` / `"Geist Mono"` but Geist is never loaded (style.css:51-53); every paint walks a dead descriptor | jcstream-stylesheet-author |
| spa-P2 | low | high | Two render-blocking CSS requests on cold paint (Google Fonts + site CSS); self-hosting fonts collapses this to one request and removes third-party dependency | jcstream-template-author |
| spa-P3 | low | med | HSTS lifetime is 31,556,952 s (just under one year); `includeSubDomains` and `preload` absent. Acceptable today but worth confirming the owner's stance | jcstream-template-author |
| spa-X1 | info | high | `.month-nav .chip` interactive target is 26 by 26 px (style.css:215-228), the smallest control on the page; passes SC 2.5.8 via the spacing exception but is the closest call | jcstream-stylesheet-author |
| spa-X2 | info | high | Inline IIFE script blocks (322 LOC total) prevent any `script-src` policy other than `'unsafe-inline'` from being useful; externalizing to `/static/main.js` + `/static/map.js` enables tight CSP | jcstream-template-author |
| spa-X3 | info | med | Sticky masthead plus month-nav creates a ~160 px obscured band; hash-jumps to in-page anchors land partly under it. SC 2.4.11 (AA) passes via "not entirely hidden"; SC 2.4.12 (AAA) does not | jcstream-stylesheet-author |

## Recommended progressive refactoring roadmap

### Tier 0a - critical accessibility patches (under 30 minutes)

These should land before Tier 0 because users on assistive technology hit them today.

R0a.1. Restore a visible focus ring on filter inputs. Replace `style.css:472-477`:

```css
.filter-bar select:focus,
.filter-bar input[type="search"]:focus {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-color: var(--accent);
}
```

Drops the invisible `box-shadow` ring; `--accent` `#4860d8` on `--bg` measures about 5.1:1 against the page, comfortably above SC 1.4.11's 3:1 non-text threshold. (Resolves spa-A1.)

R0a.2. Rebalance `--fg-dim` from `#94a3b8` to a value that passes AA on every palette surface. `#6b7a8e` measures about 3.6:1 (still clearly hierarchical) which lifts most call sites toward AA; `#5a6470` measures about 5.0:1 (full AA, slightly tighter visual hierarchy). Owner pick:
   - Conservative AA: change `--fg-dim` to `#5a6470` site-wide.
   - Hierarchical (preferred by audit 10's css-F1 framing): escalate every textual `--fg-dim` use to `--fg-muted` and leave `--fg-dim` for non-text affordances only.
   (Resolves spa-A2.)

R0a.3. Darken `.tier-F3` to push contrast over 4.5:1. Two options:
   - Background `#d96b46` -> `#c45a35` keeps the orange semantics. (Quickest.)
   - Ink white -> `#3a1a06` retains current bg.
   The 10-tier ladder palette is the load-bearing carrier of statutory severity, so the choice matters; the conservative option is to darken the bg one notch and re-verify F2 and F4 still read as a smooth gradient. (Resolves spa-A3.)

R0a.4. Apply the small bold ink darkening for spa-A4: `.tier-MM` `#64748b` -> `#5a6470`; `.tag-released` `#4f7c3a` -> `#3f6230`; `.trend-pill.is-up` red -> one notch darker. Each is a single hex swap.

R0a.5. Replace `.rb-meta-sep` (style.css:818) with `var(--fg-muted)` instead of `var(--border-hi)`, or swap the middot for a visible glyph. (Resolves spa-A5.)

R0a.6. Add `aria-label="Booking photo of {{ inm.full_name }}"` to the rb-card photo `<a>` at index.html:86, inmate.html:273, or rewrite the inner `<img>` alt to `"Booking photo of {{ inm.full_name }}"`. The detail-page hero already does the latter. (Resolves spa-A7.)

R0a.7. Bump `.tier.tier-corner` and `.id-chip` to a 24 by 24 px hit area without changing the visual chip size. The non-disruptive recipe is to add an invisible pseudo-element overlay:

```css
.tier.tier-corner { position: relative; }
.tier.tier-corner::before { content: ""; position: absolute; inset: -4px; }
.id-chip { position: relative; }
.id-chip::before { content: ""; position: absolute; inset: -6px; }
```

`::before` carries pointer events when the parent is the trigger. Verify no other absolutely-positioned descendant on the cards conflicts before merging. (Resolves spa-A6.)

### Tier 0 - cheap wins (under 30 minutes)

R0.1. Remove `"Geist"` and `"Geist Mono"` from the font stacks in style.css:51-53, or add them to the Google Fonts URL in base.html:24. Pick one. (Resolves spa-P1.)

R0.2. Add a `Content-Security-Policy` meta tag to base.html `<head>`, immediately after the existing `<meta name="robots">`. Suggested first iteration (compatible with current inline scripts):

```html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  base-uri 'self';
  object-src 'none';
  img-src 'self' data: https://*.tile.openstreetmap.org;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  script-src 'self' 'unsafe-inline' https://giscus.app https://unpkg.com https://cdn.jsdelivr.net;
  connect-src 'self' https://*.tile.openstreetmap.org https://giscus.app;
  frame-src https://giscus.app;
  form-action 'self';
  upgrade-insecure-requests;
">
```

This resolves spa-S1 partially. `'unsafe-inline'` on `script-src` is retained for now; Tier 2 below removes it.

R0.3. Add a `<meta name="referrer" content="strict-origin-when-cross-origin">` to base.html `<head>` to assert the policy in HTML even though the HTTP header is missing. (Resolves spa-S3.)

### Tier 1 - moderate (1 to 2 hours)

R1.1. Externalize the three inline scripts. Move the base.html IIFE to `web/static/main.js`, the index.html map IIFE to `web/static/map.js`. Replace inline blocks with `<script src="{{ base_url }}/static/main.js?v={{ main_js_version }}" defer></script>` and the equivalent for the map. Compute `main_js_version` and `map_js_version` the same way `css_version` is computed today (web/build.py:101 pattern; sha256 hex digest of the file content, sliced to 10 chars, registered as `env.globals[...]`).

R1.2. Add SHA-256 hashes for the two scripts to the CSP `script-src` directive and drop `'unsafe-inline'`:

```
script-src 'self' 'sha256-<MAIN_JS_HASH>' 'sha256-<MAP_JS_HASH>' https://giscus.app ...;
```

Cleaner approach: leave them as plain `'self'` entries (since they live on the same origin) and the hash is unnecessary; only the inline blocks would have needed it. The hash route is for any genuinely-inline residue (the JSON-LD block in inmate.html is `type="application/ld+json"`, which is not a JavaScript content type and is not blocked by `script-src`).

R1.3. Add `X-Content-Type-Options: nosniff` semantics by setting the meta tag inside `<head>`: `<meta http-equiv="X-Content-Type-Options" content="nosniff">`. (Note: not all browsers honor the meta form. The HTTP header is the canonical mechanism. This is a partial mitigation for spa-S2 only.)

### Tier 2 - asset pipeline (half-day)

R2.1. Self-host Inter and JetBrains Mono. Download the Latin subset woff2 files, drop them in `web/static/fonts/`, replace the Google Fonts `<link>` with `@font-face` blocks at the top of style.css. Drop the two preconnect hints. (Resolves spa-P2. Improves cold-paint LCP by one CSS round-trip and removes a third-party DNS exposure.)

R2.2. Minify `style.css` at build time. Add `csscompressor` or `rcssmin` to `requirements.txt`; in `web/build.py`, wrap the CSS file read at line 101 to also write a minified copy that is served from `/static/style.css` while the unminified source stays in the repo. Estimated wire savings: 35 to 40 KB unminified, about 5 KB after gzip.

### Tier 3 - infrastructure (1 day+, owner decision)

R3.1. To get full HTTP-header control (and resolve spa-S2/S3/S4/S5 cleanly at the boundary), choose one of:

- Front the current GitHub Pages origin with a Cloudflare Worker bound to `www.aretheyinjail.com`. Worker injects all missing headers, no origin change. Owner can implement in the Cloudflare dashboard; this repo only needs to set the headers it depends on (none new today).
- Migrate from GitHub Pages to Cloudflare Pages. Add `_headers` file at the repo root (or in `docs/`, depending on the deploy config) and replace the `.github/workflows/` Pages job with a Cloudflare Pages deployment. Larger change; affects CI and the GitHub Pages branch lifecycle.

Neither of these is in this repo's purview today. Worth surfacing in the README's deployment note so a future contributor sees the decision.

## Technical notes

### Schema-validated CSP exemplar (for reference)

The CSP suggested in R0.2 was checked by hand against the runtime requirements:

- `script-src 'self'` covers `/static/main.js` after R1.1.
- `script-src 'unsafe-inline'` (or the hash equivalent) covers the inline IIFEs while they remain inline.
- `script-src https://giscus.app` covers the Giscus loader at inmate.html:342 when the env vars are set.
- `script-src https://unpkg.com https://cdn.jsdelivr.net` covers the dual-CDN Leaflet load at index.html:315-319.
- `connect-src https://*.tile.openstreetmap.org` covers the OpenStreetMap tile fetches at index.html:381.
- `connect-src https://giscus.app` covers the Giscus JSON-RPC API (when enabled).
- `img-src https://*.tile.openstreetmap.org` covers Leaflet's tile `<img>` elements.
- `frame-src https://giscus.app` covers the Giscus iframe (Giscus injects an iframe into the page; without `frame-src` the comment section would not render).
- `font-src https://fonts.gstatic.com` covers Inter and JetBrains Mono.
- `style-src https://fonts.googleapis.com 'unsafe-inline'` covers Google Fonts CSS and the inline `style="..."` attributes in templates (there are several: index.html:23 sets a `color: var(--warn)` on the trend pill, several SVG `polyline` and `circle` attribute styles, plus the lightbox image inline style is built in JS).

R2.1 (self-host fonts) would let `style-src` drop `https://fonts.googleapis.com` and `font-src` drop `https://fonts.gstatic.com`. The inline `style="..."` attributes remain, so `style-src 'unsafe-inline'` stays unless the few inline styles are refactored into CSS classes.

### Build-helper sketch for the script-hash flow

In `web/build.py`, alongside the existing `css_version` registration:

```python
_main_js = _STATIC / "main.js"
_map_js  = _STATIC / "map.js"
env.globals["main_js_version"] = _hl.sha256(_main_js.read_bytes()).hexdigest()[:10] if _main_js.exists() else "dev"
env.globals["map_js_version"]  = _hl.sha256(_map_js.read_bytes()).hexdigest()[:10]  if _map_js.exists()  else "dev"
```

(Matches the existing pattern at web/build.py:101. No new dependency.)

### What this audit explicitly does not propose

- No refactor to a JavaScript framework or SSR runtime. The current static-render-with-progressive-enhancement model is a deliberate choice and the right one for a public-records mirror.
- No client-side router. There are no routes that benefit from in-page navigation; every page is a distinct record set served by a distinct URL.
- No service worker / offline cache. The site updates every 30 minutes; cached responses would lie about custody status, which is the load-bearing field. Caching is correctly delegated to Cloudflare and the browser via `Cache-Control: max-age=600`.
- No change to the noindex/noarchive contract. The robots meta at base.html:10 is load-bearing for the ORC 2953.32 sealing protocol and must stay.

## End of audit
