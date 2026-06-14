# a11y - HTML Accessibility Audit

## Audit metadata
- Skill: jcstream-html-accessibility
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 6 (web/templates/base.html 257 lines, web/templates/index.html 310 lines, web/templates/inmate.html 224 lines, web/templates/stats.html 105 lines, web/templates/data.html 112 lines, web/templates/_card.html 21 lines)
- Time: 2026-05-14T01:42:25Z

## Observations
- base.html:67-74 declares the lightbox with role="dialog" aria-modal="true" but the JS at lines 104-130 never traps Tab focus inside the dialog; only Escape and backdrop close are wired.
- base.html:122 sets role="combobox" aria-expanded aria-controls on #search-box, yet the JS at lines 247-252 listens for Escape only. No arrow-key navigation, no aria-activedescendant, no aria-autocomplete="list" are present.
- base.html:80 declares #tier-tip with role="tooltip" but the badge that triggers it (_card.html:7) is missing aria-describedby="tier-tip". The badge already exposes aria-label, so the tooltip text never reaches AT users via the described-by relation.
- _card.html:7 uses tabindex="0" on a span with role implicit-generic. It is focusable but exposes no role; the visible "F" / "M" text is the accessible name only through aria-label, which is fine, but the badge is not a button so its keyboard activation semantics are unclear.
- index.html:66 and inmate.html-via-_card.html:19 render <time> with no datetime attribute. SC 1.3.1 prefers programmatic association of the parsed timestamp.
- index.html:127 toggles #filter-empty visibility via the JS at base.html:202 but the element has no role="status"; SR users do not get an announcement when the empty state appears.
- stats.html:17-28 emits .statbar rows as three spans with no list semantics and no programmatic association between label, value, and percent.
- base.html:234 renders the empty-state for the search results as <div class="sr-empty"> inside a role="listbox" container; a non-option child inside a listbox is invalid ARIA per SC 4.1.2.

## Analysis

The templates already implement most of the core WCAG 2.1 AA scaffolding: a working skip link, exactly one h1 per page (sr-only on homepage, visible on detail pages), labelled controls in the filter bar, scope-attributed table headers, a caption on the charges table, an aria-live region for the filter count, an aria-modal lightbox with Escape close and focus return, and prefers-reduced-motion honored in CSS. The focus visible rule is global. The skill brief flags much of this and the templates corroborate it.

The single most disruptive defect is the lightbox focus trap. SC 2.4.3 (Focus Order) and SC 2.1.2 (No Keyboard Trap, applied inversely) together require that a modal dialog confine sequential focus to its own controls while it is open. The current JS moves focus into the dialog on open and returns focus on close, but a keyboard-only user pressing Tab from the close button lands on the next focusable element in the underlying page, while the dialog is still visually overlaying it. For a screen reader user this is worse: the AT reads the page underneath while the dialog is logically still the active context. Two mitigations are valid: scope a Tab handler to #lb that cycles between the close button and the backdrop, or set inert on everything outside #lb on open (supported in current Chrome, Safari, Firefox). The inert path is more robust because it also blocks pointer interaction with the background.

The type-ahead combobox is the second highest-risk pattern. The owner has chosen the ARIA 1.2 combobox pattern (input with role="combobox", separate listbox referenced by aria-controls), which obligates the implementation to support aria-activedescendant for arrow-key navigation. The current JS only listens for Escape. A keyboard user can Tab into each option (each is an <a>), which is functional, but a screen reader using its virtual cursor will hear "combobox, expanded" and then try to navigate the listbox with arrow keys, which does nothing. The simpler path is to demote the pattern: change the input role to searchbox (or remove role entirely; type=search is fine) and the results container role to a plain region or nav. The listbox semantics are not earning their keep here because the rest of the pattern is incomplete. If kept, also add aria-autocomplete="list" and wire aria-activedescendant.

