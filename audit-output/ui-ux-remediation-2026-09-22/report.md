# JCStream / aretheyinjail.com
## UI/UX and visual design remediation report

**Audit date:** 2026-09-22 UTC  
**Audited site:** `https://www.aretheyinjail.com/`  
**Audited source:** repository checkout `/home/user/HCJC`, source revision `db29ce3`; deployed static output was also verified from `origin/main` revision `54c1ef2` and served locally from the checked-in `docs/` directory. The sweep-data commit changes roster data, not the UI source.  
**Evidence bundle:** `audit-output/ui-ux-remediation-2026-09-22/`

## Executive summary

JCStream has a strong foundation for a high-stakes public-records interface: the roster is immediately searchable, the filter controls progressively enhance a usable static page, the visual system has a coherent Public Sans / IBM Plex Mono pairing, dark mode is implemented without a light-flash, and the detail-photo lightbox has working focus return and Escape handling.

The most important remediation work is accessibility-related rather than cosmetic:

1. **Fix dark-theme contrast failures in small, semantically important labels and alerts.** Axe found 38 failing nodes across representative pages. Several dark-theme colors are just below the 4.5:1 AA threshold for normal-sized text.
2. **Restore a non-color distinction for links in prose.** The global stylesheet removes underlines except on hover. Axe found 158 affected link nodes across 10 page types, which fails WCAG 1.4.1's requirement that color not be the sole differentiator.
3. **Repair the degree-strip interaction contract.** The UI copy says the strip can be selected, the JavaScript has a click handler, but the final stylesheet sets `.tier-strip-seg` to `pointer-events: none`. This is a concrete broken interaction.
4. **Increase actionable badge hit areas.** The roster renders 20px-high tier buttons. The audit measured 80 sub-24px actionable targets on the mobile homepage sample.
5. **Make wide data tables easier to use on phones.** The detail charges table is 669px wide inside a 366px scroll container at a 390px viewport; the bond schedule table is 590px wide. The current behavior technically preserves the data but makes comparison and discovery difficult.
6. **Normalize page hierarchy.** The homepage's visible H1 is 20px while major reference pages use 44px. The homepage is the site's primary task surface, yet its title is visually subordinate to the large month heading and dense roster grid.

No production code was changed by this audit. The report and reproducible evidence are the deliverables.

## Priority model

- **P0:** Fix before the next public UI release. Blocks or materially impairs access to core information.
- **P1:** Fix in the next design-system / interaction pass. Causes recurring task friction or a broken/ambiguous interaction.
- **P2:** Fix during the next polish pass. Improves consistency, touch use, or maintainability without blocking the core task.

## Evidence and method

### Automated and rendered checks

The evidence bundle contains:

- `scans/axe-report.json`: axe-core 4.13.0 scan results for home, inmate, help, stats, courts, judges, bond schedule, data, transparency, archive, visit, and 404 pages, in desktop and mobile viewports, with both theme states where applicable.
- `scans/probe-results.json`: rendered font sizes, placeholder styles, overflow measurements, table dimensions, and masthead dimensions.
- `scans/interact-results.json`: keyboard/search/filter/theme interaction observations.
- `scans/contrast-computations.txt`: reproducible WCAG relative-luminance calculations.
- `shots/`: 48 screenshots covering desktop, mobile, narrow 320px, light/dark, full-page, focused controls, search results, filters, and the lightbox.

The browser audit used Chromium with viewport sizes **1440x900**, **390x844**, and **320x600**. The local static server used the checked-in `docs/` output, which is the repository's GitHub Pages artifact. The public site fetch returned the same page structure and live roster UI before the local render was used for repeatable screenshots.

### Standards used

