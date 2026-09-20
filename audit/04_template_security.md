# tpl-sec - HTML Template Security Audit

## Audit metadata
- Skill: jcstream-html-template-security
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 9 (web/templates/base.html 257 lines, web/templates/index.html 310 lines, web/templates/inmate.html 224 lines, web/templates/stats.html 105 lines, web/templates/data.html 112 lines, web/templates/_card.html 21 lines, web/templates/feed.xml 19 lines, web/build.py 1282 lines, scraper/courtclerk.py 43 lines)
- Time: 2026-05-14T00:00:00Z

## Observations
- web/build.py:73-78 configures `Environment(..., autoescape=select_autoescape(["html", "xml"]), trim_blocks=True, lstrip_blocks=True)`. Autoescape is on for both HTML and the RSS feed.
- No `| safe` filter, no `{% autoescape false %}` block, and no `Markup(...)` wrapping appears in web/ or scraper/ (grep returned zero hits).
- web/templates/inmate.html:18-29 emits a `<script type="application/ld+json">` block that interpolates `inmate.full_name`, `inmate.inmate_number`, `inmate.booking_number`, `inmate.booking_date`, and `expand_sex(inmate.sex)` with raw `{{ ... }}` inside JSON string literals. Jinja HTML escaping does not JSON-escape quotes, backslashes, or control characters, so a parser-drift event that injects a `"` or backslash into a name field corrupts the LD+JSON payload and could end the script context early.
- web/templates/base.html:85 already follows the correct pattern: `var ROOT = {{ (base_url or "") | tojson }};`. The same `| tojson` discipline is missing for the inmate.html script block.
- web/templates/base.html:246 defines `esc(s)` escaping `& < > "`, used on every interpolated value in the search-results dropdown (lines 234, 239, 240). `esc()` does NOT escape `'`. base.html:135 defines `escTip(s)` escaping only `& < >`. All current `innerHTML` writes use double-quoted attribute templates, so the missing single-quote escape is latent, not exploitable today.
- web/templates/_card.html:7 places `data-tip="{{ card_tip(inm) }}"` (and lines 5, 10 set `data-photo-cap`, `data-name`, `data-search` from inmate fields). Autoescape handles the attribute-value safely. base.html:138-143 then reads `data-tip`, splits on `\n`, and feeds each line through `escTip()` before assigning to `tip.innerHTML`. Safe round-trip.
- web/templates/inmate.html:69 and _card.html:10 build `data-photo="{{ base_url }}/photos/{{ inmate.photo_filename }}"`. `photo_filename` is set in scraper/sweep.py:270-276 from `f"{inm.inmate_number}.jpg"`. The list-side `inmate_number` is constrained by regex `r"[?&]id=(\d+)"` (parsers.py:17, 55), but `parse_detail_page` (parsers.py:77) overrides it with `bio.get("Inmate Number")`, which is parser-extracted free text with no Pydantic validator.
- web/templates/index.html:228-240 inlines a second script. The `popupHtml(c)` builder uses a local `esc()` (line 229) that mirrors base.html's; every dispatch field (`p.d`, `p.a`, `p.t`) is escaped before concatenation into the Leaflet popup. SRI hashes are present on the Leaflet CSS and JS (lines 235, 239). Good.
- web/templates/feed.xml:11-15 emits `<title>`, `<description>`, `<link>`, and `<guid>` content with no XML CDATA. Because `select_autoescape` covers `.xml`, Jinja escapes `& < > "` for XML, which is sufficient for valid XML. (RSS readers will still see ampersands and angle brackets entity-encoded, which is correct.)

## Analysis

The Jinja environment is configured correctly. `select_autoescape(["html", "xml"])` is active, no `| safe` shortcut is used anywhere, and no template uses `{% autoescape false %}`. The single inline-JS sink that needed `| tojson` already has it (`ROOT` in base.html:85). The escaping discipline for the type-ahead and the map popup is consistent: a small helper escapes `& < > "` before any `innerHTML` write.

The one real bug is the JSON-LD block in inmate.html:18-29. The pattern `"name":"{{ inmate.full_name }}",` interpolates a Python string inside a JSON string literal but only escapes for HTML. A quote in `full_name` ends the JSON value, a backslash escapes the closing quote, and a control character produces invalid JSON. In script-text context, HTML escaping itself does not apply for `&`, `<`, `>` between `<script>` and `</script>` either, so a name containing `</script>` could in principle break out of the script. Today the scraper's `_split_name` and the 256-char cap on `full_name` make a literal `</script>` unlikely, but the right primitive is `| tojson`, which JSON-escapes the value AND uses Jinja's `htmlsafe_json_dumps` that further escapes `<`, `>`, `&`, `'` to avoid `</script>` breakouts. This is a minimal patch with a real upside.

