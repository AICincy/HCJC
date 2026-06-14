# gov - HTML Content Governance Audit

## Audit metadata
- Skill: jcstream-html-content-governance
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 9 (web/templates/base.html 257, web/templates/index.html 310, web/templates/inmate.html 224, web/templates/data.html 112, web/templates/stats.html 105, web/templates/_card.html 21, README.md 197, LICENSE 21, CLAUDE.md 63, wiki/Legal.md 75)
- Time: 2026-05-14T01:42:12Z

## Observations
- Required-statements matrix is mostly populated. base.html footer carries the FCRA notice and the independent-project disclaimer, and `noindex, noarchive` plus a site-level OG card. No per-page OG override exists (grep of `og:image` / `og:title` / `og:description` finds two hits, both in base.html).
- Presumption-of-innocence phrasing has three slightly different variants across templates. index.html banner says "legally presumed innocent unless and until proven guilty in a court of law"; inmate.html hero alert says "legally presumed innocent" (no full clause); stats.html alert frames it as "All charges are accusations only" plus "No person reflected in these counts has been convicted"; data.html mirrors the index banner long form. The ideas align but the canonical sentence is not used verbatim.
- ORC § 2953.32 "as amended" qualifier is present on index.html, inmate.html, and data.html. data.html goes further and names the amending acts (135th G.A. HB 234 and 136th G.A. HB 96). Consistency on the "as amended" hedge is good.
- The JSON-LD block in inmate.html (lines 18-29) declares `"license":"https://codes.ohio.gov/ohio-revised-code/section-149.43"`. The human-readable footer on the same page (line 181) declares the JCStream-published record under CC BY-NC 4.0. The two fields are talking past each other: the JSON-LD license is the source-record authority, not the JCStream republication license.
- JSON-LD `"dateCreated":"{{ inmate.booking_date }}"` is unguarded. `booking_date` is a parser string; when it is absent the rendered tag becomes `"dateCreated":""`, which is not valid Schema.org and reads as a malformed Person record to crawlers that do honor JSON-LD despite noindex.
- "There is never a fee" appears on index.html banner, data.html "no fees" section, and the About-JCStream collapsed block on index.html. inmate.html attribution line says "no fee" (lowercase, terser) and the hero alert says "at no cost". The promise is present everywhere it should be; the wording varies.
- Removal-request channel: every template that mentions removal links to `https://github.com/AICincy/JCStream/issues`. Display text varies: index banner shows `github.com/AICincy/JCStream` (no /issues suffix in visible text); inmate hero shows the same; data.html shows the same; the About-JCStream block on index.html shows `github.com/AICincy/JCStream/issues`. The link target is consistent; only the visible label drifts.
- CC BY-NC 4.0 is asserted on inmate.html (footer line 181) and README.md only. base.html footer says "the underlying public-records data is governed by Ohio law" and does not name the CC BY-NC 4.0 license. data.html non-affiliation section names MIT but is silent on CC BY-NC 4.0. The data-license posture is not visible on the homepage at all.
- The `/data/#legal` anchor exists in data.html (line 57, `<h2 id="legal" class="legal-anchor">Legal notices</h2>`). The section that follows covers all five required statements plus purpose, no-fees, and non-affiliation. The "Full legal notices ->" promise on the homepage is met.
- Comment policy on inmate.html (lines 186-201) is rendered unconditionally and lists the four categories from the skill brief. It matches wiki/Legal.md's "public commentary" section closely. No drift here.

## Analysis

The legal posture across templates is internally coherent and the right statements appear in the right places. The owner has done the work. The remaining issues are wording-drift and one substantive Schema.org bug, not gaps in coverage.

The single highest-value fix is the Schema.org `license` field. The current value points at the Ohio statute that authorizes the underlying public record. The JCStream republication is the JCStream-published derivative; the `license` predicate on the WebPage subject describes the license of the WebPage, not the license of the underlying authority. Crawlers that ingest JSON-LD will currently attribute the JCStream page to ORC 149.43 rather than CC BY-NC 4.0, which is both a factual misstatement and a quiet self-contradiction with the human-readable footer. The fix is small: change `license` to the CC BY-NC 4.0 URL and add a sibling `isBasedOn` (or move the codes.ohio.gov URL onto a `creativeWorkStatus` / `usageInfo` field) pointing at the HCSO source authority.