- **WCAG 2.2 Success Criterion 1.4.3, Contrast (Minimum):** normal text requires at least 4.5:1; large text requires 3:1. https://www.w3.org/TR/WCAG22/#contrast-minimum
- **WCAG 2.2 Success Criterion 1.4.1, Use of Color:** color must not be the only visual means of conveying information or distinguishing a link. https://www.w3.org/TR/WCAG22/#use-of-color
- **WCAG 2.2 Success Criterion 2.5.8, Target Size (Minimum):** pointer targets are at least 24 by 24 CSS pixels, subject to defined exceptions. https://www.w3.org/TR/WCAG22/#target-size-minimum
- **WCAG 2.2 Success Criterion 1.4.10, Reflow:** content should reflow without two-dimensional scrolling at 320 CSS pixels, except for content that requires two-dimensional layout. https://www.w3.org/TR/WCAG22/#reflow
- **WCAG 2.2 Success Criterion 2.4.7 and 2.4.11, Focus Visible / Focus Appearance:** keyboard focus must remain visible and sufficiently distinguishable. https://www.w3.org/TR/WCAG22/#focus-visible and https://www.w3.org/TR/WCAG22/#focus-appearance

## Findings and recommendations

### P0-01. Dark-theme small text fails contrast in recurring components

**Impact:** Users with low vision or users viewing the default dark theme may not be able to distinguish key labels, warnings, and category markers. This is particularly serious because the affected text is used for task orientation, safety/scam warnings, and statistics.

**Observed evidence:**

- Axe reported `color-contrast` violations on **38 nodes** across the tested page set. The failures occur in the dark theme on home, help, stats, courts, bond, and visit pages.
- Representative axe targets include:
  - `.visit-card:nth-child(2) > .visit-card-body > .visit-card-kicker` (`Your case`)
  - `.visit-card:nth-child(3) > .visit-card-body > .visit-card-kicker` (`Research`)
  - `.alert > strong:nth-child(1)` / `.alert.inline-alert > strong` (`Scam alert`, `Arrest is not conviction`, and bond warnings)
  - `.kpi:nth-child(1) > .label` (`In custody`)
  - `.statbar-label > .chap-2919.chap` (`Family / Domestic`)
- The computed dark-theme values are documented in `scans/contrast-computations.txt`:
  - `#F0433A` on the card surface `#1F232A`: **4.18:1**.
  - `#F0433A` on the warning surface `#2B1D19`: **4.31:1**.
  - `#A06BE8` on `#1F232A`: **4.33:1**.
  - The affected labels are 11px to 11.5px or normal body text, so the 3:1 large-text allowance does not apply.
- Source evidence: `web/static/style.css:3061-3088` applies `--accent` to the first KPI label; the dark token is defined as `#F0433A` in the dark-theme token block. The alert uses `--warn` at `web/static/style.css:3670-3684`.

**Recommendation:**

- Use a dedicated dark-theme small-text semantic token rather than the same vivid accent used for large headings and borders. For example, `#FF6B5F` provides approximately **5.65:1** on `#1F232A` and **5.82:1** on `#2B1D19`; `#FF7A6E` provides approximately **6.20:1** and **6.39:1** respectively.
- For KPI labels, use the existing `--fg-muted` (`#A3ABB6`) or a dedicated semantic muted label token. It measures approximately **6.80:1** on the dark card surface.
- For category text such as the dark-theme purple family category, use a lightened token such as `#B58BEF` or `#BC96F1` rather than `#A06BE8`; these measure approximately **5.93:1** and **6.58:1** on the card surface.
- Add a contrast-token test that checks every text token against each surface token at its actual computed font size. Do not rely only on comments in the stylesheet claiming a ratio.

**Acceptance criteria:** Axe reports no `color-contrast` violations in either theme on the audited page set; every normal-sized text combination is at least 4.5:1.

---

### P0-02. Prose links are distinguished by color only

**Impact:** Users who cannot perceive color, and users scanning dense legal/reference content, cannot reliably tell links from surrounding prose until hover or focus.

**Observed evidence:**

- Axe reported `link-in-text-block` on **158 nodes** across the representative page types. The largest counts were courts (42), data (36), help (30), visit (16), stats (9), bond (9), inmate (7), transparency (6), judges (2), and home (1).
- The scan's representative targets include `HCSO inmate search`, `HomeWAV`, `R.C. 149.43`, `schedule`, `history.json`, `courtclerk.org`, and `earlier bookings archive`.
- The rendered computed style for a normal prose link is `text-decoration: none`; this is confirmed in `scans/probe-results.json`.
- Source evidence: `web/static/style.css:302-304` globally defines `a { color: var(--link); text-decoration: none; }` and only adds underline on hover. This fails the static distinction required by WCAG 1.4.1.