The second item worth noting is that `inmate_number` is not strictly validated. The list-side path is regex-constrained to `\d+` (parsers.py:17), but `parse_detail_page` lets the bio table's `"Inmate Number"` text override the URL-derived ID (parsers.py:77). `photo_filename` is then derived from that override as `f"{inm.inmate_number}.jpg"`. If a malformed detail page produced an inmate_number containing `..` or `/` or a query string, the photo URL in templates would still resolve to that path. Because the templates use this value in `<a href>`, `<img src>`, and `data-photo` attributes (all autoescaped, so quote injection is blocked), the residual risk is path traversal under `/photos/`, not script injection. Mitigation belongs on the model side (a Pydantic validator), not in templates.

The Giscus block in inmate.html:202-216 sources its attributes from `env.globals["giscus"]` (build.py:90-95), which reads `JCSTREAM_GISCUS_*` env vars at build time. Owner-controlled, autoescaped, and `data-strict="1"` is set. No template change required, but a comment in the template documenting that these values must remain owner-side (never URL-derived) would prevent a future contributor from regressing it.

The Leaflet integration in index.html:224-307 is well structured: SRI hashes on the script and stylesheet, `crossOrigin=''`, escaped popup content, a sanity-bounded coordinate parser in `_dispatch_points` (build.py:889-892), and graceful fallback if the CDN fails. The only minor caveat is that any future SRI-hash bump must be done deliberately because the integrity tag is the only barrier against a unpkg.com supply-chain compromise.

The RSS feed (feed.xml) renders `e.name`, `e.event`, and `e.note` from `ChangeEvent` rows. With XML autoescape enabled, ampersands and angle brackets are entity-encoded. `e.timestamp_utc` is used both in `<pubDate>` (which expects RFC-822 dates per RSS 2.0 spec but accepts ISO-8601 today) and inside `<guid>`. Not a security issue, but feed.xml:14 might fail strict RSS validators because `snapshot.generated_utc` style ISO timestamps are not RFC-822. Out of scope for security.

The sparkline SVG in index.html:24-28 and stats.html:49-51 interpolates floats formatted as `%.1f` and integers, with values from `trend.spark` (which build.py computes from `data/history.json`). The `%.1f` format guarantees the value is a real number string, so a non-numeric value would raise TypeError at build time rather than reaching the SVG. Safe by construction.

The two `innerHTML` paths use `esc()` (escapes `& < > "`) and `escTip()` (escapes only `& < >`). Neither escapes single quotes. All present HTML template literals use double-quoted attributes (`href="..."`, `class="..."`), so a single-quoted value cannot escape an attribute today. A future contributor who switches one literal to single quotes would silently re-introduce an XSS. Worth tightening even now: add `'` to both escape maps.

## Technical notes

```python
# web/build.py:73-78 - autoescape config (correct)
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

```html
<!-- web/templates/inmate.html:18-29 - JSON-LD with HTML-escaped string interpolation -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person",
 "name":"{{ inmate.full_name }}",
 {% if inmate.sex %}"gender":"{{ expand_sex(inmate.sex) }}",{% endif %}
 "identifier":[{"@type":"PropertyValue","name":"HCSO inmate number","value":"{{ inmate.inmate_number }}"},
               {"@type":"PropertyValue","name":"HCSO booking number","value":"{{ inmate.booking_number }}"}],
 "subjectOf":{"@type":"WebPage","name":"Hamilton County Justice Center booking record",
   "url":"https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id={{ inmate.inmate_number }}",
   "dateCreated":"{{ inmate.booking_date }}",
   ...}}
</script>
```

```html
<!-- proposed inmate.html JSON-LD patch using | tojson -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person",
 "name": {{ inmate.full_name | tojson }},
 {% if inmate.sex %}"gender": {{ expand_sex(inmate.sex) | tojson }},{% endif %}
 "identifier":[{"@type":"PropertyValue","name":"HCSO inmate number","value": {{ inmate.inmate_number | tojson }}},
               {"@type":"PropertyValue","name":"HCSO booking number","value": {{ inmate.booking_number | tojson }}}],
 "subjectOf":{"@type":"WebPage","name":"Hamilton County Justice Center booking record",
   "url": {{ ("https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id=" ~ inmate.inmate_number) | tojson }},
   "dateCreated": {{ inmate.booking_date | tojson }},
   "isAccessibleForFree":true,
   "license":"https://codes.ohio.gov/ohio-revised-code/section-149.43"}}
