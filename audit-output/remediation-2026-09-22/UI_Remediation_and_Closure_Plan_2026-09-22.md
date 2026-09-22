# UI Remediation and Closure Plan

**Date:** 2026-09-22
**Scope:** Both September 22 UI audit reports, excluding accepted decisions and deferred research items.
**Implementation state:** Remediation and automated regression checks are complete in the working branch.
**Release state:** No deployment, push, or merge has been performed.

**Execution update, 2026-09-22:** [Closure execution record](closure/README.md). Fresh local checks passed; a combined sort/page deep-link regression was fixed and retested. Build/source manifests identify the exact tested working tree. Manual and physical-device gates remain NOT RUN. Local lab measurements expose a cold-search performance tradeoff; Gate C remains open. Production TLS probes still fail. The original measurements below are retained as historical evidence; the execution record contains the fresh results.

---

## 1. Objective

Bring the September 22 UI audit findings to a release-ready state by:

1. Preserving the completed implementation and automated regression evidence.
2. Completing the remaining manual accessibility and physical-device validation.
3. Verifying the generated `docs/` artifacts and source changes are internally consistent.
4. Separating local-build verification from production verification.
5. Recording explicit closure evidence for each finding before merge or deployment.

This plan does **not** reopen findings that were explicitly accepted or deferred, unless new evidence demonstrates that the documented decision no longer applies.

---

## 2. Current implementation status

The working branch already contains the remediation described in the September 22 UI findings report.

### Automated verification completed

| Check | Result |
| :-- | :-- |
| Python suite | **724 passed**, including 17 new UI regression cases |
| axe-core | **Zero violations in 72 scans** across 12 page types at 1440/390/320px in both themes |
| Layout verification | Home, bond, and record pages checked at 320/375/390/412/768/1024/1440px in both themes |
| Search | Record outside the initial 48 found through suggestions and Enter submission |
| Deep links | Tier, sort, and page links work; page 2 survives reload |
| Keyboard | Filters disclosure, tier selection, tooltip focus, and Escape behavior pass |
| No-JavaScript | Full archive exposes all 1,202 current records; browser Find guidance remains visible |
| Mobile tables | Label/value relationships fit their containers; long identifiers wrap at 320px |
| Source data integrity | No canonical files under `data/` changed |
| Patch hygiene | `git diff --check` passed |

### Performance improvement verified locally

The homepage initial payload was substantially reduced while keeping the full roster available through `/archive/`.

| Metric | Before | After | Change |
| :-- | --: | --: | --: |
| Server-rendered cards | 717 | 48 | -669 |
| HTML bytes | 974,541 | 82,066 | ~92% smaller |
| Gzip bytes | 108,714 | 14,332 | ~87% smaller |
| Initial DOM elements | 7,924 | 824 | ~90% smaller |

These figures are local compressed HTML measurements, not production transfer measurements.

---

## 3. Finding-level remediation record

### P0-01 / UI-03 — Contrast

**Implementation completed**

- Dark small-text and icon contrast issues corrected.
- Primary-card white ink retained.
- Category text lightened.
- Existing neutral selected-state corrections retained.
- Semantic color-pair regression checks added.
- Severity fills were intentionally left unchanged.

**Closure evidence**

- Automated contrast verification is covered by the axe scans and semantic color-pair tests.
- Visual verification was performed at the documented viewport/theme matrix.

**Remaining validation**

- Manual screen-reader checks remain separate from contrast closure.
- Confirm final rendered screenshots used for release evidence correspond to the rebuilt artifacts.

**Exit criteria**

- Automated contrast checks remain clean.
- No unintended severity-color regression is introduced.

---

### P0-02 — Prose links

**Implementation completed**

Permanent underlines were extended to:

- field values,
- table cells,
- contributed-case prose,
- footer source links.

Structured controls and dashed-rule links retain explicit exceptions.

**Exit criteria**

- Links remain visually identifiable without relying only on color.
- Exceptions are limited to the intended control/link patterns.
- Regression screenshots and automated assertions remain clean.

---

### P1-03 / UI-07 — Degree strip

**Implementation completed**

- Existing click handler remains removed.
- Remaining source-pointer affordance removed.
- Visible informational caption restored, pointing users to Charge level.

**Exit criteria**

