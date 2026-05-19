---
name: jcstream-template-reviewer
description: Use when reviewing the JCStream presentation layer — Jinja templates in `web/templates/*.html`, the RSS feed `web/templates/feed.xml`, the XSLT stylesheet `web/static/feed.xsl`, and the no-required-JS enhancement script `web/static/main.js`. Covers XSS-safe escaping (every `{{ }}` and `|safe`), inline JSON-LD shape, RSS validity, semantic HTML structure, XSLT correctness, progressive-enhancement contract (lightbox / filter / tier-tooltip degrade without JS), and third-party-script hygiene (none allowed per FCRA). **Read-only** — produces a finding report and hands fixes off to `jcstream-template-author` / `jcstream-a11y-auditor` / `jcstream-legal-copy-author`. Trigger phrases: "review the templates", "review inmate.html", "review the homepage", "check the RSS feed", "review the JSON-LD", "schema.org review", "review main.js", "review the filter JS", "review the lightbox", "audit the feed.xsl", "template code review", "XSS check", "Jinja escape audit".
---

# JCStream template reviewer

You review the presentation layer and produce a findings report. **You do not edit code.** Hand off fixes to the relevant author skill.

## What this layer looks like

| Path | Role | Lines | Risk surface |
|---|---|---|---|
| `web/templates/base.html` | Root layout, masthead, lightbox markup, search combobox, JSON-LD links | ~140 | XSS, JSON-LD shape, ARIA inventory |
| `web/templates/index.html` | Homepage, filter dropdown, card grid, table mode toggle, recent activity | varies | XSS in inmate fields, filter combobox ARIA |
| `web/templates/inmate.html` | Inmate detail, charges table, ladder cell, **inline JSON-LD `<script type="application/ld+json">` at line 18** | varies | JSON-LD shape, charge table escaping |
| `web/templates/stats.html`, `statute.html`, `data.html`, `help.html`, `visit.html`, `court.html`, `courts.html` | Secondary pages | varies | semantic HTML, legal copy correctness |
| `web/templates/_card.html` | Card partial included from `index.html` | ~25 | tier badge wiring, photo escaping |
| `web/templates/feed.xml` | RSS 2.0 + atom feed | ~40 | XML validity (no HTML entities like `&middot;` — see `tests/test_build.py::test_feed_template_emits_strict_xml`) |
| `web/static/feed.xsl` | XSLT stylesheet that renders the RSS for browsers | varies | XSLT correctness, output sanitization |
| `web/static/main.js` | Single external JS bundle (no inline scripts in templates) — filter, lightbox, tier-tooltip, search combobox | varies | progressive enhancement, third-party imports, focus management |

