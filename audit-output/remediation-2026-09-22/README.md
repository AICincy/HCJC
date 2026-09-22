# UI findings remediation

Date: 2026-09-22. Scope: both September 22 audit reports, excluding accepted decisions and deferred research items.

Implementation and regression checks are complete in the working branch. Generated HTML, CSS, JavaScript and search-index artifacts in `docs/` are updated. No deployment, push or merge was performed.

Release gates and finding-level exit criteria: [UI Remediation and Closure Plan](UI_Remediation_and_Closure_Plan_2026-09-22.md).

**Latest execution:** [Closure execution record](closure/README.md). Fresh 724-test and 72-scan runs passed. A combined sort/page deep-link regression was fixed. Exact working-tree/build hashes, final screenshots, artifact/data verification, and new local lab measurements are attached. Cold search suggestions are slower with the complete all-charge index; performance validation remains open. Manual, physical-device, CI-version-matrix, and production gates are not complete. The original evidence below remains preserved.

## Verification

| Check | Result |
| :-- | :-- |
| Python suite | **724 passed**, including 17 new UI regression cases |
| axe-core | **Zero violations in 72 scans**: 12 page types, 1440/390/320px, both themes |
| Layout | Home, bond and record pages checked at 320, 375, 390, 412, 768, 1024 and 1440px in both themes |
| Search | Found a record outside the initial 48 via suggestions and Enter submission |
| Deep links | Tier, sort and page links worked; page 2 survived reload |
| Keyboard | Filters disclosure, tier selection, tooltip focus and Escape passed |
| No JavaScript | Full archive exposes all 1,202 current records; browser Find guidance remains visible |
| Mobile tables | Label/value pairs fit their containers; long identifiers wrap at 320px |
| Source data | No canonical files under `data/` changed |
| Patch hygiene | `git diff --check` passed |

The browser test uses normal CSP for interaction checks. Only axe injection uses CSP bypass in isolated test contexts. The production CSP is unchanged.

## Finding disposition

| Finding | Remediation |
| :-- | :-- |
| P0-01 / UI-03: contrast | Completed dark small-text/icon fixes, kept primary-card white ink, lightened category text, and retained existing neutral selected-state corrections. Added semantic color-pair regression checks. Severity fills remain unchanged. |
| P0-02: prose links | Extended permanent underlines to field values, table cells, contributed-case prose and footer source links. Structured controls and dashed-rule links retain explicit exceptions. |
| P1-03 / UI-07: degree strip | Kept the already-removed click handler removed. Removed the remaining source pointer affordance. Restored a visible informational caption pointing to Charge level. |
| P2-04: legend | Exposed the text legend to assistive technology. Preserved the strip's full degree/count description. |
| P1-05: mobile tables | Opt-in stacked charge and bond tables show labels beside values. Native headers remain in the accessibility tree. Explicit roles preserve table semantics. Other tables retain horizontal scrolling. |
| P1-07: search sizing | Corrected higher-specificity rules that defeated the existing 16px override. Search and filter selects now meet the measured minimum. |
| P1-08: tier targets | Real 28px-high buttons replace reliance on overlapping invisible hit areas. Existing tooltip association, focus ring and Escape behavior remain. |
| P2-09 / UI-11: readability | Semantic charge/metadata/legal size tokens; 14px charge text; 12px roster metadata; 13px legal text with a heading, 1.6 leading and 75ch measure. Fixed the narrow record column so legal copy uses the available width. No legal sentences were removed or hidden. |
| P2-11: font assets | Removed seven unreferenced font files from source and published assets. Documented Public Sans and IBM Plex Mono roles and fallbacks. |
| UI-01: affiliation | Removed the hidden masthead seal markup. Retained the external social destination as a plainly labeled footer text link. Added independent/non-government status beside search. JCStream remains the publisher. |
| UI-04: initial DOM | Bounded the homepage to 48 cards. Full-roster suggestions use a lazy search index that includes all charge descriptions and ORC codes. Search, filters and deep links reach the complete current roster at `/archive/`. |
| UI-06: visual polish | Aligned reference-card radii with the shared card token; neutralized competing text where appropriate without changing the F1 through F5 severity fills. |
| UI-08: local navigation | Replaced the permanent fade with wrapping local links, including the final Help destination. Also fixed narrow court-directory label/value overflow found during verification. |
| UI-10: judge labels | Existing name-specific profile disclosures and official links were already correct. Preserved them and added the judge name to the optional standing-orders disclosure. |
| O-01 / O-02 / UI-02 / UI-05 / UI-09 | Preserved compact homepage heading, desktop navigation wrap, roster-first ordering and all navigation destinations. No unrequested record action bar or rebrand. Documented these decisions. |

## Homepage weight

Same repository data snapshot, before and after. Gzip figures are locally compressed HTML sizes, not measured production transfer sizes.

| Metric | Before | After |
| :-- | --: | --: |
| Server-rendered cards | 717 | 48 |
| HTML bytes | 974,541 | 82,066 |
| Gzip bytes | 108,714 | 14,332 |
| DOM elements in initial HTML | 7,924 | 824 |

HTML is about **92% smaller**. The full roster is still available through the archive. This trades preview-local filtering for an explicit full-roster route rather than downloading hundreds of hidden cards.

## Evidence

| File | Contents |
| :-- | :-- |
| [report.json](report.json) | Browser assertions, axe results, font sizes, target bounds and table measurements |
| [performance.json](performance.json) | Reproducible initial HTML size, gzip size and element counts |
| [Desktop homepage](home-1440-dark.png) | Final dark desktop rendering |
| [Mobile homepage](home-390-dark.png) | Final dark mobile rendering |
| [Narrow light homepage](home-320-light.png) | 320px light rendering |
| [Mobile bond rows](schedule-390-dark.png) | Offense/statute and residency amounts together |
| [Narrow charge rows](charges-320-light.png) | Charge label/value relationships without horizontal scrolling |
| [Narrow record](record-320-light.png) | Single-column record and in-flow presumption-of-innocence notice |

Reproduction and design contracts: [`design/ui-remediation.md`](../../design/ui-remediation.md). Browser regression runner: `scripts/check_ui_remediation.cjs`. Python regressions: `tests/test_ui_remediation.py`.

## Limits and remaining validation

Use the [manual QA checklist](manual-qa-checklist.md) to record screen-reader, iPhone zoom/touch, and physical-device results. All manual checks are currently marked Not run.

| Item | Status |
| :-- | :-- |
| Screen-reader sessions | NVDA, JAWS and VoiceOver manual verification remains unperformed. Automated semantics checks are not a conformance certification. |
| Physical mobile performance | Android parse/input latency, iOS control zoom and real network timings remain unmeasured. The size reduction is verified locally. |
| Moderated usability | Heading hierarchy, tone, navigation breadth and task-completion research remain future validation, as the audits requested. |
| External build feeds | Build succeeded with the existing missing optional Firecrawl feed warnings. No feed content was invented or new empty data artifacts added to Git. |
| Live production | HTTPS requests from this sandbox failed during TLS connection setup. Verification targets the locally rebuilt output, not a deployed production change. |