- Degree strip is informational rather than misleadingly actionable.
- Caption remains visible and understandable across tested themes/viewports.
- No stale interaction handler or cursor treatment remains.

---

### P2-04 — Legend

**Implementation completed**

- Text legend exposed to assistive technology.
- Full degree/count description preserved.

**Exit criteria**

- Accessibility tree includes the legend content.
- Full descriptive text remains associated with the visualization.

---

### P1-05 — Mobile tables

**Implementation completed**

- Charge and bond tables support opt-in stacked mobile presentation.
- Labels are displayed beside values.
- Native table headers remain represented in the accessibility tree.
- Explicit roles preserve table semantics.
- Other tables continue to use horizontal scrolling.

**Exit criteria**

- Label/value relationships remain clear at 320px.
- Identifiers wrap without container overflow.
- Accessibility semantics remain intact after responsive transformation.

---

### P1-07 — Search sizing

**Implementation completed**

- Higher-specificity CSS rules that defeated the prior 16px override were corrected.
- Search and filter selects now meet the measured minimum.

**Exit criteria**

- Computed control text size remains at or above the intended minimum.
- No higher-specificity rule reintroduces the previous regression.

---

### P1-08 — Tier targets

**Implementation completed**

- Real 28px-high buttons replace reliance on overlapping invisible hit areas.
- Existing tooltip association, focus ring, and Escape behavior retained.

**Exit criteria**

- Interactive targets meet the intended minimum geometry.
- Keyboard and tooltip behavior continue to pass.
- No interaction depends on invisible overlapping regions.

---

### P2-09 / UI-11 — Readability

**Implementation completed**

- Semantic charge/metadata/legal size tokens added.
- Charge text set to 14px.
- Roster metadata set to 12px.
- Legal text set to 13px with heading, 1.6 line-height, and 75ch measure.
- Narrow record column corrected so legal copy uses available width.
- No legal sentences were removed or hidden.

**Exit criteria**

- Text remains readable at the tested responsive widths.
- Legal notice remains visible and in-flow.
- No content has been hidden solely to satisfy layout constraints.

---

### P2-11 — Font assets

**Implementation completed**

- Seven unreferenced font files removed from source and published assets.
- Public Sans and IBM Plex Mono roles and fallbacks documented.

**Exit criteria**

- Build references only the intended font assets.
- No broken font references remain.
- Published assets no longer contain the removed unreferenced files.

---

### UI-01 — Affiliation

**Implementation completed**

- Hidden masthead seal markup removed.
- External social destination retained as a plainly labeled footer text link.
- Independent/non-government status placed beside search.
- JCStream remains the publisher.

**Exit criteria**

- No visual or semantic element implies an official-government affiliation that is not intended.
- Publisher identity remains accurate and explicit.
- Footer destination remains understandable without relying on hidden or decorative branding.

---

### UI-04 — Initial DOM

**Implementation completed**

- Homepage bounded to 48 cards.
- Full-roster suggestions use a lazy search index containing all charge descriptions and ORC codes.
- Search, filters, and deep links reach the complete current roster through `/archive/`.

**Performance result**

- Initial HTML reduced from 974,541 to 82,066 bytes locally.
- Initial server-rendered cards reduced from 717 to 48.
- Initial DOM reduced from 7,924 to 824 elements.

**Exit criteria**

- Homepage preview remains bounded.
- Search and archive remain complete.
- No result is inaccessible solely because it is outside the initial 48-card preview.
- Full-roster search works with JavaScript enabled and no-JavaScript guidance remains accurate.

---

### UI-06 — Visual polish

**Implementation completed**

- Reference-card radii aligned with the shared card token.
- Competing text neutralized where appropriate.
- F1 through F5 severity fills intentionally unchanged.

**Exit criteria**

- Shared component tokens remain consistent.
- Severity semantics are visually preserved.

---

### UI-08 — Local navigation

**Implementation completed**

- Permanent fade replaced with wrapping local links.
- Final Help destination included.
- Narrow court-directory label/value overflow also corrected during verification.

**Exit criteria**

- Local navigation remains usable at narrow widths.
- No destination is visually clipped or hidden by the navigation treatment.
- Help remains reachable without depending on a hover-only mechanism.

---

### UI-10 — Judge labels

**Implementation completed**

- Existing name-specific profile disclosures and official links preserved.
- Judge name added to the optional standing-orders disclosure.

