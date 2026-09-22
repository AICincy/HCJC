# UI audit remediation contract

Source findings: the two reports under `audit-output/` dated 2026-09-22.

## Preserved product decisions

| Decision | Contract |
| :-- | :-- |
| Roster first | Search and recent-booking cards precede audience routing. |
| Publisher | JCStream remains the name. The search area identifies it as independent. |
| Severity | F1 through F5 retain their existing red-to-amber fills and text labels. |
| Legal context | Presumption of innocence and FCRA restrictions remain in-flow on records. |
| Navigation | Keep the current destinations and desktop wrap. |
| Heading exception | The homepage H1 is deliberately compact so the roster is the primary content. Reference titles keep their larger scale. |

## Typography and assets

| Role | Family and fallback | Sizing |
| :-- | :-- | :-- |
| Body, headings, controls | Public Sans; system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif | Body 15px; search/select controls at least 16px |
| Identifiers and numeric metadata | IBM Plex Mono; ui-monospace, SFMono-Regular, Menlo, Consolas, monospace | Roster metadata at least 12px |
| Charge text | Public Sans | `--type-charge`: 14px |
| Record legal notice | Public Sans | `--type-legal`: 13px, line-height 1.6, maximum 75ch |

Only Public Sans and IBM Plex Mono weights 400, 500, 600 and 700 ship. Unreferenced JetBrains Mono and Plex Sans assets were removed from source and published output.

## Roster loading and navigation

The homepage renders at most 48 cards in booking order. Its visible notice identifies this as a preview, not the complete roster. The degree distribution and filter options still describe the full current roster.

Search suggestions fetch `search.json` on focus/input. Its `s` field contains the same full-name, all-charge-description, ORC-code and inmate-number search text used on roster cards. A failed index request announces unavailability rather than asserting no matches. The Search all button or Enter submits to `/archive/`; preview filters route there too. Existing homepage query links and month fragments forward to the full roster. Archive pagination, sorting and filtering remain progressive enhancements.

Without JavaScript, the archive exposes every current record and native month disclosures. A visible no-JavaScript note explains browser Find. The archive is not a historical store of released people.

## Accessibility contracts

| Component | Contract |
| :-- | :-- |
| Degree strip | Informational `role="img"` with degree/count summary; no click handler; visible caption directs users to Charge level. |
| Tier badges | Real 28px-high buttons, no overlapping expanded pseudo-element hit areas; keyboard tooltip and Escape retained. |
| Links | Persistent underlines in prose, definitions, table cells, legal notices and reference values. Structured navigation and controls retain their non-color cues. |
| Dark text | Dedicated `--accent-text`; lightened category text where needed. Decorative accents and severity fills are separate. |
| Mobile tables | Only `.charges.stackable` tables change layout below 721px. Headers remain in the accessibility tree; explicit table roles preserve semantics; each value has a visible label. |
| Local navigation | Links wrap rather than clipping or fading the last destination. |
| Legal notice | Heading, readable type, constrained measure, full-width narrow-screen record column; no disclosure gate. |

## Reproduce verification

```sh
python -m pytest -q
JCSTREAM_SITE_BASE_URL='' python -m web.build --out .cache/remediation-site
python -m http.server 8777 --bind 0.0.0.0 --directory .cache/remediation-site
```

Run the server separately from the one-shot checks. The browser script needs Node, Playwright, axe-core and an installed Chromium browser:

```sh
npm install --prefix .cache/ui-tools playwright axe-core
NODE_PATH="$PWD/.cache/ui-tools/node_modules" \
  node scripts/check_ui_remediation.cjs
```

Set `CHROMIUM_EXECUTABLE` when using a system browser. Set `UI_BASE_URL` for a different server origin and `UI_REPORT_DIR` for a different evidence directory. The default evidence directory is ignored `.cache/ui-verification`.

The script runs real-CSP interaction checks and 72 axe scans. Deep-link coverage includes combined sort/tier/page-size/page reloads, out-of-range page clamping, interactive sort reset, and homepage month-fragment forwarding. CSP bypass is used only to inject axe into test browser contexts; production CSP is unchanged. It also checks reflow, target sizes, search fonts, no-JavaScript access, deep-link reload, long identifiers, and seven viewport widths in both themes.

Automated checks do not replace NVDA/JAWS/VoiceOver sessions, iOS zoom tests, physical-device performance measurement or moderated task testing.