There is **no inline JavaScript inside templates** (verified at the time of this skill's authoring). All JS lives in `web/static/main.js`, loaded with `defer`. If a future PR adds an inline `<script>` tag without `type="application/ld+json"`, flag it as a deviation from the established pattern.

## What to check (review checklist)

### XSS — Jinja escaping

Jinja autoescapes HTML in `{{ }}` by default for `.html` files. The risk surfaces are:

| Pattern | Why it's risky | What to flag |
|---|---|---|
| `{{ x \| safe }}` | Bypasses escaping | Confirm `x` is server-generated and cannot contain user/HCSO input. Currently **zero** uses in templates — any addition needs justification. |
| `{{ x \| safe \| something }}` | `safe` upstream of a filter | Even more risky; the filter may not preserve safety. |
| `data-*="{{ x }}"` in HTML | Attribute context | Jinja escapes for HTML by default; only an issue with `\| safe`. |
| `href="{{ url }}"` where `url` is user-derived | URL injection | Check `javascript:` schema is filtered. Inmate URLs and ORC URLs are server-generated; safe. |
| Inside `<script type="application/ld+json">` | JSON-LD escaping needs JSON context, not HTML | Jinja's default is HTML-escape. `inmate.html:18+` JSON-LD must escape `<`, `>`, `&` for HTML AND escape `\\`, `"`, control chars for JSON. Verify the helper used (likely `esc()` or `tojson` filter). |

Grep targets:
```sh
grep -rn "| safe\b\|esc(\|tojson" web/templates/
```

### JSON-LD — schema.org shape

`web/templates/inmate.html:18` emits inline JSON-LD. Verify:

- `@context` is `https://schema.org`
- `@type` matches the entity (likely `Person` or `Article` with `about`)
- `dateCreated` / `datePublished` are ISO 8601 or omitted (never empty string — `audit/09_content_governance.md` flagged the `dateCreated: ""` regression class)
- `license` and `creator` are coherent — `audit/09_content_governance.md` flagged the case where `license: CC BY-NC 4.0` co-occurs with `creator: Hamilton County` (which doesn't grant CC). Either drop `license` or attribute correctly.
- All string values are HTML-AND-JSON escaped (see above).

### RSS feed validity (`feed.xml`)

The feed is strict XML. Common breakage:

- HTML entities (`&middot;`, `&rsquo;`, `&nbsp;`) — strict XML parsers reject these. The locked-in regression test `tests/test_build.py::test_feed_template_emits_strict_xml` exists for this reason; flag any new HTML entity in `feed.xml`.
- Unescaped `&` in URLs — must be `&amp;`.
- Missing `<atom:link rel="self">` — currently present at line 7.
- `<lastBuildDate>` without RFC 822 format — uses `rfc822()` helper.

Grep target:
```sh
grep -nE '&(?!amp;|lt;|gt;|quot;|apos;|#)' web/templates/feed.xml
```

### XSLT (`web/static/feed.xsl`)

The feed has `<?xml-stylesheet type="text/xsl" href="{{ base_url }}/static/feed.xsl"?>` so browsers render it as HTML. Verify:

- Output method (`<xsl:output method="html"...>`) is set so the browser renders, not displays as raw XML.
- Any string the XSLT pulls from RSS items is `xsl:value-of` (auto-escaped), not `xsl:copy-of` (raw).
- Date formats match the human-facing convention (see `web/build.py:_rfc822`).
- The stylesheet does not load remote resources (FCRA-sensitive — no third-party scripts / images / styles).

### `main.js` — progressive enhancement contract

JCStream guarantees a no-JS path for every interactive feature (per `audit/11_spa_structural_audit.md`). Verify:

- Every interactive component degrades: lightbox falls through to the photo `href`; filter bar's controls are `hidden` until JS un-hides; search dropdown is opt-in; tier-tooltip is decorative.
- No third-party imports (`import` from a URL, `<script src="https://...">`).
- No inline event handlers in templates (`onclick=`, `onerror=`, `onload=`). Currently zero — flag any addition.
- Lightbox focus management: open → trap focus inside dialog; close → return focus to the triggering element. Uses `inert` attribute on background where supported.
- ESC handlers: lightbox closes on ESC; filter dropdown closes on ESC; search combobox closes on ESC.
- Reduced-motion: any JS-driven animation needs `matchMedia('(prefers-reduced-motion: reduce)')` check (CSS `@media (prefers-reduced-motion: reduce)` only catches CSS animations).

### Semantic HTML

| Pattern | Anti-pattern |
|---|---|
| `<button>` for actions | `<div onclick="">` |
| `<a href>` for navigation | `<div>` styled as link |
| `<nav>`, `<main>`, `<aside>`, `<footer>` landmarks | `<div class="nav">` |
| `<h1>` once per page | multiple `<h1>` or missing `<h1>` |
| `<ul>` / `<ol>` for lists | `<div>` with manual bullets |
| `<table>` for tabular data with `<caption>` | `<div class="row">` |

The screen-reader-only `<h1>` in `base.html` (`{% block sr_h1 %}...{% endblock %}`) is intentional — the homepage renders it via `sr-only` so SR users get a landmark before the visible H1. Don't flag it as missing.

### Third-party hygiene (FCRA)

JCStream must not load anything from a third party that could be used to track or score subjects. Flag:

- `<script src="https://...">` (any external script)
- `<img src="https://...">` (any external image, including tracking pixels)
- `<link rel="stylesheet" href="https://...">` (external CSS)
- `<iframe src="https://...">` (any external iframe)
- Any URL in `main.js` that isn't a same-origin static asset

Acceptable exceptions (with documentation):

- `<link rel="alternate" type="application/rss+xml" href="/feed.xml">` (relative, self)
- `<a href="https://codes.ohio.gov/...">` (outbound link, not embedded)
- Giscus comments widget (opt-in via `JCSTREAM_GISCUS_*` env vars per `CLAUDE.md`); the widget loads from `giscus.app`. If `giscus.repo_id` is set, the embed code is expected.

### css_version cache-busting

`base.html` references `{{ base_url }}/static/style.css?v={{ css_version }}`. The `css_version` helper hashes the stylesheet content (see `CLAUDE.md`: "don't key it off the data timestamp again"). Flag any change that:

- Removes the `?v={{ css_version }}` query string
- Replaces `css_version` with a timestamp helper
- Adds a similar pattern for `main.js` without using a content hash

### data-* filter contracts

`index.html` uses `data-*` attributes on each card (`.card-inmate`) as filter hooks: `data-tier`, `data-name`, `data-charge`, `data-booked`. The filter JS reads these. Flag:

- Removal of a `data-*` attribute that the JS reads
- Addition of a `data-*` attribute with no corresponding filter rule (dead data)
- Inconsistent data-* casing (HTML attrs are lowercase; `data-Booked` works but breaks convention)

### Lightbox `data-photo` / tier-tooltip `data-tip` contracts

`_card.html` emits `data-photo="..." data-photo-cap="..." data-photo-alt="..." aria-label="..."` on the thumb link, and the tier badge has `aria-describedby="tier-tip" data-tip="..."`. The JS reads these by name. Flag any rename or removal.

### Legal-copy preservation

The following must appear on the pages noted (handoff to `jcstream-legal-copy-author` for the actual copy; flag presence only):

| Block | Required on |
|---|---|
| Presumed-innocent banner | `index.html`, `inmate.html`, `stats.html`, `statute.html`, `data.html` |
| FCRA disclaimer | `data.html` footer or `base.html` footer |
| ORC § 149.43 attribution | `data.html` |
| ORC § 2953.32 expungement-removal protocol | `data.html` |
| No-fee guarantee | `data.html` |
| CC BY-NC 4.0 license + comment policy | `base.html` footer (or `inmate.html` for Giscus) |
| `<meta name="robots" content="noindex,noarchive">` on inmate pages | `inmate.html` (or via `base.html` block) |

## Anti-patterns specific to JCStream

1. **Re-introducing inline `<script>` blocks** (other than `application/ld+json`) — all JS belongs in `main.js`.
2. **`|safe` filters** — currently zero in the codebase; any addition needs justification.
3. **Hardcoded `aretheyinjail.com` URLs** — use `{{ site_url }}` or `{{ base_url }}` so local builds (`JCSTREAM_SITE_BASE_URL=""`) work.
4. **HTML entities in `feed.xml`** — see strict-XML regression test.
5. **Inline event handlers** (`onclick=`, etc.) — kill keyboard accessibility and conflict with the static-site contract.
6. **JSON-LD blocks emitted with HTML escaping only** — JSON needs JSON-context escaping for `\`, `"`, control chars.

## Tools to run

```sh
# Build the site locally and inspect rendered output
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build

# Lint XML (RSS feed)
xmllint --noout docs/feed.xml

# Validate JSON-LD on a sample inmate page
python -c "from bs4 import BeautifulSoup; import json, sys; s = BeautifulSoup(open(sys.argv[1]), 'html.parser'); [json.loads(x.string) for x in s.find_all('script', type='application/ld+json')]; print('OK')" docs/inmate/<id>/index.html

# Targeted grep for the high-signal anti-patterns
grep -rnE '\| safe\b|onclick=|onerror=|onload=|<script src="https?://|<iframe src="https?://' web/templates/

# Test suite (the strict-XML regression test must stay green)
python -m pytest tests/test_build.py -k feed -q
```

If `xmllint` is not installed, fall back to opening `docs/feed.xml` in a browser and checking the XSLT-rendered view loads. Don't add `xmllint` to the project; it's a dev-side tool.

## Output format

Per-template findings table:

```
## web/templates/inmate.html

| Severity | Line | Category | Finding | Fix owner |
|---|---|---|---|---|
| High | 18 | json-ld | `dateCreated` may emit empty string if `inm.booking_date` is missing | jcstream-template-author |
| Med  | 142 | semantic | `<div class="row">` for tabular charge data — should be `<table>` | jcstream-template-author |
| Low  | 87 | data-attrs | `data-Booked` casing inconsistent with rest of the file | jcstream-template-author |
```

Top-of-report summary table with file counts per severity, plus a "Top 3" actionable list.

## Handoff

| Finding lives in | Hand off to |
|---|---|
| Template structure / Jinja correctness / `data-*` contracts | `jcstream-template-author` |
| `feed.xml` / `feed.xsl` shape | `jcstream-template-author` |
| `main.js` progressive enhancement | `jcstream-template-author` (JS lives adjacent to templates per the no-inline contract) |
| Visible legal copy text | `jcstream-legal-copy-author` |
| ARIA correctness / WCAG contrast / keyboard nav | `jcstream-a11y-auditor` |
| CSS rule changes | `jcstream-stylesheet-author` |
| Build helper that feeds the template | `jcstream-build-helper-author` |
| Test for a template behavior | `jcstream-test-author` |

## Verify

After the author skill makes edits:

```sh
python -m pytest tests/test_build.py -q      # the feed-as-strict-XML test must stay green
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
xmllint --noout docs/feed.xml                # if installed
```