**Recommendation:**

- Add a persistent underline to links inside prose containers: paragraphs, list items, definitions, table cells, ledes, legal disclosures, and field/value reference blocks. Use `text-underline-offset: 0.12em` and an adequate thickness for readability.
- Keep navigation, tabs, cards, buttons, and compact data controls as explicit exceptions, provided their role and state are conveyed by layout, borders, focus, or labels.
- Preserve the current blue link tokens because they already have strong contrast against their intended surfaces. Changing the color alone cannot solve the 1.4.1 issue: the surrounding body text is also a relevant comparison.
- Add a visual regression/axe rule that checks prose links in both themes and at rest, not only on hover.

**Acceptance criteria:** Every link embedded in a prose block has an always-present non-color distinction, normally an underline; axe reports no `link-in-text-block` violations.

---

### P1-03. The degree strip advertises selection but is disabled by CSS

**Impact:** The visual strip suggests a filter interaction that does nothing when clicked or tapped. This creates a particularly confusing mismatch for users trying to interpret felony/misdemeanor distribution.

**Observed evidence:**

- `web/templates/_roster_tool.html:99-104` renders the strip and its caption. The caption says: “Select a color to filter.”
- `web/static/main.js:672-682` contains a delegated `.tier-strip-seg` click handler that sets the tier select and dispatches a change event.
- `web/static/fold-chrome.css:124-126` overrides the interaction with `.tier-strip-seg { cursor: default; pointer-events: none; }` and disables hover outline.
- The final rendered page therefore has both the event handler and the disabling CSS. The evidence screenshot set includes the home and archive roster renders; the exact CSS/JS mismatch is more definitive than a screenshot alone.

**Recommendation:** Choose one of two coherent designs:

1. **Keep it interactive:** remove `pointer-events: none`, restore `cursor: pointer`, give each segment a real accessible button or link semantics, provide a visible focus state, and expose each segment's count/name to assistive technology.
2. **Make it informational:** remove the click handler and change the caption to “Roster share by most serious charge,” with a nearby conventional tier select for filtering.

The preferred solution is a real button per segment inside a labelled group. A single `role="img"` wrapper with an aria-label is not enough to expose separate selectable segments.

**Acceptance criteria:** Clicking/tapping a visible segment either changes the filter or the copy no longer claims it is selectable; keyboard users can reach and operate the same function.

---

### P1-04. The degree legend is hidden from assistive technology while the visual strip is compressed

**Impact:** The visual key for charge categories and felony/misdemeanor coding is present for sighted users but is deliberately removed from the accessibility tree. The 4px distribution strip is also too compressed to communicate individual categories visually without the surrounding text.

**Observed evidence:**

- `web/templates/_roster_tool.html:80` sets `<p class="legend" aria-hidden="true">`, hiding the legend's category labels from screen readers.
- `web/static/fold-chrome.css:91` sets `.tier-strip-cap { display: none; }`, hiding the explanatory caption visually while the strip remains only 4px tall.
- The strip's wrapper does have an aria-label, but that label describes the degree distribution as a whole, not the color legend or the individual interaction affordances.

**Recommendation:**

- Remove `aria-hidden="true"` from the legend if it communicates information needed to interpret the roster. Give it a visible heading or `aria-label="Charge category legend"`.
- Keep the thin bar as a visual summary, but provide an adjacent text summary or accessible list containing each degree and count.
- If segments remain interactive, expose their accessible names and pressed/selected state independently.

**Acceptance criteria:** A screen-reader user can determine what each category color means and can obtain every count without relying on the CSS color encoding.

---

### P1-05. Wide data tables are technically scrollable but difficult to use on mobile

