# UI & Aesthetic Audit — AreTheyInJail.com / JCStream

**Audit date:** 2026-09-22 (UTC)  
**Target:** [aretheyinjail.com](https://aretheyinjail.com/) — the published content resolved to the `www` hostname during review  
**Scope:** User-interface design, information architecture, visual language, responsive behavior, and accessibility-adjacent interaction risks. This is a remediation report, not a formal WCAG conformance certification.

## Executive summary

The product is substantially more capable than its first impression suggests. The live site provides a direct roster search, client-side filtering, judge/court reference pages, provenance dates, source links, correction/removal routes, and explicit presumption-of-innocence language. The implementation also has several good foundations: a skip link, native disclosure elements, visible focus rules, reduced-motion handling, accessible labels for the core search/filter controls, and progressive enhancement in the roster UI ([base template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L52-L124), [roster tool](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L17-L131), [motion/focus CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L262-L304)).

The main problem is hierarchy, not missing pages. The roster-first ordering is an intentional product decision and should remain intact. The highest-confidence fixes are the large initial roster DOM, the 4px chart/control ambiguity, the judge labels, the mobile Help TOC overflow, and a P1 contrast verification of dark-theme accent text. The masthead seal/affiliation treatment should be corrected without assuming that the publisher name needs to change. The severity scale and load-bearing legal copy are project rules and should be preserved while their surrounding presentation is refined.

### Overall assessment

| Dimension | Assessment | Why |
|---|---|---|
| Core utility | **Strong** | Search, filters, roster detail, court reference, and source links are present. |
| Task hierarchy | **Intentional, with focused refinements** | Roster-first is appropriate; the audit should not add a competing above-roster route row. |
| Trust/identity | **Clarify affiliation, not necessarily the name** | JCStream can remain the publisher; the masthead seal should not imply government affiliation. |
| Visual coherence | **Mixed** | The system is deliberate; surrounding shapes and decoration can be simplified without muting the project’s severity scale. |
| Accessibility foundation | **Good with targeted gaps** | Several strong primitives are present; dark accent text, the tier strip, and mobile TOC need focused work. |
| Perceived performance | **Needs remediation** | The homepage ships hundreds of roster cards in its initial HTML and only paginates after JavaScript runs. |

## Priority summary

| ID | Priority/status | Finding | Recommended outcome |
|---|---:|---|---|
| UI-01 | P2 / decision | Publisher identity and masthead affiliation need separation | Keep JCStream unless a deliberate naming decision is made; move/relabel the seal. |
| UI-02 | Accepted | Roster-first ordering is intentional | Do not pull Help/Bond above search or add a four-tile row above the months. |
| UI-03 | P1 / verify | Dark-theme accent text may fail contrast | Measure actual rendered selector pairs now; fix only confirmed failures. |
| UI-04 | P1 | Client-side pagination arrives after a large initial DOM | Server-render a small first slice; keep the full archive behind a deliberate route. |
| UI-05 | P2 / later | Navigation breadth is a later IA question | Do not cut links immediately; use task data before considering a five-link primary. |
| UI-06 | P2 | Surrounding visual language is over-signalled | Preserve the F1–F5 scale; refine chrome, spacing, and redundant signals around it. |
| UI-07 | P2 | The 4px severity strip is an ambiguous pointer-only control | Make it decorative; let the existing Charge level control own filtering. |
| UI-08 | P2 | Mobile in-page navigation hides overflow without a consistent cue | Wrap/group sections or add an explicit “more sections” affordance. |
| UI-09 | Deferred | A record-page action bar is not yet justified | Preserve current in-context links; test record tasks before adding new controls. |
| UI-10 | P2 | Judge cards repeat generic “Profile” controls | Give each disclosure a name-specific label and make the action purpose explicit. |
| UI-11 | P2 | Important legal/provenance copy needs presentation refinement | Keep presumed-innocent/FCRA content in-flow; improve size, measure, grouping, and scanability. |


## Findings and remediation details

### UI-01 — Publisher identity and masthead affiliation should be separated, not rebranded

**Priority: P2 — trust clarity and an explicit product decision**

#### Evidence

- The live homepage title is `JCStream · 1210 currently in custody`, while the public address is `aretheyinjail.com`; the live page’s primary heading is “Search the roster” ([live homepage](https://www.aretheyinjail.com/)).
- The masthead visibly brands the site **JCStream** and describes it as “Hamilton County · Justice Center mirror” ([base template, lines 56–60](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L56-L60)).
- The footer correctly says the project is independent and not affiliated with the Sheriff’s Office or a government entity ([base template, lines 145–150](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L145-L150)).
- The masthead also presents a seal/link labeled “Hamilton County Booking Photos on Facebook” ([base template, lines 62–69](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L62-L69)).

#### Revised assessment

The domain asks a natural-language question and **JCStream can validly remain the publisher name**. Changing the wordmark to “Are They In Jail?” would be a public identity/trust decision, not an implementation fix, and is out of scope unless the product owner chooses it. The more immediate issue is that an external booking-photo seal in the primary masthead can visually imply official affiliation before the footer disclaimer is encountered.

#### Remediation

1. Keep the JCStream wordmark unless a separate naming exercise deliberately changes it.
2. Move the booking-photo/Facebook seal out of the primary masthead into the source/provenance area.
3. If retained, label it plainly as an external social/source link rather than a civic seal.
4. Put a concise adjacent attribution near the first search interaction: `JCStream — independent public-record mirror; not a government site.`
5. Optionally use a descriptive title such as `JCStream · Hamilton County custody roster` without changing the visible product name.
6. Validate the result with a short comprehension test: users should distinguish the domain question, the JCStream publisher, and the official/non-official source relationship.

#### Acceptance criteria

- JCStream remains visibly identifiable unless a deliberate product-name decision says otherwise.
- The masthead cannot reasonably be mistaken for a government seal or official county site.
- The independent status is adjacent to the first search interaction and remains in the full legal/source area.

This finding does **not** recommend a rebrand. It recommends separating publisher identity, domain intent, and source affiliation clearly.


### UI-02 — Roster-first hierarchy is an accepted product decision

**Status: Accepted — no remediation requested**

The live homepage starts with roster search/filtering and monthly booking results ([live homepage](https://www.aretheyinjail.com/)). The template places the “Where to start” audience cards after the legal disclosure and roster block ([homepage template](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/index.html#L31-L110)). That ordering is intentional: the roster is the primary product, and the audience cards are supporting context.

The previous recommendation to add a four-route row above the months is withdrawn. Do **not** pull Help, Bond, or other audience routes above search, and do not add a competing tile row to the first roster workspace. Preserve the current roster-first hierarchy. If future analytics or user testing shows that a secondary audience cannot find its route, solve that below the roster, in the existing navigation, or through a small contextual link—not by displacing the primary search task.


### UI-03 — Dark-theme accent text requires P1 contrast verification

**Priority: P1 — verify before treating the state as acceptable**

#### Evidence and candidate calculation

The dark theme defines `--accent: #F0433A` and a later visual pass defines `--accent-quiet: color-mix(in oklch, #F0433A 73%, #141619)` ([dark tokens](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L119-L204), [latest override](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4551-L4580)). The same override applies `--accent-quiet` to small text in the active nav state, month counts, and the primary statistic on the court page ([style override, lines 4566–4574](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4566-L4574)).

Using the CSS Oklab/Oklch interpolation specified by that rule, the mixed color is approximately `#AF3B34`; against `#141619` it is approximately **3.0:1**. A second candidate is the current pager number: `#F0433A` text on the dark `--accent-bg` (`#2B1D19`) is approximately **4.31:1**, below the 4.5:1 normal-text threshold. The pager styles are here ([pager state](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4491-L4520)).

These are strong candidates for a real failure, but this audit did not have a browser’s computed-style/accessibility engine. Treat this as a **P1 verification item now**, not as a reason to redesign the accent system before measuring the actual rendered selectors.

WCAG 2.2 SC 1.4.3 requires at least 4.5:1 for normal text, and includes placeholder, hover, and focus text ([W3C — Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)). Meaningful control boundaries and state indicators have a separate 3:1 non-text requirement ([W3C — Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)).

#### Remediation

1. Inventory every dark-theme selector that uses `--accent`, `--accent-quiet`, or `--accent-bg` for text.
2. Measure the actual computed foreground/background pairs in normal, current, hover, focus, and selected states with a browser or contrast test.
3. If a pair fails, make the smallest local correction—text color, background, or a text/border treatment—while preserving the project’s accent and severity language.
4. Do not remove or redesign the scale/token globally until the selector-level results justify it.
5. Add the measured state matrix to automated regression checks.

#### Acceptance criteria

- Every actual normal-text combination passes 4.5:1; large text passes 3:1.
- Non-text focus/state indicators pass 3:1 against adjacent colors.
- The audit records the measured rendered values and selectors, not just root-token estimates.


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

### UI-05 — Navigation breadth is a later IA question, not an immediate cut

**Priority: P2 — defer structural changes until task/link data exists**

#### Evidence

The shared navigation exposes seven “Roster tools,” eight “Court reference” links, and three “Site” links ([nav groups](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_nav_groups.html#L8-L55)). The footer repeats a large set of destinations ([base footer](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L128-L150)), while reference pages also render a “More court reference” block of up to seven cards ([reference block](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_more_reference.html#L7-L29)).

#### Revised assessment

The link set is broad, but breadth alone is not enough evidence to remove destinations. A five-link primary nav with a More area may be a good later direction, but it should follow usage data and task testing—not be bundled with the roster-first decision or implemented as an immediate cut.

#### Remediation when this work is scheduled

- Instrument navigation use or review existing analytics/search queries.
- Identify the five highest-value user tasks and the links that support them.
- Prototype a five-link primary plus More only after confirming that secondary/reference destinations remain discoverable.
- Keep the footer as a complete index during the transition.

For now, preserve the current navigation and focus on the higher-confidence issues: contrast verification, DOM weight, the decorative tier strip, named judge controls, and mobile TOC overflow.


### UI-06 — Refine the surrounding visual language without muting the project severity scale

**Priority: P2 — visual polish within an intentional project rule**

#### Evidence

The site combines a centered uppercase mono wordmark and double-rule masthead ([masthead styles](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L306-L355)), rounded pill navigation ([in-page TOC](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3730-L3760)), multiple card radii and shadows ([cards](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L3838-L3969)), a seven-category color legend ([roster legend](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L80-L90)), and filled red-to-amber felony badges ([severity badges](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L938-L1011)).

The live detail page simultaneously states “Arrest is not conviction” and “charges below are accusations only” ([live record example](https://www.aretheyinjail.com/inmate/2672540/)). The severity scale is a project rule and should remain visible; this finding is about the amount of competing chrome around it, not about draining the F1–F5 scale into an optional visualization mode.

#### Remediation

- Preserve the F1–F5 severity scale, its meaning, and redundant text labels.
- Reduce competing decoration around that scale: align radii, spacing, border weights, and legends so the severity signal is intentional rather than one of many simultaneous accents.
- Keep color plus text/pattern/state so the scale is not color-only; verify the actual color pairs under UI-03.
- Use neutral treatments for unrelated metadata, while retaining the defined red/amber treatment where the project rule calls for it.
- Validate the tone with stakeholders and representative users rather than unilaterally neutralizing a meaningful research signal.

#### Acceptance criteria

F1–F5 remains visible and recognizable in the roster/detail experience. The refinement reduces visual noise around the scale without changing its semantics, colors, or availability.


### UI-07 — Make the 4px degree strip decorative; let Charge level filter

**Priority: P2 — control clarity and keyboard parity**

#### Evidence

The roster template renders a 4px `role="img"` tier strip whose segments are clickable in JavaScript ([roster markup](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/_roster_tool.html#L94-L105), [4px CSS](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L4311-L4319)). The JavaScript describes the segment behavior as “Pointer-only enhancement”; the accessible equivalent is the existing select ([tier-strip handler](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/main.js#L676-L688)). The explanatory caption is hidden by the final chrome stylesheet ([fold chrome](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/fold-chrome.css#L89-L106)).

#### Revised assessment

The strip is a chart pretending to be a control. Charge level already provides the filter, so the strip does not need a second interaction model. A 4px bar should communicate distribution only; it should not require users to discover pointer behavior or force keyboard users to rely on a different control.

#### Remediation

- Remove the click handler, pointer cursor, and interactive affordance from the strip.
- Keep it as a decorative/data visualization with an accurate accessible description if it conveys a meaningful distribution; otherwise mark it decorative.
- Keep the existing labeled Charge level select as the single filter control.
- Restore a short visible caption/legend if the chart is not self-explanatory; the caption should explain the relationship to the Charge level select, not invite clicking.

This is the preferred resolution; do not replace the strip with another set of tiny buttons.


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

### UI-09 — Record-page next-step actions are deferred pending task evidence

**Status: Deferred — do not add a six-action bar by default**

#### Evidence

The live record page is information-rich: person/status summary, booking metadata, charge table, bond, court/case links, time in custody, bond distribution, severity ladder, statute context, and similar inmates ([live record example](https://www.aretheyinjail.com/inmate/2672540/)). The template places the person summary and legal disclosure before the charges table ([record hero](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/inmate.html#L46-L104)).

The audit observed that practical links are distributed through the record, but did not measure a failure to find them. Adding six prominent actions—Verify, Bond, Visit, Court, Help, and Correction—could create a second dashboard and compete with the record itself.

#### Decision and future test

- Preserve the current record hierarchy and in-context links.
- Keep the presumed-innocent and data-use language near the record; do not trade it for action chrome.
- Test concrete tasks with family/friend, case, and research users before adding controls.
- If one next step is consistently missed, add that one contextual link at the point of need rather than a permanent six-action bar.

This item is retained as a future research question, not as a current must-fix or a recommendation to pull Help/Bond above the homepage search.


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

### UI-11 — Legal/provenance copy needs presentation refinement, not demotion

**Priority: P2 — readability and trust**

#### Evidence

The footer contains four long legal/source paragraphs at `font-size: 11px`, while record-level legal text is `12px` ([legal styles](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/static/style.css#L2466-L2473), [footer markup](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/base.html#L143-L150)). The record also carries a long legal paragraph immediately after the personal metadata ([record legal copy](https://github.com/AICincy/HCJC/blob/5c7ac9b3c38c94d891722f3579741649fcb27e92/web/templates/inmate.html#L89-L98)).

#### Revised assessment

The presumed-innocent and FCRA sentences are load-bearing and must remain in-flow on the record page. They should not be demoted behind a generic disclosure or removed in favor of a six-action row. The issue is presentation: small type, long lines, and dense legal references make important warnings harder to scan.

#### Remediation

- Keep the current `Arrest is not conviction`, accusation, independent-mirror, and FCRA language adjacent to the record.
- Give that block a clear heading such as `Important legal and data-use information`, stronger spacing, and readable 13–14px text where feasible.
- Constrain prose to roughly 60–75ch, while allowing structured metadata/tables to use the available width.
- Separate auxiliary policy detail with subheadings and links, but do not hide the load-bearing sentences behind JavaScript or move them only to the footer.
- Keep the complete policy available without JavaScript and printable; a dedicated policy page can supplement the record, not replace its essential warning.
- Preserve source freshness/provenance adjacent to the claim it qualifies.

#### Acceptance criteria

- A record visitor sees the presumed-innocent and FCRA framing without opening a disclosure or visiting another page.
- The essential legal block is readable at desktop, mobile, zoom, and print widths.
- Full policy remains available, while the record page retains the minimum context needed to prevent misuse.


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

1. JCStream brand + independent/source line.
2. One plain-language promise: `Find a person in the current Hamilton County custody roster.`
3. Search input and freshness line.
4. Roster browsing workspace.
5. Existing audience/context content below the roster.
6. Detailed methodology and legal policy.

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

### Phase 0 — high-confidence fixes

1. Measure the actual dark-theme text/state combinations and correct confirmed contrast failures (UI-03).
2. Reduce initial roster HTML/DOM weight without changing the roster-first order (UI-04).
3. Make the 4px tier strip decorative and leave Charge level as the filter (UI-07).
4. Give judge disclosures name-specific labels (UI-10).
5. Move/relabel the masthead booking-photo seal to clarify affiliation (UI-01).
6. Add a mobile overflow cue or grouped pattern to the Help TOC (UI-08).

### Phase 1 — evidence-led structure

1. Review navigation usage and task data before considering a five-link primary plus More (UI-05).
2. Test record-page tasks before adding any next-step controls (UI-09).
3. Keep the existing roster-first homepage order; do not add an above-roster Help/Bond route row (UI-02).

### Phase 2 — visual and content refinement

1. Refine surrounding radii, spacing, borders, and legends without altering the F1–F5 project severity scale (UI-06).
2. Improve legal/provenance typography and grouping while keeping load-bearing copy in-flow on records (UI-11).
3. Run usability sessions with at least three audience types: family/friend, person with a case, and researcher.


## Verification plan

Before calling the remediation complete, test:

**Product decisions to preserve during remediation:** roster-first homepage order; JCStream as publisher unless separately renamed; the F1–F5 severity scale; and presumed-innocent/FCRA language in-flow on record pages.

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
