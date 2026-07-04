# Execution prompt: complete the JCStream UI/UX (UI layer only)

Paste everything below the line into ChatGPT 5.5. It has full agentic access
to the `AICincy/HCJC` repository, the same as Claude Code. Nothing to fill in:
paste and send.

---

You are a senior front-end engineer finishing the UI/UX of **JCStream**, a
static public-records mirror of the Hamilton County (Ohio) Justice Center
inmate roster (live at https://www.aretheyinjail.com). Your job is to make the
UI **fully done**: complete, consistent, polished, accessible, and easy to use,
building on the existing civic-modern light design. You do **not** change core
code or data behavior.

## Output format

- Work on the task branch the agent harness assigns you; never commit to
  `main`. Make focused commits with clear messages and open pull requests
  against `main`.
- Group work into small, reviewable pull requests, one coherent UI concern per
  PR (e.g. "responsive roster cards", "empty/loading states", "focus-visible
  polish"). Do not bundle unrelated changes.
- For every PR that changes anything visible, attach before/after screenshots
  at desktop (1440px) and mobile (390px) widths, light theme only.
- Before each commit, run `python -m pytest -q` and keep it green. If a
  template change breaks a test, fix the template, not the test, unless the
  test asserts old markup you intentionally replaced.

## The stack (read before editing)

- Static site. A Python build (`web/build.py`) renders Jinja templates into
  `docs/` from `data/current.json`. You edit templates and assets; the build
  and data are off-limits (see Boundary).
- Templates: `web/templates/` — `base.html`, `index.html`, `inmate.html`,
  `stats.html`, `statute.html`, `data.html`, `_card.html`, `bond-disparity.html`,
  `court.html`, `courts.html`, `help.html`, `visit.html`, `transparency.html`,
  `feed.xml`.
- Assets: `web/static/` — `style.css` (~3100 lines, the single stylesheet),
  `main.js` (~360 lines, progressive enhancement), `map.js` (Leaflet map),
  `feed.xsl`, plus `fonts/`, `img/`, `judges/`, `vendor/`.
- Build the site locally to preview: `JCSTREAM_SITE_BASE_URL="" python -m web.build`,
  then serve and screenshot (see Screenshot flow). Never open `docs/` over
  `file://` — root-absolute `/static/...` links load unstyled. Always serve over
  HTTP.

## Boundary (the one rule that cannot bend)

**UI layer only. Do not change core code or data behavior.**

| Editable (UI) | Off-limits (core) |
| :-- | :-- |
| `web/templates/*.html` | `scraper/**` (all of it) |
| `web/static/style.css` | `web/build.py` Python logic, page-render functions, `env.globals` registrations |
| `web/static/main.js`, `map.js` | `web/classify.py`, `web/shape/**` (data shaping / tier / category logic) |
| `web/static/` assets you add (inline SVG, CSS) | `data/**`, the sweep, JSON schemas |
| CSS/JS/markup, ARIA, copy layout | `tests/**` (only touch if markup you changed is asserted) |

- Use only template variables and Jinja globals that already exist. If a UI
  idea genuinely needs a new computed value, a new data field, or a new Python
  helper, **do not build it** — list it under "Requires a core change" in the
  PR description and move on. Staying in the UI lane is the whole point.
- Do not add build steps, bundlers, or a framework. This is hand-written
  Jinja + CSS + vanilla JS and stays that way.

## Workflow

1. **Audit first.** Walk every page type (roster/index, inmate detail, stats,
   statute, data, bond-disparity, court, courts, help, visit, transparency).
   Produce a short punch list of UI/UX gaps: inconsistencies, rough responsive
   breakpoints, missing empty/loading/error states, weak affordances, unclear
   hierarchy, keyboard/focus gaps, and anything unfinished. Share the punch list
   and a proposed pass order before large changes.
2. **Implement in passes**, smallest-risk first: consistency and tokens →
   layout/responsive → interaction states → accessibility polish → net-new
   ease-of-use features. One PR per pass or per concern.
3. **Verify each pass** against the Definition of done. Screenshot desktop and
   mobile. Run the tests. Re-check the page you changed AND one unrelated page
   for regressions (shared CSS bleeds).

## Hard rules

- **No required JavaScript.** Every feature must degrade gracefully with JS
  off: content readable, links work, forms/filters have a usable no-JS state.
  `main.js` only enhances. Do not make core content depend on it.
- **Single light theme.** There is no dark theme (the dark-mode media query was
  removed by spec). Do not add `prefers-color-scheme: dark`, a theme toggle, or
  dark tokens. `--tier-*-dark` are color names, not a dark theme.
- **WCAG AA.** All text and meaningful UI meets AA contrast (4.5:1 text, 3:1
  large text/UI). Every interactive element has a visible `:focus-visible`
  ring, a name, and keyboard operability. Respect `prefers-reduced-motion`
  (wrap non-essential motion). Preserve/extend correct ARIA
  (`aria-current`, `aria-pressed`, `aria-modal`, `role="status"`, screen-reader
  `.sr-only` text). Do not add a second live region that competes with the
  existing single announcer (`#search-status`).
- **No third-party scripts, fonts, or network calls** beyond what already ships.
  This is an FCRA-boundary requirement. Fonts are self-hosted in
  `web/static/fonts/`; the map uses vendored assets. The only permitted
  third-party embed is Giscus, and only when already enabled via env. Do not
  add analytics, CDNs, trackers, or web fonts.
- **Do not alter legal copy.** Presumed-innocent banners, the FCRA disclaimer,
  ORC § 149.43 attribution, the expungement/removal notice, the no-fee
  guarantee, and the license footer must remain present and unchanged in
  meaning on every page they appear. You may restyle their container; you may
  not weaken, remove, or reword the text.
- **Cache-busting is by content hash.** The stylesheet is versioned by a hash
  the build computes (`css_version`); do not hardcode a version or key it off a
  date. Just edit `style.css`; the build re-hashes.
- **Category and tier hooks are contracts.** Cards carry
  `data-chap="<slug>"` and charges carry `charge-<cls>` classes
  (`2903, 2907, 2909, 2911, 2913, 2917, 2919, 2921, 2923, 2925, traffic, other`).
  Tier classes are `tier-F1`…`tier-MM`; `main.js` builds `sr-<tier>` names
  dynamically. Before deleting any "unused" selector, grep for both the literal
  class and any dynamic construction site. Note: `2905`, `2914`, `2915` are
  intentionally collapsed upstream (into `2903`/`2913`) and have no live
  selectors by design — do not "add the missing" ones.
- **No token aliasing.** The print `:root` overrides `--accent` and `--surface`
  independently; do not alias one design token to another (e.g.
  `--warn: var(--accent)`) or you recolor print output.
- Keep the existing `body.is-table` table view, the lightbox (with its inert
  focus management), the filter/search bar, and the tier tooltip working in
  both JS and no-JS states.

## Screenshot flow (sanctioned)

`cd docs && python3 -m http.server 8899 --bind 127.0.0.1 &`, then drive a
headless browser against `http://127.0.0.1:8899/`. Never `file://`. Capture the
light theme at 1440px and 390px. Attach to the PR.

## Definition of "done" (the completeness bar)

The UI is done when, across **every** page type:

1. Visual language is consistent: spacing scale, type scale, color tokens,
   radius, shadow, and component styling match; no orphaned one-off styles.
2. Fully responsive from ~360px to wide desktop, with deliberate breakpoints
   (720px primary; 540/1024/1080 secondary) and no horizontal scroll or
   overlap at any width.
3. Every state is designed: default, hover, focus-visible, active, disabled,
   empty (no results / no data), and any loading/skeleton where JS populates
   content.
4. Keyboard-only users can reach and operate everything; tab order is logical;
   focus is visible and managed in the lightbox/modals; skip-to-content works.
5. Screen-reader semantics are correct and not duplicated; images have
   appropriate `alt`; icons are `aria-hidden` with text labels.
6. Ease-of-use is improved where it counts: search/filter clarity, scannability
   of the roster and charge tables, obvious primary actions, readable data
   density, and clear affordances for the table view, lightbox, and map.
7. Print stylesheet produces a clean, legal-copy-complete printout.
8. `prefers-reduced-motion` is honored; no motion is required to understand
   state.
9. `python -m pytest -q` is green and no template renders broken markup.

## Failure handling

- If a task cannot be done in the UI layer (needs a new data field, a Python
  helper, or a build change), stop, record it under "Requires a core change" in
  the PR, and continue with UI work that can be done. Never edit `scraper/`,
  `web/build.py` logic, `web/classify.py`, `web/shape/`, or `data/` to force it.
- If a change would remove or reword legal copy, stop and flag it instead.
- If you are unsure whether something is core or UI, treat it as core and ask.

Start with the audit punch list and a proposed pass order. Do not begin large
changes until that plan is shared.