**Impact:** Important charge and bond information requires horizontal scrolling and can separate labels from values. This is usable in a narrow technical sense, but it is poor for quick lookup on a phone and creates a two-dimensional navigation burden.

**Observed evidence:**

- At a 390px viewport, the inmate charges table measured **669px wide** inside a wrapper with **366px client width** and `overflow-x: auto`; evidence is in `scans/probe-results.json`.
- At the same viewport, the bond schedule table measured **590px wide**. The page itself did not gain global horizontal scroll because the table wrapper clips/scrolls, but the user still must perform horizontal table navigation.
- At 320px, the homepage document itself did not overflow (`scrollWidth == clientWidth`), which is a positive result; the issue is localized to wide data tables rather than global layout failure.

**Recommendation:**

- For the inmate charge table, switch to a stacked definition-list/card pattern below a breakpoint, or keep a table with a sticky first column and a visible “scroll horizontally” affordance.
- For the bond schedule, use a responsive two-column card/list representation on narrow screens: offense/statute, degree, and amount should remain visible together.
- Ensure focus does not move into offscreen columns without scrolling the focused cell into view.
- Add a 320px and 390px test for every table, including long statute/case identifiers.

**Acceptance criteria:** The primary label/value relationship is visible together at 320px and 390px; any remaining horizontal scroll is clearly announced and does not hide the key column.

---

### P1-06. Homepage heading hierarchy is visually inconsistent with the rest of the site

**Impact:** The homepage's primary task lacks the visual emphasis established by the reference pages. This makes the page feel like a dense dashboard rather than a clearly guided entry point, and it weakens information hierarchy above the roster.

**Observed evidence:** Rendered heading measurements from `scans/probe-results.json` and `scans/` heading output:

- Home H1, “Search the roster”: **20px**.
- Inmate detail H1: **24px**.
- Help, stats, courts, judges, bond, data, transparency, archive, visit, and safety H1s: generally **44px** on desktop.
- Homepage month H2s render at approximately **22px** while the H1 is 20px, so a repeated content heading can be visually larger than the page's primary heading.
- Source evidence: `web/static/fold-chrome.css:102-111` explicitly sets `.section-h h1` to `clamp(16px, 2vw, 20px)`.

**Recommendation:**

- Establish a page-level type scale with a clear homepage exception documented in the design system. For example, use a 28-32px homepage H1 at desktop and 24-28px on mobile, then use 18-22px for month headings.
- Keep the “Last checked” metadata adjacent to the heading, but reduce its visual competition through spacing and muted styling rather than shrinking the H1.
- Make the search panel visually subordinate to the H1 but clearly primary relative to the roster.

**Acceptance criteria:** The homepage H1 is visibly the strongest heading before the roster, and the type scale is consistent across desktop and mobile without causing wrapping problems.

---

### P1-07. Search control text is undersized for a primary mobile interaction

**Impact:** The site's primary action is a search field, but the field uses 13px text. This is below the common 16px mobile form-control convention and can trigger browser zoom behavior in some mobile browsers, while also reducing legibility.

**Observed evidence:**

- `web/static/style.css:690-707` sets the search input to `font: inherit` and then explicitly `font-size: 13px`.
- `scans/probe-results.json` confirms a 13px computed font size for the search input and a 390px mobile viewport audit.
- The input height is a reasonable 44px, so the problem is text scale rather than the overall control hit area.

**Recommendation:** Set the input to at least 16px on mobile and desktop, preserving the 44px height. Adjust placeholder color only after verifying it against the dark and light input backgrounds. Keep the visible placeholder concise: “Name, charge, or ORC code.”

**Acceptance criteria:** The search field computes to at least 16px at mobile widths, remains visually aligned with the Filters control, and does not cause layout shift.

---

### P1-08. Homepage roster tier buttons are below the 24px minimum target height

**Impact:** The grade badges are actionable controls that show charge detail, but their 20px height is small for touch use. Because they sit in card corners, they can also be difficult to hit without accidentally activating a nearby card/link.

**Observed evidence:**