**Exit criteria**

- Names and associated disclosures remain correctly paired.
- Official links are clearly attributable to the relevant judge/profile.

---

### O-01 / O-02 / UI-02 / UI-05 / UI-09 — Preserved decisions

The following were intentionally preserved:

- compact homepage heading,
- desktop navigation wrap,
- roster-first ordering,
- existing navigation destinations,
- no unrequested record action bar,
- no rebrand.

These are documented decisions rather than pending remediation items.

---

## 4. Remaining validation gates

The main outstanding work is **manual and production-oriented validation**, not another implementation pass.

### Gate A — Screen-reader validation

**Status:** Not run.

Required manual sessions:

- NVDA,
- JAWS,
- VoiceOver.

Validate at minimum:

1. Heading hierarchy and landmark navigation.
2. Search and filter control labels.
3. Degree strip and text legend semantics.
4. Table headers and responsive table semantics.
5. Tier controls and tooltip/focus behavior.
6. Disclosure controls and Escape handling.
7. Archive/search result discovery.
8. Judge labels and supporting links.
9. Presumption-of-innocence/legal notice visibility and reading order.

**Exit criteria**

Each session records pass/fail observations and any follow-up issue. Automated axe results must not be presented as a substitute for manual screen-reader conformance testing.

---

### Gate B — Physical mobile validation

**Status:** Not run.

Validate on representative physical devices:

- iPhone with zoom/control scaling behavior,
- Android device for parsing and input latency,
- touch interaction at narrow widths.

Check:

- text/control zoom,
- tap target acquisition,
- filter disclosure interaction,
- tier selection,
- table scrolling/stacking,
- long identifiers,
- search entry and submission,
- page/deep-link reload behavior,
- orientation/viewport resizing.

**Exit criteria**

No blocking interaction or layout regression is observed on representative physical devices.

---

### Gate C — Production-style performance validation

**Status:** Not measured in the live environment.

Local measurements establish the direction and magnitude of the HTML reduction, but they are not production network-transfer measurements.

Measure after deployment or in an equivalent production-like environment:

- compressed HTML transfer size,
- time to first byte,
- first contentful paint,
- largest contentful paint,
- input latency for search/filter interactions,
- archive/search-index load behavior,
- mobile network behavior.

**Exit criteria**

Production measurements do not reveal a material regression relative to the prior baseline and the homepage payload reduction remains effective.

---

### Gate D — Production verification

**Status:** Not run.

The sandbox could not establish the required HTTPS connections to the live environment. Therefore, the current evidence is for the rebuilt local output only.

After deployment, verify:

1. Home page loads successfully over HTTPS.
2. Archive contains the complete current roster.
3. Search discovers records beyond the initial 48.
4. Filters and tier links work on desktop and mobile.
5. Page/deep links survive reload.
6. No-JavaScript archive behavior remains accurate.
7. CSP behavior is unchanged in production.
8. Generated assets are served correctly.
9. Footer, Help, legal, and external links resolve correctly.
10. No production-only CSS/JS/font path issue appears.

**Exit criteria**

Production smoke tests pass and the evidence is captured using the exact deployed commit/build identifier.

---

### Gate E — Build/feed validation

**Status:** Local gate passed on 2026-09-22. Fresh HEAD and remediation builds both succeeded with the same four missing optional Firecrawl feeds (two WARNING and two caught ERROR logs). No canonical data changed. Full public-data manifest and local HTTP byte parity passed. See the [execution record](closure/README.md) for artifact exclusions, hashes, and the unchanged baseline empty clerk fallback, which was not added to Git. Final reviewed-commit deployment build remains outstanding.

Rules:

- Do not invent feed content.
- Do not add new empty data artifacts merely to suppress warnings.
- Confirm generated outputs are derived from the same canonical source snapshot.
- Record whether optional feed warnings are expected and unchanged.

**Exit criteria**

The build succeeds using the intended data inputs and no new feed-related artifact or data integrity regression is introduced.

---

## 5. Evidence package

Maintain the following artifacts together for final review:

| Artifact | Purpose |
| :-- | :-- |
| `report.json` | Browser assertions, axe results, font sizes, target bounds, table measurements |
| `performance.json` | Reproducible local HTML, gzip, and DOM measurements |
| `home-1440-dark.png` | Final desktop rendering |
| `home-390-dark.png` | Final mobile rendering |
| `home-320-light.png` | Narrow light-theme rendering |
| `schedule-390-dark.png` | Mobile bond rows |
| `charges-320-light.png` | Narrow charge rows |
| `record-320-light.png` | Narrow record and legal-notice rendering |
| `design/ui-remediation.md` | Reproduction and design contracts |
| `scripts/check_ui_remediation.cjs` | Browser regression runner |
| `tests/test_ui_remediation.py` | Python UI regression tests |
| `manual-qa-checklist.md` | Required manual validation record |

For every manual or production check, record:

- date/time,
- environment/device/browser,
- exact build/commit,
- test performed,
- result,
- screenshot or log when relevant,
- issue identifier if failed.

---

## 6. Release checklist

### Before merge

- [x] Working-branch implementation reviewed against the September 22 findings.
- [x] `724 passed` Python suite remains green. Local Python 3.11.2; CI 3.13/3.14 still unverified.
- [x] 72 axe scans remain at zero violations.
- [x] `git diff --check` remains clean.
- [x] Generated `docs/` artifacts match the source build. All common paths match; workflow-generated public-data mirrors remain build-only and the preserved review document is nongenerated.
- [x] No canonical files under `data/` changed unintentionally.
- [x] Manual screen-reader validation completed or explicitly tracked as release risk. **Risk tracked as MANUAL-A; testing NOT RUN, not waived.**
- [x] Manual physical-device validation completed or explicitly tracked as release risk. **Risk tracked as DEVICE-B; testing NOT RUN, not waived.**
- [ ] Evidence package is complete. Local package complete; required manual/device/production evidence remains missing.
- [x] Accepted and deferred findings remain excluded from remediation scope.

### Before deployment

- [ ] Final build generated from the reviewed commit. Tested working tree identified by source/build manifests; no final commit or deployment exists.
- [ ] Published HTML/CSS/JS/font assets verified. Local generated paths verified; published delivery unverified.
- [x] Search index contains the intended full roster. All 1,202 IDs equal canonical data and archive IDs.
- [ ] Production-like performance checks recorded. Local gzip/CDP lab recorded, but not equivalent production infrastructure; PERF-01 remains open.
- [ ] Deployment artifact hashes/build identifiers captured. Local candidate hashes captured; final deployment artifact not produced.

### After deployment

- [ ] HTTPS production smoke test passes.
- [ ] Home/archive/search/deep-link checks pass.
- [ ] Mobile layout checks pass.
- [ ] No production-only CSP, asset, or font regression observed.
- [ ] Production performance measurements captured.
- [ ] Final audit report updated with the deployed commit/build.
- [ ] Remediation marked closed only after evidence is attached.

---

## 7. Risk and decision notes

### CSP

The production CSP is unchanged.

The browser test uses normal CSP for interaction checks. CSP bypass is used only for isolated axe injection contexts and must not be interpreted as a production CSP change.

### No-JavaScript path

The no-JavaScript archive behavior is an intentional accessibility/resilience path, not a temporary fallback. It should remain part of final regression verification.

### Homepage payload tradeoff

The implementation intentionally trades preview-local filtering of hundreds of hidden cards for:

- a bounded initial homepage,
- a complete `/archive/`,
- a lazy full-roster search index,
- explicit deep-link/search access to records outside the initial 48.

This tradeoff should remain documented so future changes do not silently restore the previous large initial DOM.

### Source-data integrity

No canonical `data/` files were changed. Any future UI remediation must preserve that boundary unless the task explicitly includes source-data corrections.

---

## 8. Final closure criteria

The UI remediation should be considered **implementation-complete** based on the current working-branch evidence, but **not fully release-closed** until the remaining validation gates are addressed.

Final closure requires:

1. Automated regression remains green.
2. Required manual accessibility checks are recorded.
3. Representative physical-device checks are recorded.
4. Deployment/production verification is completed after release.
5. Production performance is measured rather than inferred from local sizes.
6. The final report links the evidence to the exact reviewed/deployed build.
7. No additional blocking regression is discovered.

**Current state:** implementation and automated verification complete; manual accessibility, physical-device, production performance, and live-production validation remain outstanding.

**Deployment state:** no deployment, push, or merge has been performed.
