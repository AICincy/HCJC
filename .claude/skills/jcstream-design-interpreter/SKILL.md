---
name: jcstream-design-interpreter
description: Use when porting a design asset into the JCStream project — a Figma export, JSX mockup, screenshot, design zip, or hand-drawn spec. Translates the input into Jinja templates + CSS tokens + Python helpers while preserving the static-site / no-JS-required contract and accessibility. Trigger phrases: "port this design", "implement the mockup", "translate the Figma", "from this screenshot", "build from this mockup", "convert this JSX", "redesign the homepage from this", "redesign … from this spec", "here's a Figma/PNG/screenshot of the new …", "based on this PNG".
---

# JCStream design interpreter

You translate design specs into the JCStream stack. Inputs vary (JSX, Figma export, screenshots, design zips); the *output contract* is fixed.

## Output contract
1. **Static Jinja templates** (`web/templates/*.html`) — no React, no client framework.
2. **Token-driven CSS** (`web/static/style.css`) — every color/space/type goes through `:root` tokens (see **jcstream-stylesheet-author**).
3. **Python helpers in `web/build.py`** when the design surfaces a computed value not already exposed (see **jcstream-build-helper-author**).
4. **No required JavaScript.** Progressive enhancement only — the site must be fully readable with JS disabled.
5. **Accessibility preserved or improved** — see **jcstream-a11y-auditor**.

## Translation playbook
For each design component:

1. **Identify the input shape.** JSX? Pull the JSX file. Figma? Ask for the spec or the screenshot. Zip? Unzip into `/tmp` and read the manifest.
2. **Map class names.** The `.ut-*` table below is a **historical worked example** from the modern-utility port — those selectors no longer exist in the live CSS (only a stray `.ut-muted` remains at `style.css`). For a new design, write a fresh mapping table before coding; use the `.ut-*` table only as a worked-example template.
3. **Tokenize the colors.** Don't paste hexes inline; add them to `:root` if they're truly new, otherwise reuse.
4. **Extract data needs.** Note every value the design displays. For each, find or write a build.py helper — existing globals include `bond_context`, `display_date`, `timeline_markers`, `primary_charge`, `primary_chapter`, `primary_tier`, `recent_booked_inmates`, `similar_by_statute`, `tier_counts`, `avatar_initials`, `card_data`, `approx_age` (`web/build.py`).
5. **Render with a sample snapshot first.** Run `python -m web.build` against `data/current.json` and open the page. Don't ship until the live data looks right.

## Pitfalls
- **JSX `useState` / `useMemo`**: stateful UI is out of scope. Either pre-compute the value in build.py or use a tiny progressive-enhancement JS hook (e.g. the table/cards toggle).
- **JSX `onClick={() => onSelect(id)}`**: convert to a plain `<a href="{{ base_url }}/inmate/{{ id }}/">` and let the browser do navigation.
- **JSX inline SVGs with computed paths**: fine to copy verbatim, but if they depend on data, render them server-side from Jinja.
- **Design fonts not in the system stack**: the project fetches **only Inter + JetBrains Mono** from Google Fonts (`base.html`). Geist / Geist Mono appear as CSS *fallbacks* in `style.css` but are never loaded — a design that depends on Geist will silently render as Inter. Don't add a third Google Font without a strong reason.
- **`React.Fragment` or `<>...</>`**: drop the fragment, render children directly.
- **CSS-in-JS or styled-components**: extract to vanilla CSS classes.

## Project primitives a port must preserve
A redesign that silently drops one of these regresses live behavior. Reuse them; don't recreate parallels.

- **Shared lightbox + `inert` focus management** (`base.html`, `style.css`): one `<div class="lightbox" id="lb" role="dialog" aria-modal="true" hidden>` for the whole site. JS swaps the `<img>` and marks every other body child `inert` (with a Tab-cycler fallback for browsers without `inert` support). Any image-detail design wires into this dialog via `data-photo` / `data-photo-cap` / `data-photo-alt` attributes — do not author a second modal.
- **Roster view-toggle** (`index.html`, `base.html`, `style.css`): `body.is-table` flip driven by a `#view-toggle` button with `aria-pressed` + `localStorage` persistence (`jcs-view`). A roster-listing redesign must keep the toggle button and the `body.is-table` CSS branch.
- **`data-*` filter hooks** (`_card.html`, `index.html`, `base.html`): every inmate card carries `data-tier`, `data-chap`, `data-name`, `data-search`; the filter bar uses `data-filter` on inputs. New card markup without these attributes breaks the search/filter bar.
- **`css_version` cache-bust** (`build.py`): the stylesheet querystring is `sha256(style.css)[:10]`. CLAUDE.md explicitly warns not to key it off the data timestamp. Don't invent a parallel cache-bust scheme.
- **`base.html` override blocks**: `base.html` defines `{% block title %}`, `{% block body_class %}`, `{% block sr_h1 %}`, `{% block content %}`. New page templates `{% extends "base.html" %}` and override these blocks — never duplicate `<head>` / `<header>` / the lightbox / the script block.

## Reference mapping (historical worked example: modern-utility direction → JCStream class names)
| Design class | JCStream class |
|---|---|
| `.dir-utility` | (body — no class needed; styles cascade from `body`) |
| `.ut-header` | `.masthead` |
| `.ut-brand-mark` | `.masthead .brand::before` (generated content) |
| `.ut-tier-F1…MM` | `.tier-F1…MM` |
| `.ut-ladder-cell` | `.ladder-cell` |
| `.ut-recent-card` | `.rb-card` |
| `.ut-detail-hero` | `.inmate-hero` |
| `.ut-kpi-card` | `.kpi` |
| `.ut-toplist-row` | `.toplist-row` |
| `.ut-bondctx-axis` | `.bondctx-axis` |
| `.ut-tl-axis` | `.tl-axis` |
| `.ut-cal-day` | `.cal-day` |

When a new direction lands, extend this table before writing code.

## Anti-patterns
- Shipping JS for something Jinja can render at build time.
- Recoloring tokens to match a design's hex literals — adjust the design's hex on paper if the project's palette is the source of truth.
- Adding a build.py helper without registering it on `env.globals`.

## Verify
Build, render, eyeball, then run tests:
```sh
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
python -m pytest -q
```