The presumption-of-innocence drift is low-risk but real. The full sentence on index.html ("legally presumed innocent unless and until proven guilty in a court of law") is the strongest formulation. The inmate.html hero compresses to "legally presumed innocent" without the "unless and until proven guilty" trailer. The compressed form is still legally accurate, but a canonical, single sentence reused verbatim makes the policy defensible against any "you say it different ways on different pages" complaint. Pick the long form and reuse it.

The "no fee" promise is present everywhere required, but appears in three surface forms ("there is never a fee", "at no cost", "no fee"). All are truthful; only "there is never a fee, and there never will be" (the data.html and About block form) commits to the future. The inmate.html attribution line "no fee" is the weakest variant. Strengthening it costs no risk and reinforces the homepage promise on every detail page.

The CC BY-NC 4.0 data license is asserted on inmate detail pages and in README, but not on the homepage, base.html footer, or data.html non-affiliation section. The non-affiliation section names MIT for code, then says "the underlying public-records data is governed by Ohio law" without acknowledging that the JCStream arrangement of that data carries the CC BY-NC 4.0 license. This is an asymmetric license claim: the project asserts CC BY-NC on inmate pages but does not assert it where the project as a whole is documented. Either drop the CC BY-NC claim from inmate.html (and document the rationale) or add it to data.html and base.html footer. Adding it is the lower-risk choice.

The `dateCreated:""` failure mode is a small parser-robustness leak that the html-content-governance lens catches because it touches the JSON-LD a crawler sees. The current parser does not always populate `booking_date`. When it doesn't, the published JSON-LD is technically malformed. The fix is a Jinja `{% if inmate.booking_date %}` guard around the `dateCreated` line, or omitting the WebPage object when the date is missing.

The Open Graph posture is exactly what CLAUDE.md describes: site-level `og:title`, `og:description`, `og:url`, plus `twitter:card=summary`. No per-page override exists. The template comment in base.html (lines 13-15) documents the rationale. Nothing to change.

The `noindex, noarchive` posture is correctly applied in base.html (line 10) and is inherited by every page. The template comment (lines 7-9) cites ORC § 2953.32 as the rationale. Aligned.

The comment policy on inmate.html is the most carefully written block in the codebase. It matches wiki/Legal.md's posture, is rendered unconditionally (so the policy is visible even when Giscus is disabled), and lists every category the skill brief calls out. No change recommended.

## Technical notes

```html
<!-- base.html, line 10: noindex posture, correctly inherited site-wide -->
<meta name="robots" content="noindex, noarchive">
```

```html
<!-- inmate.html, lines 24-28: JSON-LD license field misattributes the
     JCStream-published page to the source authority rather than to
     CC BY-NC 4.0 (the human-readable footer's actual claim). -->
"subjectOf":{"@type":"WebPage","name":"Hamilton County Justice Center booking record",
   "url":"https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id={{ inmate.inmate_number }}",
   "dateCreated":"{{ inmate.booking_date }}",
   "isAccessibleForFree":true,
   "license":"https://codes.ohio.gov/ohio-revised-code/section-149.43"}
```

```html
<!-- inmate.html, line 26: dateCreated is unguarded; renders as
     "dateCreated":"" when booking_date is missing. -->
"dateCreated":"{{ inmate.booking_date }}"
```

```html
<!-- index.html, line 6: canonical (long-form) presumption sentence. -->
<strong>Arrest is not conviction.</strong> Everyone listed here is
<strong>legally presumed innocent</strong> unless and until proven guilty in a
court of law.
```

```html
<!-- inmate.html, line 38: compressed presumption sentence; drops the
     "unless and until proven guilty in a court of law" trailer. -->
<p class="alert"><strong>This individual is legally presumed innocent.</strong>
The charges below are accusations only and are not evidence of guilt.</p>
```