- `web/static/style.css:940-954` sets `.tier` to `height: 20px` and font-size 10.5px.
- The mobile target scan measured **80** actionable elements below 24px on the homepage sample. The repeated roster tier buttons were 31.5px wide by **20px high**.
- These are `<button>` elements in `web/templates/_card.html:11`, not merely decorative labels, so the inline-content exception to WCAG 2.5.8 does not apply.

**Recommendation:** Increase the tier button's hit area to at least 24px high, preferably 28px, while keeping the visible label compact through padding and line-height. Ensure the expanded tooltip remains associated with the button via `aria-describedby` and remains usable at the larger hit area.

**Acceptance criteria:** Every tier button is at least 24x24 CSS pixels at mobile widths, has a visible focus indicator, and does not overlap adjacent card controls.

---

### P2-09. Body and metadata type scales are dense on roster and legal surfaces

**Impact:** The overall visual language is coherent, but the roster combines 15px body text with 12-13px metadata, 10.5px tier badges, 11px legal/kicker text, and IBM Plex Mono identifiers. On a page containing sensitive names and charges, the result is information-dense and makes secondary facts compete with or crowd the primary name.

**Observed evidence:** The rendered typography probe recorded:

- Body: 15px / 24.75px.
- Roster name: 17px on the sampled desktop render.
- Charge: 13px.
- ID chip: 12px in the probe and 11px in the base card rule at `web/static/style.css:907`.
- Tier badge: 10.5px at `web/static/style.css:940-954`.
- Visit/help kicker: 11px.
- Footer/legal text: 11-12px on mobile pages.

This is not asserted as an automatic WCAG failure; it is a visual hierarchy and scanning concern supported by the rendered measurements and screenshots.

**Recommendation:** Reserve the smallest type for nonessential metadata. Keep names at the largest card size, raise charge text to 14px where space permits, and use 12px minimum for identifiers and status metadata. Increase line-height for legal/help text rather than shrinking it further. Define these choices as semantic tokens instead of page-specific values.

**Acceptance criteria:** A user can scan name, charge, custody/booked date, and severity in that order at a glance on a 390px viewport, without relying on hover or color.

---

### P2-10. Desktop navigation consumes substantial vertical space before the core task

**Impact:** The desktop masthead combines a centered brand, running roster metric, theme toggle, a multi-row site rail, and a second court-reference row. This creates a visually heavy top chrome for a task site whose primary action is search.

**Observed evidence:**

- The desktop screenshot `shots/home-desktop-dark-fold.png` shows the multi-row navigation rail before “Search the roster.”
- The source groups 7 “Roster tools” links and 8 “Court reference” links in `_nav_groups.html`; `web/static/fold-chrome.css:18-29` deliberately wraps the groups on desktop.
- The home screenshot and rendered probe show the core search heading begins only after the masthead/nav region.

**Recommendation:** Keep the brand, theme toggle, and one primary navigation row in the masthead. Move lower-frequency court-reference links into the menu drawer or a clearly labelled “Reference” section. If the two-row rail is retained, establish a stronger visual group separation and reduce vertical padding.

**Acceptance criteria:** At a 900px-high desktop viewport, the brand, search heading, search field, and first roster row are visible without the navigation rail dominating the first screen.

---

### P2-11. Unused font assets add design-system ambiguity and page weight

**Impact:** The source ships JetBrains Mono and IBM Plex Sans files, while the active stylesheet uses Public Sans and IBM Plex Mono. This does not directly harm the rendered page, but it makes the visual system harder to maintain and increases static asset weight.

**Observed evidence:**

- `web/static/fonts/` contains JetBrains Mono and Plex Sans assets.
- A repository search found no active stylesheet reference to JetBrains Mono or Plex Sans; the active tokens in `web/static/style.css` use `Public Sans` and `IBM Plex Mono`.
- The homepage load probe recorded approximately 61 resources and approximately 975KB transferred locally; the static CSS is approximately 153KB. The unused font files are approximately 123KB combined in the source font directory.

**Recommendation:** Remove unused font files from the published artifact, or document them as reserved design-system assets outside the page's deployment bundle. Keep one canonical font family per semantic role.

