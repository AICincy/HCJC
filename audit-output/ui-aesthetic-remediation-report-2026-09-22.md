# UI & Aesthetic Audit — AreTheyInJail.com / JCStream

**Audit date:** 2026-09-22 (UTC)  
**Target:** [aretheyinjail.com](https://aretheyinjail.com/) — the published content resolved to the `www` hostname during review  
**Scope:** User-interface design, information architecture, visual language, responsive behavior, and accessibility-adjacent interaction risks. This is a remediation report, not a formal WCAG conformance certification.

## Executive summary

The product is substantially more capable than its first impression suggests. The live site provides a direct roster search, client-side filtering, judge/court reference pages, provenance dates, source links, correction/removal routes, and explicit presumption-of-innocence language. The implementation also has several good foundations: a skip link, native disclosure elements, visible focus rules, reduced-motion handling, accessible labels for the core search/filter controls, and progressive enhancement in the roster UI ([base template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L52-L124), [roster tool](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L17-L131), [motion/focus CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L262-L304)).

The main problem is not missing functionality; it is **hierarchy**. The visual system currently presents a large, dense data surface before it clearly establishes the product name, the independent/non-governmental relationship, or the next step for family members and people seeking help. The dark theme also contains a measurable small-text contrast regression in its latest accent override. On mobile, important secondary navigation is deliberately compressed into horizontal rails without a consistent cue that more content exists.

### Overall assessment

| Dimension | Assessment | Why |
|---|---|---|
| Core utility | **Strong** | Search, filters, roster detail, court reference, and source links are present. |
| Task hierarchy | **Needs remediation** | The roster dominates; help, bond, visit, and court routes are secondary or below the roster. |
| Trust/identity | **Needs remediation** | `JCStream` is the dominant name even though the public URL and user intent are “Are they in jail?”. The masthead seal/social link adds affiliation ambiguity. |
| Visual coherence | **Mixed** | The system is deliberate, but mono wordmark + double rule + pills + cards + severity fills + multiple category colors create a dashboard/incident-board tone. |
| Accessibility foundation | **Good with targeted gaps** | Several strong primitives are present; the dark accent token and pointer-only tier strip need attention. |
| Perceived performance | **Needs remediation** | The homepage ships hundreds of roster cards in its initial HTML and only paginates after JavaScript runs. |

## Priority summary

| ID | Priority | Finding | Recommended outcome |
|---|---:|---|---|
| UI-01 | P1 | Public identity and product name are misaligned | Make **Are They In Jail?** the user-facing masthead; keep JCStream as attribution. |
| UI-02 | P1 | First-viewport task routing is too roster-centric | Put a compact “start here” action row immediately below search/freshness. |
| UI-03 | P1 | Dark-theme active text has contrast regressions | Remove `--accent-quiet` from text use or retune it; add automated light/dark contrast checks. |
| UI-04 | P1 | Client-side pagination arrives after a large initial DOM | Server-render a small first slice; keep the full archive behind a deliberate route. |
| UI-05 | P2 | Navigation is over-complete and flat | Reduce primary navigation to the five most common tasks; move technical links to More/footer. |
| UI-06 | P2 | Shape and color language is visually noisy and can read as punitive | Adopt one shape vocabulary and reserve saturated red for warnings/state. |
| UI-07 | P2 | The 4px severity strip is an ambiguous pointer-only control | Make it decorative or turn each segment into a real, keyboard-operable control. |
| UI-08 | P2 | Mobile in-page navigation hides overflow without a consistent cue | Wrap/group sections or add an explicit “more sections” affordance. |
| UI-09 | P2 | Record pages lack a compact next-step action cluster | Add Verify, Bond, Visit/contact, Court record, Help, and Correction actions near the record heading. |
| UI-10 | P2 | Judge cards repeat generic “Profile” controls | Give each disclosure a name-specific label and make the action purpose explicit. |
| UI-11 | P2 | Important legal/provenance copy is too small and too long in-flow | Keep concise framing inline; move full policy text to a structured legal/data surface. |

---

## Findings and remediation details

### UI-01 — The public identity is not the user’s mental model

**Priority: P1 — trust, comprehension, and continuity**

#### Evidence

- The live homepage title is `JCStream · 1210 currently in custody`, while the requested public address is `aretheyinjail.com`; the live page’s primary heading is “Search the roster” ([live homepage](https://www.aretheyinjail.com/)).
- The masthead visibly brands the site **JCStream** and describes it as “Hamilton County · Justice Center mirror” ([base template, lines 56–60](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L56-L60)).
- The footer correctly says the project is independent and not affiliated with the Sheriff’s Office or a government entity ([base template, lines 145–150](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L145-L150)), but that clarification arrives after the strongest visual identity has already been established.

#### Why it matters

A person arriving from a search result, a shared link, or the domain name should understand both **what this is** and **whether it is official** before interpreting a name/photo/charge record. “JCStream” sounds like a technical product or data feed; it does not answer the natural-language question implied by the domain. The adjacent seal link to “Hamilton County Booking Photos on Facebook” further increases the risk that a visitor reads the masthead as an official county property, even though the footer disclaims affiliation ([base template, lines 62–69](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L62-L69)).

W3C guidance also recommends continuity between a page title and the link/context that brought a user to the page ([WCAG 2.4.4 — Link Purpose](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html)). This is not a claim that the current title fails WCAG; it is a product-language and trust issue.

#### Remediation

1. Make the visible wordmark **Are They In Jail?** or **Are They In Jail? — Hamilton County**.
2. Put the source attribution on the secondary line: `Current Hamilton County custody roster · independent mirror by JCStream`.
3. Change the homepage title to `Are They In Jail? · Hamilton County custody roster` and preserve the current count as a secondary title suffix.
4. Move the booking-photo/Facebook seal out of the primary masthead into a source/provenance area. If retained, label it as an external social source rather than a civic seal.
5. Repeat “Independent public-record mirror — not a government site” beside the first search interaction, not only in the footer.

#### Acceptance criteria

- A first-time visitor can answer “what is this?”, “is it official?”, and “where do I search?” without scrolling.
- Browser title, visible wordmark, and shared-link preview use the same primary name.
- The independent status is adjacent to the first interaction and remains in the full legal/source area.

---

### UI-02 — The first viewport optimizes the roster but under-serves non-roster tasks

**Priority: P1 — task completion**

#### Evidence

The live homepage starts with roster search/filtering and then a long sequence of monthly booking results ([live homepage](https://www.aretheyinjail.com/)). In the template, the “Where to start” audience cards—“Someone you know was arrested,” “You have a case,” and “Researching the system”—are rendered **after** the legal disclosure and roster block ([homepage template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/index.html#L31-L110)). The help page shows that the audience includes people looking for a public defender, visitation, bond, case lookup, expungement, crisis assistance, and court-arrival information ([live Help & Self-Help](https://www.aretheyinjail.com/help/)).

#### Why it matters

Search-first is correct for one core audience, but the site itself serves at least three distinct jobs: find a person, navigate a case/custody process, and research the system. A family member who needs bond, visitation, or free legal help should not have to infer that those routes exist from a collapsed menu or traverse the roster. This is especially consequential on a phone, where the primary nav becomes a menu disclosure ([base template, lines 78–105](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L78-L105)).

#### Remediation

Keep the roster as the main product, but insert one compact route row immediately below search/freshness and above the first month:

- **Find someone** — Search the current roster.
- **Bond, visit, or contact** — Practical custody steps.
- **Court date or case** — Docket and courtroom routes.
- **Free help now** — Public defender, legal aid, crisis resources.

Use text links or small utility tiles, not four more large filled cards. Keep the longer audience cards lower on the homepage for users who want context.

#### Acceptance criteria

- On a 375px viewport, all four routes are visible or reachable without opening the global menu.
- Each route lands on a page whose heading matches the link text.
- The roster remains the first primary control; routing does not displace search.

---

### UI-03 — Dark-theme active text has measurable contrast regressions

**Priority: P1 — accessibility and visual legibility**

#### Evidence and calculation

The dark theme defines `--accent: #F0433A` and a later visual pass defines `--accent-quiet: color-mix(in oklch, #F0433A 73%, #141619)` ([dark tokens](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L119-L204), [latest override](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4551-L4580)). The same override applies `--accent-quiet` to small text in the active nav state, month counts, and the primary statistic on the court page ([style override, lines 4566–4574](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4566-L4574)).

Using the CSS Oklab/Oklch interpolation specified by that rule, the mixed color is approximately `#AF3B34`; against `#141619` it is approximately **3.0:1**. That is a decorative red, not a legible normal-text color. A second case is the current pager number: `#F0433A` text on the dark `--accent-bg` (`#2B1D19`) is approximately **4.31:1**, below the 4.5:1 normal-text threshold. The pager styles are here ([pager state](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4491-L4520)).

WCAG 2.2 SC 1.4.3 requires at least 4.5:1 for normal text, and explicitly includes placeholder, hover, and focus text ([W3C — Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)). Meaningful control boundaries and state indicators have a separate 3:1 non-text requirement ([W3C — Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)).

#### Remediation

- Use `--accent-quiet` only for non-text decoration: rules, borders, or a large graphical accent.
- Use `--fg` or a lightened accent for active navigation/count text. Do not rely on the color alone; retain weight, underline, or a border indicator.
- Change the selected pager state to `color: var(--fg)` with an accent border, or use a dark enough tinted background for the chosen text color.
- Add a small contrast test matrix for normal, hover, focus, selected, light, and dark states. The test should evaluate the actual token combinations, not just root variables.

#### Acceptance criteria

- All normal text states pass 4.5:1; large text passes 3:1.
- All non-text focus/state indicators pass 3:1 against adjacent colors.
- Visual hierarchy still distinguishes current nav, selected pager, and primary actions without a saturated red fill everywhere.

---

### UI-04 — The homepage ships a large roster DOM and paginates after JavaScript

**Priority: P1 — mobile load, perceived performance, and scanability**

#### Evidence

At the audit snapshot, the generated `docs/index.html` was **929,399 bytes** and contained **728** `.card-inmate` articles and **661** image elements. These figures are reproducible from the checked-in snapshot with:

```sh
wc -c docs/index.html
awk '/<article class="card-inmate"/{n++} END{print n}' docs/index.html
grep -o '<img ' docs/index.html | wc -l
```

The roster template loops through every `by_month` group and emits every card into the page ([roster template, lines 119–131](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L119-L131)). JavaScript pagination then hides cards and builds pager controls in the browser ([pagination implementation](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/main.js#L364-L520)). `loading="lazy"` and `content-visibility` reduce image/paint cost, but they do not eliminate the initial HTML transfer or the cost of constructing hundreds of nodes.

#### Why it matters

The visual result can look compact while the browser is still parsing a very large page. On mobile or a slow connection, this increases time to first useful interaction and makes assistive-technology navigation unnecessarily long. Client-side pagination is also a visual enhancement, not a server-side reduction.

#### Remediation

1. Render a bounded initial slice server-side—e.g. the current month and the first 24–48 cards.
2. Keep a real archive route for earlier months and preserve query/deep-link behavior.
3. If the desired interaction is instant filtering across all records, load a compact search index or JSON data source on demand rather than shipping all card markup.
4. Keep a complete no-JavaScript path: search/filter links can target the archive or server-generated query pages.
5. Measure compressed transfer, parse time, first input delay, and keyboard traversal length before and after.

#### Acceptance criteria

- The first homepage HTML is materially smaller than the current snapshot and contains only the first useful roster slice.
- Search remains usable with JavaScript enabled and the archive remains usable with JavaScript disabled.
- Deep links to an inmate/month/filter continue to land on the correct content.

---

### UI-05 — Navigation is too broad and too flat for a public-facing first visit

**Priority: P2 — information architecture**

#### Evidence

The shared navigation exposes seven “Roster tools,” eight “Court reference” links, and three “Site” links ([nav groups](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_nav_groups.html#L8-L55)). The footer repeats a large set of destinations ([base footer](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L128-L150)), while reference pages also render a “More court reference” block of up to seven cards ([reference block](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_more_reference.html#L7-L29)).

#### Why it matters

The links are individually reasonable, but the aggregate creates three competing navigation systems: the desktop rail, the mobile drawer, and the repeated card strip/footer. The first-time user must decide among “Calendar,” “Courts,” “Bond schedule,” “Visit and contact,” “Help and free aid,” “Services and programs,” “Stats,” “Data,” “Access,” and others before understanding the product’s primary route.

#### Remediation

Use a two-level information architecture:

**Primary:** Roster, Court dates, Bond/visit, Help, More.  
**More:** Courts, Judges, Jury duty, Rules, Forms, Services, Stats, Statutes, Data, Access, RSS, GitHub.

On reference pages, replace the full repeated card matrix with a compact “Related” list. Keep the footer as a complete index, but visually subordinate technical/project links.

This also gives the mobile drawer a meaningful first screen rather than a long list.

---

### UI-06 — The visual language is deliberate but over-signalled

**Priority: P2 — overall aesthetics and emotional tone**

#### Evidence

The site combines a centered uppercase mono wordmark and double-rule masthead ([masthead styles](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L306-L355)), rounded pill navigation ([in-page TOC](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3730-L3760)), multiple card radii and shadows ([cards](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3838-L3969)), a seven-category color legend ([roster legend](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L80-L90)), and filled red-to-amber felony badges ([severity badges](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L938-L1011)).

The live detail page simultaneously states “Arrest is not conviction” and “charges below are accusations only” ([live record example](https://www.aretheyinjail.com/inmate/2672540/)). The current red/amber severity palette is therefore a sensitive visual choice: it can help scanning, but it can also make accusation severity feel like a punitive or editorial judgment.

This is an aesthetic and trust observation, not a claim that the color coding is technically wrong. The code does provide text labels alongside color, which is the right direction.

#### Remediation

- Adopt one shape vocabulary: mostly rectangular 4–6px surfaces, with round pills reserved for truly stateful controls.
- Reduce the number of simultaneous signals. Keep the F1–MM text label and a thin category marker; avoid a saturated filled chip, a color strip, a colored charge label, and a legend all competing at once.
- Use red primarily for warnings, errors, and the active primary action. Use neutral/blue/ink treatments for ordinary degree/category metadata.
- Keep the warm severity scale available in the detail page or an optional “visualize severity” mode if it is important to the research audience.
- Make “presumed innocent” framing visually calm and close to the record, not visually outshouted by the severity palette.

#### Acceptance criteria

A visual review at light and dark themes should show one clear focal point per screen: search on the homepage, person/status on a record, and the requested information on reference pages.

---

### UI-07 — The 4px degree strip is a pointer-only control with weak discoverability

**Priority: P2 — control clarity and keyboard parity**

#### Evidence

The roster template renders a 4px `role="img"` tier strip whose segments are clickable in JavaScript ([roster markup](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L94-L105), [4px CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4311-L4319)). The JavaScript explicitly describes the segment behavior as “Pointer-only enhancement”; the accessible equivalent is the select ([tier-strip handler](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/main.js#L676-L688)). The explanatory caption is hidden by the final chrome stylesheet ([fold chrome](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/fold-chrome.css#L89-L106)).

#### Why it matters

A 4px bar reads as a chart, not a filter. A user must discover that its segments are interactive, and keyboard users cannot focus or activate the individual segments. WCAG 2.2 sets a 24×24 CSS-pixel minimum pointer target except for defined exceptions ([W3C — Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)). A visible control also needs a perceivable boundary/state, with 3:1 non-text contrast where applicable ([W3C — Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)).

#### Remediation options

**Preferred:** make the strip a non-interactive data visualization and let “Charge level” be the only filter control. Remove `cursor: pointer` and the click handler.

**If it must filter:** render each segment as a button/link with a name such as `Filter to F1 — 41 people`, at least a 24px target (ideally 44px), visible focus, and a text legend. Keep the select as a keyboard-friendly alternative, not as a hidden explanation for a visual control.

---

### UI-08 — Mobile in-page navigation hides overflow without a consistent cue

**Priority: P2 — responsive navigation**

#### Evidence

The live Help page exposes a long “On this page” rail with sections including Charged, In custody, Expungement, Civil, Specialty courts, Probation, Crisis, Appearing in court, and Guides from the courts ([live Help & Self-Help](https://www.aretheyinjail.com/help/)). The template contains the same set ([Help template, lines 71–81](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/help.html#L71-L81)). At widths under 720px, `.tab-toc` becomes one non-wrapping horizontal scroller ([responsive TOC CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3730-L3760)). The separate month rail has a right-edge fade, but the generic tab TOC does not ([month rail cue](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L518-L550)).

#### Remediation

Choose one of these patterns and use it consistently:

1. Wrap the section links to two rows on mobile when there are fewer than about six sections.
2. Show the first three high-use sections plus a visible `More sections` disclosure.
3. Keep the horizontal rail but add a fade/chevron and a short `Swipe for more` cue that disappears once the user scrolls.
4. Group the Help page into three task clusters—Custody, Case/legal help, Crisis/community—and use a short local index within each group.

W3C’s informative mobile guidance treats small-screen size as a distinct design constraint rather than assuming desktop content will remain discoverable unchanged ([W3C mobile accessibility guidance](https://www.w3.org/TR/mobile-accessibility-mapping/#small-screen-size)).

---

### UI-09 — Record pages need a next-step action cluster

**Priority: P2 — task completion after lookup**

#### Evidence

The live record page is information-rich: person/status summary, booking metadata, charge table, bond, court/case links, time in custody, bond distribution, severity ladder, statute context, and similar inmates ([live record example](https://www.aretheyinjail.com/inmate/2672540/)). The template places the person summary and long legal disclosure before the charges table ([record hero](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/inmate.html#L46-L104)), and the practical links are distributed throughout the page rather than collected as next steps.

#### Why it matters

Finding a person is usually not the end task. The next question is likely “How do I verify this?”, “How do I post bond?”, “How do I visit/contact them?”, “Where is the case/court date?”, or “How do I request a correction/removal?”. The current record is optimized for research depth; it is less optimized for a stressed family member who has already found the right name.

#### Remediation

Add a compact action row below the record name/status and above the metadata:

- **Verify at HCSO**
- **Bond and release**
- **Visit or contact**
- **Court record / case**
- **Free help**
- **Correction or removal**

Use one primary action (probably Verify) and quiet text links for the rest. Do not turn every action into a colored pill. Keep the legal disclosure collapsed or summarized with a `Read legal/data-use notice` control, while preserving the full text and no-JavaScript access.

#### Acceptance criteria

- The action row is visible without scrolling on a typical desktop record and near the top on mobile.
- Each action has descriptive link text and a destination-specific external-link indicator where needed.
- The action row never implies that a charge is a conviction or that the mirror is the official source.

---

### UI-10 — Judge cards repeat generic “Profile” controls

**Priority: P2 — scanability and assistive-technology orientation**

#### Evidence

The live Judges page lists 30 judges with search and court filters ([live Judges](https://www.aretheyinjail.com/judges/)). Each card may expose a repeated `Profile` disclosure, followed by a separate `Official profile` link ([judge template, lines 50–86](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/judges.html#L50-L86)). The first control has the same visible label for every judge; only the surrounding card heading supplies the context.

W3C says headings/labels should describe a control’s topic or purpose ([WCAG 2.4.6 — Headings and Labels](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html)), and link purpose should be understandable from the link/context ([WCAG 2.4.4 — Link Purpose](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html)).

#### Remediation

- Use `Profile for Jennifer L. Branch`, `Profile for Katie Casch`, etc. as accessible names while keeping a short visible label if desired.
- Prefer visible `Profile and courtroom procedures` when the disclosure contains both bio and procedure content.
- Keep `Official profile` as a distinct, explicitly external source action.
- Consider making the judge name the heading and adding a small `Copy courtroom contact` or `Call chambers` action only if user research supports it; do not add more controls merely to fill cards.

---

### UI-11 — Small legal/provenance text is doing too much work in-flow

**Priority: P2 — readability and trust**

#### Evidence

The footer contains four long legal/source paragraphs at `font-size: 11px`, while record-level legal text is `12px` ([legal styles](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L2466-L2473), [footer markup](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L143-L150)). The record also carries a long legal paragraph immediately after the personal metadata ([record legal copy](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/inmate.html#L89-L98)).

The copy is important and should not be deleted. The issue is hierarchy: small type, long line lengths, and dense legal references make both the useful warning and the policy text harder to scan. Web.dev recommends considering line length, font size, and line height together; it cites roughly 45–75 characters as a comfortable single-column range and recommends relative/ch-based constraints ([web.dev Typography](https://web.dev/learn/design/typography)).

#### Remediation

- Keep a short inline statement near the record: `Arrest is not conviction. Charges are accusations. This is an independent public-record mirror.`
- Put full FCRA, copyright, source-reuse, correction/removal, and public-record policy in a dedicated `Legal & data use` page or a clearly labeled disclosure.
- Use 13–14px for readable legal/supporting copy, `max-inline-size: 70ch` for prose, and clear subheadings within the full policy.
- Keep source freshness/provenance adjacent to the claim it qualifies, rather than relying on a distant footer.
- Keep the complete policy available without JavaScript and printable.

---

## What is already working well

These strengths should be preserved while remediating the hierarchy:

1. **The core task is obvious once the page is loaded:** the homepage exposes “Search the roster” and a real search input ([live homepage](https://www.aretheyinjail.com/)).
2. **The roster has useful progressive enhancement:** the template ships native `<details>`, labeled controls, and card content; JavaScript adds filtering, suggestions, sorting, and paging rather than being the only source of content ([roster template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L17-L131)).
3. **Keyboard and motion foundations are present:** the stylesheet includes `:focus-visible`, a skip link, and `prefers-reduced-motion` handling ([CSS foundations](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L262-L304)). W3C identifies visible focus as necessary for keyboard users ([W3C — Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)).
4. **The site does not hide its ethical/legal posture:** the live record says arrest is not conviction, charges are accusations, and the project is independent; the template also exposes source, FCRA, correction, and removal language ([live record](https://www.aretheyinjail.com/inmate/2672540/), [record template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/inmate.html#L70-L98)).
5. **Reference pages have useful freshness/provenance cues:** the live Judges page identifies the capture date and source corpus, while the Help page identifies when its resources were captured ([live Judges](https://www.aretheyinjail.com/judges/), [live Help](https://www.aretheyinjail.com/help/)).
6. **Touch sizing is often intentionally generous:** nav links, pager controls, and judge disclosure summaries use 44px minimum heights ([nav/pager CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L356-L371), [pager CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4491-L4520), [judge CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3953-L3967)).

## Recommended visual direction

### Positioning

**An editorial civic utility, not an incident dashboard.** The site can remain data-forward and serious without looking like a punishment/status console.

### Homepage hierarchy

1. Brand + independent/source line.
2. One plain-language promise: `Find a person in the current Hamilton County custody roster.`
3. Search input and freshness line.
4. Four compact task routes.
5. Roster browsing workspace.
6. Detailed context, methodology, and legal policy.

### Type

- Use a human-readable sans for headings/body and keep mono for IDs, ORC codes, timestamps, and case numbers.
- Avoid uppercase/letterspacing for anything users need to read as a sentence.
- Keep body text at 15–16px minimum; reserve 11–12px for true metadata.
- Constrain prose to roughly 60–75ch; let tables/data grids use the available width.

### Color

- Neutral page/surface system as the default.
- One accessible accent for focus/primary actions.
- Muted category markers; explicit text labels remain primary.
- Red reserved for warning, error, or a deliberately labeled severity signal—not generic navigation and counts.
- Test both light and dark themes from actual component states.

### Shape and motion

- Use 4–6px radii for cards and controls; reserve pills for status only.
- Prefer rules, spacing, and alignment to multiple nested containers.
- Keep the existing reduced-motion behavior and subtle hover transitions.
- Avoid adding entrance animations until first-input and focus behavior are measured.

## Remediation roadmap

### Phase 0 — high-leverage fixes

1. Fix UI-03 token/state contrast and add a contrast regression test.
2. Align visible brand, title, and source/independence language (UI-01).
3. Add the four-route task row above the roster (UI-02).
4. Rename judge disclosures (UI-10).
5. Move or relabel the masthead social seal so it cannot imply government affiliation.

### Phase 1 — task and performance structure

1. Replace client-only first-page pagination with server-bounded roster output (UI-04).
2. Simplify the primary navigation and consolidate reference links (UI-05).
3. Add record-page next-step actions (UI-09).
4. Make the mobile TOC behavior consistent (UI-08).

### Phase 2 — visual-system refinement

1. Reduce filled severity/category signals and unify radii (UI-06).
2. Decide whether the tier strip is visualization or control; implement one semantic model (UI-07).
3. Rework legal/provenance disclosure hierarchy and prose measure (UI-11).
4. Run usability sessions with at least three audience types: family/friend, person with a case, and researcher.

## Verification plan

Before calling the remediation complete, test:

- **Viewports:** 320, 375, 412, 768, 1024, and 1440px.
- **Themes:** light/dark, fresh/stale/blocked states, hover/focus/selected/disabled states.
- **Input:** keyboard-only, touch, screen reader spot checks, reduced motion, zoom/text resize.
- **Tasks:** find by name, filter by charge level, open a record, verify source, find bond/visit/help, find a judge, jump to a Help section.
- **Performance:** HTML transfer size, parse/DOM time, first useful search interaction, image requests, and keyboard focus count.
- **Accessibility checks:** text contrast at 4.5:1 for normal text, non-text/focus indicators at 3:1, target sizes, accessible names, status announcements, and no pointer-only critical action.
- **Content/trust:** official vs independent distinction, capture/freshness line, presumption of innocence, source link, correction/removal route, and no-fee message remain discoverable.

## Limitations

- The audit used the live text representation of the homepage, Judges, Help, and one representative record, plus source/CSS inspection at commit `5c7ac9b3c38c94d891722f3579741649fcb27e92`.
- No browser screenshot, Lighthouse run, assistive-technology session, or moderated user test was available in this audit pass. Responsive findings should therefore be verified in a real browser before implementation decisions are finalized.
- Roster contents, counts, capture dates, and upstream links are mutable public data. Live-page claims are point-in-time observations.

## Source index

### Live pages

- [L1 — Homepage](https://www.aretheyinjail.com/)
- [L2 — Judges](https://www.aretheyinjail.com/judges/)
- [L3 — Help & Self-Help](https://www.aretheyinjail.com/help/)
- [L4 — Representative record](https://www.aretheyinjail.com/inmate/2672540/)

### Standards and guidance

- [S1 — WCAG 2.2 SC 1.4.3 Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [S2 — WCAG 2.2 SC 1.4.11 Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- [S3 — WCAG 2.2 SC 2.5.8 Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [S4 — WCAG 2.2 SC 2.4.7 Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)
- [S5 — WCAG 2.2 SC 2.4.6 Headings and Labels](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html)
- [S6 — WCAG 2.2 SC 2.4.4 Link Purpose](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html)
- [S7 — WCAG 2.2 SC 4.1.3 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
- [S8 — web.dev Typography](https://web.dev/learn/design/typography)
- [S9 — W3C Mobile Accessibility Mapping](https://www.w3.org/TR/mobile-accessibility-mapping/)