```html
<!-- inmate.html, line 39: "at no cost". Compare to index.html line 8
     "there is never a fee", data.html lines 79-80 "there is never a fee,
     and there never will be", and inmate.html line 183 "no fee". -->
open an issue at <a href="https://github.com/AICincy/JCStream/issues">github.com/AICincy/JCStream</a>
&mdash; at no cost.
```

```html
<!-- inmate.html, line 181: CC BY-NC 4.0 claim. This claim is absent from
     base.html footer (line 60) and from data.html non-affiliation
     (lines 104-109). -->
Record data licensed <a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="license noopener" target="_blank">CC&nbsp;BY-NC&nbsp;4.0</a>
```

```html
<!-- data.html, line 57: anchor target referenced from index.html and
     inmate.html. Section is comprehensive; cross-link integrity OK. -->
<h2 id="legal" class="legal-anchor">Legal notices</h2>
```

```html
<!-- base.html, lines 18-19: site-level Open Graph card; no per-page
     override anywhere. twitter:card is summary (small card). -->
<meta property="og:title" content="JCStream - Hamilton County, OH Justice Center roster mirror">
<meta property="og:description" content="...">
<meta name="twitter:card" content="summary">
```

```html
<!-- data.html, lines 75-77: ORC 2953.32 "as amended" cite that names
     the amending acts. Strongest form of the citation in the codebase. -->
<a href="https://codes.ohio.gov/ohio-revised-code/section-2953.32">ORC &sect; 2953.32</a>
(as amended &mdash; including changes by 135th G.A. HB 234 and 136th G.A. HB 96)
```

## Required-statements matrix (filled)

| Template | Presumed innocent | ORC 149.43 cite | Removal protocol | Never a fee | FCRA disclaimer | Independent project | noindex meta |
|---|---|---|---|---|---|---|---|
| base.html (footer) | n/a | implicit ("Ohio law") | n/a | n/a | YES (line 60) | YES (line 60) | YES (line 10) |
| index.html | YES (banner line 6, long form) | YES (line 7) | YES (line 8) | YES (line 8 + line 210) | YES (line 8) | YES (line 7) | inherited |
| inmate.html | YES (hero line 38, compressed) | YES (line 39, line 72) | YES (line 39) | weak ("at no cost" line 39, "no fee" line 183) | YES (line 39) | inherited via base | inherited |
| stats.html | partial (line 11, indirect: "all charges are accusations") | absent | absent | absent | absent | inherited via base | inherited |
| data.html | YES (section line 60) | YES (line 68) | YES (lines 72-81) | YES (lines 79-80, 97-101) | YES (lines 84-88) | YES (lines 104-109) | inherited |

## Findings

### gov-F1. JSON-LD `license` misattributes the page to the source authority - severity high, confidence high
- Templates: web/templates/inmate.html lines 24-28
- The Schema.org `license` predicate on the WebPage describes the license of the WebPage, not the legal authority that authorized the underlying public record. Current value points at codes.ohio.gov section 149.43, contradicting the human-readable CC BY-NC 4.0 claim five lines later.
- Why it matters: factual self-contradiction in machine-readable metadata, attributable to JCStream by any crawler that ingests JSON-LD (which many do regardless of noindex).

### gov-F2. JSON-LD `dateCreated` is unguarded and can emit `""` - severity medium, confidence high
- Templates: web/templates/inmate.html line 26
- When `inmate.booking_date` is missing or empty the rendered output is `"dateCreated":""`, which is not valid Schema.org.
- Why it matters: malformed structured data is silently quality-degrading; on a Person/WebPage about a presumed-innocent individual the project should not be emitting broken metadata.

### gov-F3. Presumption-of-innocence phrasing drifts across templates - severity medium, confidence high
- Templates: index.html line 6 (long form), inmate.html line 38 (compressed), stats.html line 11 (indirect), data.html line 60 (full).
- The four variants are all legally accurate, but no single sentence appears verbatim in all four required places.
- Why it matters: defensibility. A canonical sentence, reused verbatim, is easier to point at when challenged.