**Acceptance criteria:** The published asset directory contains only fonts referenced by CSS, and the design-system documentation names the active families and fallback stack.

## Positive findings worth preserving

1. **Progressive enhancement:** The roster search/filter markup is present without requiring JavaScript. This is visible in `_roster_tool.html`, where the search, selects, month details, and cards are rendered server-side.
2. **Search feedback:** The rendered interaction test found that typing `jones` produced a visible results panel with 17 results, a `role="status"` announcement of “17 results,” and 11 visible roster cards.
3. **Theme persistence:** The theme toggle changed the rendered root from dark to light in the interaction test, and `theme-init.js` applies the stored theme before paint.
4. **Lightbox behavior:** The detail-page lightbox opened with the correct photo alt text and caption, moved focus to the close button, and restored focus after Escape. This is recorded in `scans/interact-results.json` and the screenshot `shots/lightbox.png`.
5. **Responsive global layout:** At 320px, the homepage had `scrollWidth == clientWidth`, so the overall page did not create global horizontal scrolling. The remaining table issue is localized and can be addressed without undoing the broader responsive layout.
6. **Reduced-motion handling:** The stylesheet includes a `prefers-reduced-motion: reduce` rule that disables transitions and animations, and the JavaScript uses instant scrolling when the preference is active.
7. **Contrast in many core tokens:** The light-theme body/link, placeholder, primary text, and tier badge combinations passed the measured AA checks. The primary failures are concentrated in a small set of dark-theme semantic tokens and link decoration.

## Suggested implementation order

### Sprint 1: accessibility blockers

1. Add persistent prose-link underlines and exceptions for navigation/control surfaces.
2. Replace failing dark-theme small-text tokens and add automated contrast-token tests.
3. Increase tier button hit areas to at least 24px.
4. Make the degree strip either genuinely interactive and keyboard accessible or informational with accurate copy.
5. Expose the legend and degree counts to assistive technology.

### Sprint 2: mobile task completion

1. Redesign the inmate charges and bond schedule tables for narrow screens.
2. Increase the search input to 16px.
3. Test focus movement and target spacing at 320px and 390px.
4. Verify all warning/scam callouts in both themes after token changes.

### Sprint 3: hierarchy and visual polish

1. Normalize the homepage H1/month heading scale.
2. Reduce desktop masthead/navigation height while preserving discoverability.
3. Establish semantic typography tokens for name, charge, metadata, kicker, and legal text.
4. Remove unused font assets and update the design-system documentation.

## Evidence index

| Evidence | Location |
|---|---|
| Main report | `audit-output/ui-ux-remediation-2026-09-22/report.md` |
| Automated accessibility results | `scans/axe-report.json` |
| Contrast calculations | `scans/contrast-computations.txt` |
| Rendered layout/type/overflow probes | `scans/probe-results.json` |
| Keyboard/search/theme/lightbox checks | `scans/interact-results.json` |
| Desktop homepage fold | `shots/home-desktop-dark-fold.png` |
| Mobile homepage | `shots/home-mobile-dark-fold.png` |
| Narrow 320px homepage | `shots/home-narrow-dark-fold.png` |
| Mobile inmate detail | `shots/inmate-mobile-dark-fold.png` |
| Search dropdown state | `shots/search-dropdown.png` |
| Open filters state | `shots/filters-open.png` |
| Focus states | `shots/focus-search.png`, `shots/focus-tier.png` |
| Lightbox state | `shots/lightbox.png` |

## Limitations

- This is a source- and rendered-page audit, not a moderated usability study with people who use screen readers, magnification, switch access, or cognitive aids.
- Automated axe results are evidence of concrete failures, not a proof that all accessibility issues are found. Manual testing with NVDA/JAWS/VoiceOver and keyboard-only task scenarios is still recommended.
- The live roster contents change frequently. Screenshots and counts in the evidence bundle are time-stamped by the audit run; UI claims are tied to selectors, source lines, and rendered measurements rather than to any individual's record.
- The report does not evaluate the legal accuracy, completeness, or appropriateness of the underlying public-record data.