</script>
```

```javascript
// web/templates/base.html:246 - esc() escapes & < > " but NOT '
function esc(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c];
  });
}
// web/templates/base.html:135 - escTip() escapes only & < >
function escTip(s) {
  return String(s).replace(/[&<>]/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;'})[c];
  });
}
```

```javascript
// proposed: extend both escape maps to cover single quotes
function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
  });
}
// (and add "'":'&#39;' to escTip's map, with regex /[&<>']/g)
```

```python
# scraper/parsers.py:17, 55 - list-side inmate_number is digits only
_DETAIL_ID = re.compile(r"[?&]id=(\d+)")
# scraper/parsers.py:77 - but bio override is unconstrained text
inmate_number=bio.get("Inmate Number") or inmate_number,
# scraper/sweep.py:270 - photo path is derived from inmate_number
photo_path = PHOTOS_DIR / f"{inm.inmate_number}.jpg"
```

```python
# proposed: pydantic validator on Inmate.inmate_number
from pydantic import BaseModel, Field, field_validator

class Inmate(BaseModel):
    inmate_number: str

    @field_validator("inmate_number")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        v = (v or "").strip()
        if not v.isdigit():
            raise ValueError(f"inmate_number must be digits, got {v!r}")
        return v
```

```html
<!-- web/templates/_card.html:7 - card_tip emitted into data-tip attribute -->
<span class="tier tier-{{ tier.kind }} tier-corner" tabindex="0"
      aria-label="{{ tier.label }} ..." data-tip="{{ card_tip(inm) }}">
  {{ tier.short }}
</span>
<!-- base.html:138-143 then reads data-tip and renders each line via escTip(). -->
```

## Findings

### tpl-sec-F1 - JSON-LD interpolates scraped strings without JSON escaping
- Severity: medium
- Confidence: high
- Template: web/templates/inmate.html:18-29
- Sink: `<script type="application/ld+json">` body. Five fields (`inmate.full_name`, `expand_sex(inmate.sex)`, `inmate.inmate_number`, `inmate.booking_number`, `inmate.booking_date`) are dropped inside JSON string literals using HTML-only escaping. A quote, backslash, control character, or literal `</script>` substring corrupts the JSON or, in the worst case, ends the script context.

### tpl-sec-F2 - `esc()` and `escTip()` do not escape single quotes
- Severity: low
- Confidence: high
- Template: web/templates/base.html:135, 246
- Sink: `tip.innerHTML` and `sresults.innerHTML`. Current literals only use double-quoted attributes, so the gap is latent today. If a future contributor switches an attribute to single-quoted, every interpolated field becomes injectable.

### tpl-sec-F3 - `inmate_number` is not validated, but is used in URLs and filenames
- Severity: low
- Confidence: high
- Template: web/templates/_card.html:10, web/templates/inmate.html:69, 70, 178; consumed by all `data-photo` and href values.
- Sink: `<a href>`, `<img src>`, `data-photo`. Autoescape blocks attribute breakouts, but a malformed bio-table override (parsers.py:77) could produce a value containing `..` or `/`, yielding a path-traversal-shaped URL under `/photos/`. Not an XSS, but a defensive cliff away from one if any template ever inlines this value into JS.

### tpl-sec-F4 - Giscus widget origin not pinned in template comment
- Severity: informational
- Confidence: high
- Template: web/templates/inmate.html:202-216
- Sink: dynamically inserted `<script src="https://giscus.app/client.js" ...>`. Today the attributes come from env-supplied build globals (build.py:90-95) and are autoescaped. No security gap, but no in-template warning prevents a future contributor from accepting these values from a URL parameter.

### tpl-sec-F5 - RSS GUID is not stable per record across feed regenerations
- Severity: informational
- Confidence: medium
- Template: web/templates/feed.xml:13
- Sink: `<guid isPermaLink="false">{{ e.event }}-{{ e.inmate_number }}-{{ e.timestamp_utc }}</guid>`. Not a security issue, but unstable GUIDs can be confused with feed-poisoning. Out of scope for tpl-sec; flagged for completeness.

## Recommendations

### tpl-sec-F1 - Switch JSON-LD interpolations to `| tojson`
Replace the five `"key":"{{ value }}"` patterns in inmate.html:18-29 with `"key": {{ value | tojson }}`. Jinja's `tojson` calls `htmlsafe_json_dumps`, which JSON-escapes quotes/backslashes/control chars AND HTML-escapes `<`, `>`, `&`, `'` inside the JSON string so a `</script>` substring cannot end the script context. base.html:85 already follows this pattern for `ROOT`.