The tier-badge tooltip in _card.html:7 has a partial implementation. The tooltip element (#tier-tip in base.html:80) has role="tooltip", which only matters when an aria-describedby relation points at it. The badge currently relies on aria-label, which already exposes the badge's role and a short description; the tooltip then re-exposes a longer "card_tip" body that AT users never see. Either drop the visual tooltip from the AT tree (it is decorative since aria-label carries equivalent text), or toggle aria-describedby="tier-tip" on the badge in the showTip/hideTip handlers so SR users hear the long form. The current state is inconsistent: sighted users see the long form on hover/focus, AT users see only the short form.

The stats.html statbar markup is loose semantically. The label, count, and percent are three sibling spans inside a .statbar div with no list, no row, no grouping role. SR users will hear three disconnected strings per row, repeated for dozens of rows. The minimal fix is role="list" on .statbars and role="listitem" on each .statbar, with the children left as is. A more idiomatic fix is a <dl> with <dt> for label and <dd> for the count + percent, which then matches the bio block in inmate.html:46-59.

The <time> elements in index.html:66, inmate.html:167, and inmate.html:178 lack a datetime attribute. The visible text is a UTC timestamp string the parser already produces, so the patch is mechanical: emit datetime="{{ e.timestamp_utc }}" alongside the visible label. This unlocks SC 1.3.1 conformance and downstream tooling (Reader Mode, archive bots, search engines that respect noindex but still read structured data).

The filter empty-state paragraph (#filter-empty) is toggled by hidden via JS but has no role="status" and no aria-live. When a screen reader user types into the search input and zeroes out the results, nothing announces the change. Adding role="status" (which has implicit aria-live="polite") plus a stable text node makes the toggle audible. The .filter-count span already has aria-live="polite" and announces "0 of N shown", which partially covers this, but the empty-state paragraph carries the contextual message a user expects.

The dispatches map (index.html:94-97) lazy-loads Leaflet from a CDN. The map element has aria-label, and a <noscript> fallback links to dispatches.json. For JS-off users, the only fallback is a raw JSON link, which is not human-readable. The shooting_rows and cfs_rows lists rendered below the map (index.html:175-203) partially fill this gap when the data is present, but the relationship between map and list is not declared. This is a minor SC 1.3.1 concern and a moderate SC 1.1.1 (Non-text Content) gap if the map points carry information not present in the lists.

## Technical notes

```html
<!-- base.html:67-74, current lightbox -->
<div class="lightbox" id="lb" role="dialog" aria-modal="true" aria-label="Booking photo" hidden>
  <button type="button" class="lightbox-backdrop" aria-label="Close"></button>
  <button type="button" class="lightbox-close" aria-label="Close">&times;</button>
  <figure class="lightbox-figure">
    <img id="lb-img" src="" alt="" decoding="async">
    <figcaption id="lb-cap"></figcaption>
  </figure>
</div>
```

```js
// base.html, add to openLB / closeLB. Modern inert path.
function openLB(src, caption, alt) {
  lastFocus = document.activeElement;
  lbImg.src = src; lbImg.alt = alt || ('Booking photo: ' + (caption || ''));
  lbCap.textContent = caption || '';
  lb.hidden = false;
  // Inert everything else.
  Array.prototype.forEach.call(document.body.children, function (n) {
    if (n !== lb) n.inert = true;
  });
  lb.querySelector('.lightbox-close').focus();
}
function closeLB() {
  lb.hidden = true; lbImg.src = '';
  Array.prototype.forEach.call(document.body.children, function (n) { n.inert = false; });
  if (lastFocus && lastFocus.focus) lastFocus.focus();
}
```

```js
// base.html, Tab-trap fallback for browsers without inert.
lb.addEventListener('keydown', function (e) {
  if (e.key !== 'Tab') return;
  var focusables = lb.querySelectorAll('button, [href], [tabindex]:not([tabindex="-1"])');
  if (!focusables.length) return;
  var first = focusables[0], last = focusables[focusables.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});
```

```html
<!-- base.html:122, current combobox input -->
<input type="search" data-filter="search" id="search-box"
       placeholder="name, charge, ORC code, or #" autocomplete="off"
       role="combobox" aria-expanded="false" aria-controls="search-results">
<div class="search-results" id="search-results" role="listbox" hidden></div>
```

```html
<!-- Recommended: drop ARIA listbox semantics, use the search landmark. -->
<input type="search" data-filter="search" id="search-box"
       placeholder="name, charge, ORC code, or #" autocomplete="off"
       aria-autocomplete="list" aria-expanded="false" aria-controls="search-results">
<div class="search-results" id="search-results" role="region"
     aria-label="Search results" hidden></div>
<!-- Each result becomes a plain <a> (no role="option"); the empty-state stays a <p>. -->
```

```html
<!-- _card.html:7, add aria-describedby and use a button role -->
<button type="button"
        class="tier tier-{{ tier.kind }} tier-corner"
        aria-label="{{ tier.label }}"
        aria-describedby="tier-tip"
        data-tip="{{ card_tip(inm) }}">{{ tier.short }}</button>
<!-- A button is keyboard-activatable. The describedby relation is harmless when #tier-tip is empty/hidden because role="tooltip" elements are typically only announced on focus. -->
```

```html
<!-- index.html:66 and _card.html, emit datetime on <time> -->
<time datetime="{{ e.timestamp_utc }}">{{ e.timestamp_utc }}</time>
<time datetime="{{ inm.booking_date }}">booked {{ inm.booking_date }}</time>
```

```html
<!-- index.html:127, give the empty state status semantics -->
<p class="empty" id="filter-empty" role="status" hidden>
  No one in custody matches that filter.
</p>
<!-- role="status" implies aria-live="polite"; visibility toggle then announces. -->
```

```html
<!-- stats.html:17-28, give statbars list semantics -->
<div class="statbars" role="list">
  {% for label, count in rows %}
  <div class="statbar" role="listitem">
    <span class="statbar-label">{{ label }}</span>
    <span class="statbar-track" aria-hidden="true">
      <span class="statbar-fill {{ accent }}" style="width: {{ '%.1f' % pct }}%"></span>
    </span>
    <span class="statbar-val">{{ "{:,}".format(count) }} <small>{{ '%.0f' % pct }}%</small></span>
  </div>
  {% endfor %}
</div>
```

## Findings

### a11y-F1. Lightbox dialog does not trap Tab focus
- WCAG: 2.4.3 Focus Order (A), 2.1.2 No Keyboard Trap (A, inversely), 4.1.2 Name Role Value (A)
- Severity: high. Confidence: high.
- Where: web/templates/base.html:67-74 (markup) and 104-130 (JS).
- Defect: Tab from the close button escapes the modal into the underlying page; the page is not made inert; SR users continue to read background content while the visual dialog covers it.

### a11y-F2. Combobox pattern is incomplete
- WCAG: 4.1.2 Name Role Value (A), 2.1.1 Keyboard (A)
- Severity: high. Confidence: high.
- Where: web/templates/base.html:122-123, 214-253.
- Defect: input has role="combobox" aria-expanded aria-controls but no aria-activedescendant, no aria-autocomplete, and no arrow-key navigation. The listbox contains a non-option child (sr-empty div). The pattern signals a contract the implementation does not honor.

### a11y-F3. Tier badge tooltip has no aria-describedby
- WCAG: 1.3.1 Info and Relationships (A), 4.1.2 Name Role Value (A)
- Severity: medium. Confidence: high.
- Where: web/templates/_card.html:7 (badge) and web/templates/base.html:80 (tooltip element).
- Defect: badge uses tabindex="0" with aria-label but is not declared as a button and does not describedby the tooltip. SR users hear only the short label; the longer card_tip body is invisible to AT.

### a11y-F4. <time> elements emit no datetime attribute
- WCAG: 1.3.1 Info and Relationships (A)
- Severity: medium. Confidence: high.
- Where: web/templates/index.html:66, 178, 197 and web/templates/_card.html (no <time> there) and web/templates/inmate.html:167.
- Defect: rendered <time> contains a parseable UTC string only in the inner text. No programmatic timestamp is exposed to AT, Reader Mode, or downstream tools.

### a11y-F5. Filter empty-state is not announced
- WCAG: 4.1.3 Status Messages (AA)
- Severity: medium. Confidence: high.
- Where: web/templates/index.html:127 and web/templates/base.html:202.
- Defect: #filter-empty toggles hidden but has no role="status" / aria-live. SR users do not hear "No one in custody matches that filter" unless they navigate to it.

### a11y-F6. Statbar rows lack list semantics
- WCAG: 1.3.1 Info and Relationships (A)
- Severity: low. Confidence: medium.
- Where: web/templates/stats.html:17-28, 56-60, 68-79.
- Defect: bar rows are three sibling spans with no grouping role. SR users hear disconnected fragments per row over a long page.

### a11y-F7. Recent activity card has two anchors with no grouping
- WCAG: 1.3.1 Info and Relationships (A), 2.4.4 Link Purpose (A)
- Severity: low. Confidence: medium.
- Where: web/templates/index.html:54-80, web/templates/_card.html:5-20.
- Defect: each card has a thumb anchor and a name anchor with similar destinations; SR users hear the link list as duplicates. The card itself is not a single landmark or article. Cards announce as a flat sequence of name, charge, id-chip with the thumb link redundant.

### a11y-F8. Dispatch map text fallback is a raw JSON link
- WCAG: 1.1.1 Non-text Content (A)
- Severity: low. Confidence: low.
- Where: web/templates/index.html:94-97.
- Defect: when JS is off the only fallback is a link to dispatches.json. The shooting and CFS lists below the map are conditionally rendered and not declared as a fallback.

## Recommendations

- F1: add `inert` to all body children except `#lb` on open, restore on close; add a Tab cycler keyed to `#lb` as a fallback for browsers without `inert` (see Technical notes block 2 and 3).
- F2: drop role="combobox" from the input, drop role="listbox" and role="option" from results; keep `aria-autocomplete="list"`, `aria-expanded`, `aria-controls`. The results region becomes `role="region" aria-label="Search results"` with plain `<a>` children. Move the sr-empty into a `<p>` outside the region or give it `role="status"`.
- F3: convert the badge `<span>` to `<button type="button">` and add `aria-describedby="tier-tip"`. Toggle `aria-describedby` only when the tooltip is visible if you want to avoid speaking the long form on every focus traversal.
- F4: in `web/build.py` (or directly in the templates), emit `<time datetime="{{ value }}">{{ value }}</time>` at every site.
- F5: add `role="status"` to `#filter-empty` in index.html:127. No JS change needed; toggling `hidden` on a status region announces.
- F6: add `role="list"` to `.statbars` and `role="listitem"` to `.statbar` in stats.html (or switch to a `<dl>` to match the bio block in inmate.html).
- F7: wrap each card body in a single `<article>` with `aria-labelledby` pointing at the name anchor; or merge thumb and name anchors so the card has one primary link plus a "View photo" affordance.
- F8: when `cfs_rows` or `shooting_rows` is present, render them inside the map section as the visible fallback, and tie them with `aria-describedby` from the map container. When neither is present, the `<noscript>` link is fine.

## Remediation plan

1. Land F1 (lightbox focus trap with inert + Tab cycler). Highest user impact, surgical JS change in base.html.
2. Land F5 (role="status" on #filter-empty) and F4 (datetime on <time>). Pure markup, zero risk.
3. Land F3 (badge becomes button, aria-describedby="tier-tip"). Verify CSS still styles `button.tier` the same as `span.tier`; if not, fix CSS in the same patch.
4. Land F2 (demote combobox pattern). Update both markup in base.html:122-123 and the render() function around base.html:236-241 in one commit so ARIA and behavior stay aligned.
5. Land F6 / F7 / F8 as a single low-risk semantics patch.

## Cross-references

- CSS contrast on .muted, .danger, .misd, tier badge colors, and focus ring visibility on dark backgrounds: jcstream-css-accessibility-performance.
- Legal-text wording, FCRA notice, ORC citations, sealing/expungement framing, noindex policy: jcstream-html-content-governance.
- Template escaping of inmate names, ld+json injection surface, inline script safety for the lightbox and combobox JS: jcstream-html-template-security.

## Confidence and limitations

High confidence in F1, F2, F4, F5 because they are directly observable in the static templates and the inline JS. Medium confidence in F3 because the badge's keyboard activation semantics depend on whether the owner wants the tooltip itself to be the announcement, or wants aria-label to remain the only AT exposure. Lower confidence in F7 and F8 because they involve subjective trade-offs against the dark-theme card density and against keeping the map progressive-enhancement-only. I did not test with a live screen reader (NVDA, VoiceOver, Orca) and did not load the rendered docs/ output in a real browser. No outbound network was used. Findings are scoped to web/templates/*.html with style.css consulted only for focus-visible cross-reference.

End of report.