### gov-F4. CC BY-NC 4.0 data license claim is asymmetric across templates - severity medium, confidence high
- Templates: asserted on inmate.html line 181 and README.md line 191; absent from base.html footer line 60, absent from data.html non-affiliation section lines 104-109.
- base.html footer instead says "the underlying public-records data is governed by Ohio law", which is about source-record authority, not about JCStream's republication license.
- Why it matters: the project asserts a republication license on inmate pages while not asserting it where the project as a whole documents its licensing. Either drop the claim from inmate.html or add it everywhere it belongs.

### gov-F5. "Never a fee" promise drifts to weaker forms on detail pages - severity low, confidence high
- Templates: index.html line 8 "there is never a fee"; index.html line 210 "no exceptions"; data.html lines 79-80 "there is never a fee, and there never will be"; inmate.html line 39 "at no cost"; inmate.html line 183 "no fee".
- Why it matters: the homepage promise is unconditional and future-tense; the detail page versions are terser and not future-tense. Verbatim reuse of the canonical promise on the detail page costs nothing.

### gov-F6. stats.html lacks an ORC 149.43 cite and a removal-protocol link - severity low, confidence high
- Templates: web/templates/stats.html lines 1-105
- The page aggregates roster-level facts but does not name the legal authority for publishing them or the removal channel. The presumption framing on line 11 is solid; the cite and the removal channel are absent.
- Why it matters: someone hitting /stats/ as their first page gets the disclaimer but no path to the legal section or to a removal request.

### gov-F7. Removal-link visible label drifts (target is consistent) - severity low, confidence high
- Templates: index.html line 8 ("github.com/AICincy/JCStream"); inmate.html line 39 ("github.com/AICincy/JCStream"); index.html line 210 ("github.com/AICincy/JCStream/issues"); inmate.html line 183 ("report an error or request removal").
- Why it matters: cosmetic only. The href targets are all `/issues`. Visible label could be the same everywhere for trust.

### gov-F8. ORC 2953.32 "as amended" hedge is strong on data.html but plainer elsewhere - severity low, confidence medium
- Templates: data.html lines 75-77 names the amending acts (135th G.A. HB 234, 136th G.A. HB 96); index.html line 8 and inmate.html line 39 say "as amended" without naming acts.
- Why it matters: the data.html form is the strongest hedge in the codebase against citation-currency staleness. The shorter forms remain defensible as long as "as amended" is present, which it is. ORC citation currency against current Ohio law is unverified - live source out of scope.

## Recommendations (exact wording)

R1 - inmate.html JSON-LD: change the WebPage object to attribute the JCStream-published page to CC BY-NC 4.0 and use `isBasedOn` for the HCSO source. Before/after:

Before (lines 24-28):
```
"subjectOf":{"@type":"WebPage","name":"Hamilton County Justice Center booking record",
   "url":"https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id={{ inmate.inmate_number }}",
   "dateCreated":"{{ inmate.booking_date }}",
   "isAccessibleForFree":true,
   "license":"https://codes.ohio.gov/ohio-revised-code/section-149.43"}
```

After:
```
"subjectOf":{"@type":"WebPage","name":"JCStream record page",
   "url":"{{ site_url }}/inmate/{{ inmate.inmate_number }}/",
   {% if inmate.booking_date %}"dateCreated":"{{ inmate.booking_date }}",{% endif %}
   "isAccessibleForFree":true,
   "license":"https://creativecommons.org/licenses/by-nc/4.0/",
   "isBasedOn":{"@type":"WebPage",
     "name":"Hamilton County Justice Center booking record (HCSO source)",
     "url":"https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id={{ inmate.inmate_number }}",
     "license":"https://codes.ohio.gov/ohio-revised-code/section-149.43"}}
```

R2 - canonical presumption sentence: adopt the index.html line 6 long form everywhere the presumption appears. Inmate hero alert (inmate.html line 38) becomes:

```
<p class="alert"><strong>Arrest is not conviction.</strong> This individual is
legally presumed innocent unless and until proven guilty in a court of law. The
charges below are accusations only and are not evidence of guilt.</p>
```

stats.html line 11 becomes:

```
<p class="alert"><strong>Arrest is not conviction.</strong> Every person reflected
in these counts is legally presumed innocent unless and until proven guilty in a
court of law. All charges are accusations only; these are point-in-time figures
for the current roster.</p>
```

R3 - canonical "never a fee" promise: use the data.html line 79 form everywhere. Inmate.html line 39 becomes:

```
... open an issue at <a href="https://github.com/AICincy/JCStream/issues">github.com/AICincy/JCStream/issues</a>.
<strong>There is never a fee, and there never will be.</strong>
```

Inmate.html line 183 becomes:

```
<a href="https://github.com/AICincy/JCStream/issues">report an error or request removal &mdash; there is never a fee</a>
```

R4 - CC BY-NC 4.0 alignment: either drop the inmate.html footer claim, or add the same claim to base.html footer and data.html non-affiliation section. Recommended: add. base.html line 60 becomes:

```
... Source code is MIT-licensed; the JCStream-arranged record data is licensed
<a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="license">CC&nbsp;BY-NC&nbsp;4.0</a>;
the underlying public records are governed by Ohio law.
```

data.html non-affiliation paragraph (lines 104-109) gains a final sentence:

```
The JCStream-arranged record data is licensed
<a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="license">CC&nbsp;BY-NC&nbsp;4.0</a>;
the underlying public records remain governed by Ohio law and carry no JCStream
license claim.
```

R5 - stats.html legal footer block: append a short paragraph after line 103 with the ORC 149.43 cite and the removal channel:

```
<p class="muted">These counts derive from public records published by HCSO under
the Ohio Public Records Act, <a href="https://codes.ohio.gov/ohio-revised-code/section-149.43">ORC &sect; 149.43</a>.
To request correction or removal of any record reflected here, open an issue at
<a href="https://github.com/AICincy/JCStream/issues">github.com/AICincy/JCStream/issues</a>.
There is never a fee. <a href="{{ base_url }}/data/#legal">Full legal notices &rarr;</a></p>
```

R6 - removal-link label consistency: every visible link label for the removal channel should read `github.com/AICincy/JCStream/issues` (matching href). This is a one-line edit in index.html line 8 and inmate.html line 39.

## Remediation plan

1. Patch inmate.html JSON-LD per R1 (high severity, smallest surface, biggest defensibility win). Snapshot a rendered detail page through a JSON-LD validator after the change.
2. Apply canonical presumption sentence per R2 to inmate.html hero and stats.html alert. No CSS impact.
3. Apply canonical "never a fee" promise per R3 to inmate.html hero and attribution line. No CSS impact.
4. Add CC BY-NC 4.0 to base.html footer and data.html non-affiliation paragraph per R4. Pytest baseline already covers template rendering; rerun.
5. Add the stats.html legal footer paragraph per R5 and align removal-link labels per R6.

## Cross-references
- The JSON-LD `dateCreated` empty-string emission (gov-F2) overlaps with parser-robustness territory (booking_date null safety). Cross-scope: jcstream-python-parser-robustness.
- The visible-label "open in same tab vs new tab" question on legal links is mostly already settled (ORC and removal links use no `target="_blank"`; courtclerk and creativecommons links open in new tab with `rel="noopener"`). Accessibility implications cross-scope: jcstream-html-accessibility.
- Currency of ORC 2953.32 against current Ohio law cannot be verified live (no outbound network). Cross-scope: an authority-currency review against codes.ohio.gov when network is available. Marked unverified - live source out of scope.

## Confidence and limitations
- High confidence on all findings: every claim is supported by an exact line in the templates as quoted.
- ORC citation currency: unverified - live source out of scope. The "as amended" hedge is present everywhere required, so currency drift is mitigated.
- Schema.org `license` semantics interpretation follows schema.org/CreativeWork and schema.org/WebPage definitions; recommendation R1 is consistent with those definitions but a Schema.org validator pass against a rendered page is the final check before shipping.
- Did not read sibling audit reports (per scope). If parser-robustness audit independently flags `booking_date` null safety, gov-F2 should be folded into that fix.

End of report.