### tpl-sec-F2 - Add single-quote to both JS escape maps
Update the regex in `esc()` to `/[&<>"']/g` and add `"'":'&#39;'` to the map (base.html:246). Mirror in `escTip()` (base.html:135) with regex `/[&<>']/g`. Two-line change each, no behavior change for today's literals, future-proofs against attribute-style regressions.

### tpl-sec-F3 - Add a Pydantic validator on `Inmate.inmate_number`
In scraper/models.py, add `@field_validator("inmate_number")` requiring `v.isdigit()`. This fails closed at parse time rather than letting a malformed bio-table override leak through to `photo_filename` and template URLs. Also add a unit test that feeds the validator a value containing `..` or `/` and asserts ValueError.

### tpl-sec-F4 - Document the Giscus attribute provenance in the template
Add a Jinja comment `{# Giscus attrs come from build-time env vars (JCSTREAM_GISCUS_*); never accept these from URL params or user input. #}` immediately above the `{% if giscus.repo_id %}` block in inmate.html:202.

### tpl-sec-F5 - Stabilize the RSS GUID (informational, defer)
Replace `{{ e.event }}-{{ e.inmate_number }}-{{ e.timestamp_utc }}` with something hash-stable per event (e.g. a SHA-1 of `event|inmate_number|timestamp`). Out of scope for security; punt.

## Remediation plan

1. Patch JSON-LD escaping
   - Touches: web/templates/inmate.html
   - Verification: `python -m web.build` against the current `data/current.json`; run any `inmate/*/index.html` through a JSON-LD validator (https://validator.schema.org/) for one synthetic name with a quote in it; `python -m pytest -q` stays green.
   - Duration: 10 minutes
   - Rollback: revert the single template hunk

2. Tighten JS escape maps
   - Touches: web/templates/base.html (two helper functions)
   - Verification: rebuild, browse the homepage type-ahead with a name containing `'`, hover a tier badge with `'` in the ORC title.
   - Duration: 5 minutes
   - Rollback: revert the two regex+map literals

3. Add `inmate_number` validator
   - Touches: scraper/models.py, plus one new test in tests/
   - Verification: `python -m pytest -q` shows the new test green; existing 102 tests stay green; a synthetic malformed bio override raises ValueError.
   - Duration: 20 minutes
   - Rollback: drop the validator and its test

4. Add Giscus provenance comment
   - Touches: web/templates/inmate.html (single Jinja comment)
   - Verification: rebuild, `diff -u` shows comment-only delta in rendered HTML.
   - Duration: 2 minutes
   - Rollback: delete the comment

5. (Deferred) Stabilize RSS GUID
   - Touches: web/templates/feed.xml, possibly build.py to precompute a hash
   - Verification: RSS validator (https://validator.w3.org/feed/) reports stable GUIDs across two consecutive builds.
   - Duration: 15 minutes
   - Rollback: revert the template change

## Cross-references

- Scraper parser robustness on `inmate_number` and `bio.get("Inmate Number")` - parsers.py:77; coordinate with the parser-robustness audit (the validator I propose for F3 belongs to that subagent's scope as much as mine).
- Photo-filename derivation and pruning safety - scraper/sweep.py:270-276; coordinate with the sweep-reliability audit; the validator in F3 would also harden their PHOTO_PRUNE_MAX_FRACTION path.
- Pydantic schema coverage for all scraped-string fields - data-integrity audit owns the broader story; F3 is a narrow slice.
- CSP via a meta tag (since GitHub Pages cannot set headers) was deliberately not flagged per skill guidance; if the owner wants a future hardening, the architecture audit would be the right home.

## Confidence and limitations

- Confidence is high that autoescape is on, `| safe` is absent, and the JSON-LD block uses raw interpolation. These are mechanical greps against the committed templates at commit 8355cc8 and were verified directly.
- Confidence is medium on the practical exploitability of F1. The 256-char `full_name` cap and `_split_name` logic in models.py:48 make `</script>` injection improbable today, but the fix is still strictly better and trivial.
- I did not run the build or render any templates; findings are static. Verifying F1 with a real malformed name requires synthesizing a snapshot row, which is out of scope for read-only.
- I read scraper/courtclerk.py to confirm `case_summary_url` percent-encodes its argument (urllib.parse.quote with `safe=''`). It does. No finding there.
- I assumed the comment in CLAUDE.md about `JCSTREAM_SITE_BASE_URL` and `JCSTREAM_CNAME` being workflow-supplied is accurate; I did not validate the workflow YAML.

End of report.
