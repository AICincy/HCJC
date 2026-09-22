# Manual UI release checklist

**Checklist approval:** Approved by the owner on 2026-09-22.

**Execution status: NOT RUN.** Automated results and checklist approval do not complete any checkbox below.

Latest identified local build and open risks: [Closure execution record](closure/README.md). The 2026-09-22 automated rerun does not complete manual validation.

Test the remediated preview before publication. Production has not been updated by this session. Use ordinary browsing only; do not submit correction/removal requests or other external forms as test actions.

## Record the test environment

| Field | Fill in |
| :-- | :-- |
| Tester and date | |
| Preview URL and revision/build | |
| Device and operating system | |
| Browser and version | |
| Screen reader and version | |
| Theme | Dark / Light |
| Text size or zoom | |
| Result | Pass / Fail / Not run |

Source baseline: `fd12870`. Remediation lives on `arena/01a0cae3-hcjc`; record the tested revision after a commit, or identify the working-tree preview explicitly.

## Required environments

| Environment | Purpose | Complete |
| :-- | :-- | :-- |
| Windows, Firefox or Chrome, NVDA | Keyboard and table semantics | [ ] |
| Windows, Edge or Chrome, JAWS | Independent screen-reader check | [ ] |
| iPhone, Safari, VoiceOver | Touch navigation, controls and table reading | [ ] |
| iPhone, Safari, VoiceOver off | Input zoom, pinch zoom and touch targets | [ ] |
| Mid-range Android phone, Chrome | Cold loading and first useful interaction | [ ] |

Record unavailable environments as **Not run**, not Pass. Exercise both themes. Use a record with multiple charges and case links for the table tests.

## Keyboard and screen-reader checks

| Done | Task | Pass criteria |
| :-- | :-- | :-- |
| [ ] | Reload Home, then Tab to the skip link and activate it. | Focus reaches main content. The search heading is discoverable by heading navigation. No focus trap occurs. |
| [ ] | Read the notice beside search. | It identifies JCStream as independent and the displayed cards as a preview, not the entire roster. |
| [ ] | Focus search. Search for an inmate number from the archive that is absent from the first 48 cards. | Suggestions include the record. A results status is announced. Enter opens the full-roster search and finds it. The preview does not falsely announce no matches. |
| [ ] | Activate Filters with Enter or Space. Choose a charge level. | Controls have distinct labels. All options are operable. The resulting archive filter includes matching records outside the preview. Focus and navigation remain understandable. |
| [ ] | Read the degree strip and category legend. | The degree/count summary is available. Category names and F/M meanings are available when Filters is open. The strip is not presented as a button and does not invite clicking. |
| [ ] | Focus a tier badge; read its tooltip; press Escape. | The button identifies the degree and charge-detail purpose. The tooltip describes the focused record, not a previously focused record. Escape dismisses it without moving focus. |
| [ ] | Read charge-table rows at desktop width and a narrow/mobile width. | Table name, row boundaries and headers remain discoverable. ORC, description, level, date, bond, disposition and case number stay associated with the correct charge. No cell content disappears or moves into another row. |
| [ ] | Read the bond schedule at narrow width. | Each offense stays associated with its ORC and all three residency amounts. Criminal/Traffic group labels are understandable. NO BOND and source flags retain their wording. |
| [ ] | Navigate the Help local links from first through last. | Every destination, including the last link, is visible and operable. Focused links are not clipped. Each link reaches the intended section. |
| [ ] | Navigate judge disclosures and official links by control/link list. | Each profile control includes the judge's name. Official profiles are distinguishable from on-page disclosures. |
| [ ] | Read a record without opening any disclosure. | Presumption of innocence, accusation-only framing, removal/no-fee information and FCRA restrictions remain in-flow. |
| [ ] | Change archive page, then reload its URL. Switch sorting and reset filters. | The copied page URL restores its page. Sorting and filtering preserve the records. Announcements describe the current state without repeated or contradictory messages. |

Record duplicate or confusing announcements verbatim. Do not infer usable screen-reader behavior solely from the accessibility tree or axe results.

## iPhone, touch and zoom

| Done | Task | Pass criteria |
| :-- | :-- | :-- |
| [ ] | With VoiceOver off, focus Home search, archive search and charge-level controls. | Safari does not unexpectedly zoom because of undersized text. The keyboard does not make the active control unreachable. |
| [ ] | Pinch zoom, increase text size, and rotate the device. | Names, controls, legal copy and table values remain readable. Controls and essential content are not clipped. User zoom remains available. |
| [ ] | Tap several tier badges beside record links. | The intended badge responds without opening an adjacent record or photo accidentally. Tooltip text fits the viewport. |
| [ ] | With VoiceOver on, swipe through search, Filters and a stacked charge row; double-tap controls. | Touch exploration finds the same functions as keyboard navigation. Table reading does not lose header/value relationships. |
| [ ] | Scroll through stacked bond rows and focus an ORC link. | The offense and its amounts can be read together without horizontal scrolling. Sticky controls do not fully obscure the focused link. |
| [ ] | Inspect Home, Help, warnings, selected filters and pager states in both themes. | Small text remains legible. Prose links have a visible non-color cue at rest. Focus indicators remain discernible. |

## Physical-device performance

Use the same device, browser, connection and roster snapshot for before/after comparison. Production may contain a different snapshot and is not a controlled baseline. Repeat cold loads three times per build. Record median values, not just the best run.

| Measurement | Before | After | Notes |
| :-- | :-- | :-- | :-- |
| Device, network and throttling settings | | | |
| Compressed homepage transfer | | | |
| DOMContentLoaded / parse-related timing | | | |
| Time until search accepts and displays typed input | | | |
| First suggestion latency after focus/input | | | |
| Filter navigation latency to full archive | | | |
| Typing response while the archive loads | | | |

**Pass criteria:** homepage loading is materially improved; search does not drop input or stall; full-roster filtering remains usable. Record any noticeable delay and its duration. These are usability criteria, not a claim of a measured Core Web Vitals score.

The verified local HTML reduction is 974,541 to 82,066 bytes. That is not a substitute for this physical-device test.

## Failure record

| Field | Fill in |
| :-- | :-- |
| Checklist task | |
| Device/browser/AT/theme | |
| URL and build | |
| Reproduction steps | |
| Expected behavior | |
| Observed behavior or exact announcement | |
| Screenshot/recording reference | |
| Severity and affected task | |
| Fix reference and retest result | |

Keep screenshots and recordings limited to what demonstrates the defect. Avoid copying unnecessary personal-record information into issue titles or public commentary.

## Release sign-off

| Gate | Result |
| :-- | :-- |
| Required environments exercised | Not run |
| Screen-reader checks | Not run |
| iPhone touch and zoom | Not run |
| Physical-device performance | Not run |
| Blocking failures resolved and retested | Not run |
| Reviewer and date | |

Missing coverage must remain explicit. Passing this checklist supports release confidence; it does not certify full WCAG conformance or replace the audits' deferred moderated usability research.
