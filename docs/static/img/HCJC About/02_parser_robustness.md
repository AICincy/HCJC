# parser - Parser Robustness Audit

## Audit metadata
- Skill: jcstream-python-parser-robustness
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 4
  - scraper/parsers.py (208 lines)
  - scraper/sweep.py (355 lines, parser call sites only)
  - scraper/models.py (80 lines, context)
  - tests/test_parsers.py (51 lines, context)
- Time: 2026-05-14T01:41:42Z

## Observations
1. parsers.py:113, `_parse_name` requires three conjunctive properties on the heading text: it must live in `h1`/`h2`/`h3`, contain a comma, and satisfy `text.upper() == text`. A single property drifting (e.g., title-case rendering) zeroes detail-side names.
2. parsers.py:148-150, charge ingestion gates each row on `description or orc` after `cells = {c.attributes.get("label", ""): _text(c) ...}`. The labels `"Description"` and `"ORC Code"` are literal; a rename to `"Charge Description"` or `"ORC"` drops every charge.
3. parsers.py:185-191, `_extract_inline_photo` keys on the literal substring `"274px" in style` and the `src.startswith("data:")` test. A width tweak (e.g., 280px) yields zero photos site-wide; the only signal is the 50% watchdog.
4. parsers.py:17, `_DETAIL_ID = re.compile(r"[?&]id=(\d+)")` only matches query-string IDs. A WordPress permalink shift to `/inmate/12345/` makes every list row id-less and the row gets skipped at parsers.py:38-40.
5. parsers.py:20, `_BIO_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$")` accepts only ASCII letters and spaces in labels. A label with `#`, hyphen, or digit (e.g., `"Class #"`) is silently dropped from the bio dict.
6. parsers.py:142, `_parse_charges` runs `tree.css("tr")` globally with no section scoping. If HCSO ever adds another labeled table on the detail page (e.g., a holds/warrants table), false-positive `Charge` rows can appear unless they happen to lack both `Description` and `ORC Code`.
7. parsers.py:192-199, the decode failure path returns `None` without distinguishing "no candidate img found" from "candidate img found but base64 decoded to garbage". Both look identical to the watchdog at sweep.py:199-204.
8. parsers.py:113, `text.upper() == text` would mistakenly accept a value that is fully numeric or punctuation-only (e.g., `","` alone or a comma-bearing footer caption) because those equal their uppercase form. Selection then leaks into `_split_name` as `("","","")` or stranger.
9. parsers.py:178-200 returns `None` even for the validate=False base64 path; HCSO declaring `image/png` but serving JPEG bytes is documented at line 182 but never verified. A future cutover serving a real PNG would still parse, but no marker check means a 1-byte truncated payload still passes through to `downscale_and_save` (Pillow handles it, but the bug source is invisible).
10. sweep.py:262-268, the list-row name fallback fires only when `list_row is not None`. On `--refresh-known` re-fetches, the `row_by_id` map at sweep.py:124 is rebuilt from the current cycle's list sweep, so a detail-only stale id (carried forward from previous, no longer on any list page) would have `list_row=None` if it were ever re-fetched. Today `to_fetch` (sweep.py:107-112) only includes ids seen in `seen_ids`, so this is latent.

## Analysis

Obs 1, 8: `_parse_name` is the most brittle hot spot. The all-caps + comma + heading-tag conjunction is a fingerprint, not a contract. Three failure variants each silently zero the detail name: title-case heading, name moved into a `<span class="page-title">`, or name wrapped in mixed casing whitespace. The list-row fallback at sweep.py:262 saves new-booking pages, but `--refresh-known` runs and any future flow that re-fetches a detail without a same-cycle list row would not benefit. The name watchdog at sweep.py:193 trips at 70%, which is the right floor, but it triggers after the bad sweep has already been written. A tiered extractor (heading, `<meta property="og:title">`, `<title>`, list-row) with distinct debug breadcrumbs would let the owner see which tier saved the cycle.

Obs 2, 5: charge label drift is silent because the row gate at parsers.py:150 drops rows that lack both `Description` and `ORC Code`. The existing log warning at parsers.py:170 only fires when *every* charge is lost. A single column going dark (e.g., `"Bond Amount"` to `"Bond ($)"`) loses that field on every charge with no warning. Per-label coverage telemetry, gathered across a sweep and emitted via a sweep-end log when any high-prevalence label drops to zero, would catch this before downstream pages show empty bond columns.

Obs 3, 9: photo extraction shares the same brittleness style as the name heading. The 274px style hook is a heuristic; the right defensive posture is to keep it as the preferred selector and add a JPEG-SOI byte-marker check on any data-URI img as a fallback. The validate=False base64 decode at parsers.py:196 will accept padding-tolerant garbage; promoting decode failures to a WARNING (rather than a silent `None`) costs nothing.

Obs 4: `_DETAIL_ID`'s query-string assumption is reasonable today but cheap to harden. Adding a path-style alternative (`/inmate-detail/(\d+)`) preserves correctness across a WordPress permalink reshape that the watchdogs would not catch quickly: a permalink change zeroes `seen_ids`, hits `SWEEP_MIN_ROSTER_FRACTION` (0.5) and triggers `_sweep_looks_healthy` to refuse the write. That is *better* than a silent partial; still, the parser-side fix avoids the recovery wait.

Obs 6: scoping `_parse_charges` to a containing section (search for an ancestor heading text containing `"Charges"` or a wrapper with a class/id signal) would prevent future false positives. This is preventive, not active.

Obs 7: the decode-failed-vs-no-candidate ambiguity has a one-line fix at parsers.py:198 already (the existing WARNING). The real gap is the no-candidate case: when no img matches the 274px filter, `_extract_inline_photo` returns `None` silently. A separate breadcrumb at INFO level for "no candidate img matched 274px filter" would tell the owner which leg of the heuristic broke.

Obs 10: this one is latent under current sweep logic but worth a sentence: the `_fetch_one` fallback assumes a co-sweep list row. If the owner ever adds a path that refreshes detail pages outside the cycle (e.g., a backfill mode), the fallback evaporates. A note in the docstring is enough.

## Technical notes

```python
# parsers.py: tiered name extractor preserving current behavior as tier 1
def _parse_name(tree: HTMLParser) -> str:
    # Tier 1: existing LAST, FIRST all-caps heading
    for tag in ("h1", "h2", "h3"):
        for node in tree.css(tag):
            text = _text(node)
            if "," in text and text.upper() == text and any(c.isalpha() for c in text):
                return text.strip()
    # Tier 2: og:title meta
    for meta in tree.css('meta[property="og:title"]'):
        content = meta.attributes.get("content", "").strip()
        if "," in content and content.upper() == content and any(c.isalpha() for c in content):
            log.debug("name extracted from og:title fallback")
            return content
    # Tier 3: document <title>
    title = tree.css_first("title")
    if title:
        text = _text(title)
        if "," in text:
            log.debug("name extracted from <title> fallback")
            return text
    log.warning("inmate-detail name heading (LAST, FIRST all-caps) not found")
    return ""
```

```python
# parsers.py: alphabet guard on Obs 8
# Reject heading text that has no letters at all (e.g., punctuation lines)
if "," in text and text.upper() == text and any(c.isalpha() for c in text):
    return text.strip()
```

```python
# parsers.py: JPEG SOI fallback for inline photo
def _extract_inline_photo(tree: HTMLParser) -> bytes | None:
    candidates = []
    for img in tree.css("img"):
        src = img.attributes.get("src", "")
        if not src.startswith("data:"):
            continue
        header, _, payload = src.partition(",")
        if "base64" not in header or not payload:
            continue
        style = img.attributes.get("style", "")
        try:
            data = base64.b64decode(payload, validate=False)
        except (ValueError, base64.binascii.Error):
            log.warning("failed to base64-decode inline photo candidate")
            continue
        # Preferred: declared 274px width (HCSO's current style hook)
        if "274px" in style:
            return data
        # Fallback: JPEG SOI marker (HCSO declares image/png but serves JPEG)
        if data[:3] == b"\xff\xd8\xff":
            candidates.append(data)
    if candidates:
        log.info("inline photo matched JPEG-SOI fallback, not the 274px hook")
        return candidates[0]
    return None
```

```python
# parsers.py: defensive _DETAIL_ID alternatives
_DETAIL_ID = re.compile(r"(?:[?&]id=|/inmate-detail/)(\d+)")
```

```python
# parsers.py: relaxed _BIO_LINE allowing # and digits in labels
_BIO_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 #/_-]*?)\s*:\s*(.*?)\s*$")
```

```python
# parsers.py: per-label coverage telemetry
KNOWN_BIO_LABELS = {
    "Inmate Number", "Booking Number", "Date of Birth", "Sex", "Race",
    "Booking Date", "Projected Release Date", "Holder", "Holder Status",
}
KNOWN_CHARGE_LABELS = {
    "Description", "ORC Code", "Common Pleas Case #", "Municipal Case #",
    "Other Case #", "Court Date", "Bond Type", "Bond Amount",
    "Disposition", "Comments",
}

def parse_detail_page(html, inmate_number):
    tree = HTMLParser(html)
    bio = _parse_bio(tree)
    name = _parse_name(tree)
    charges = _parse_charges(tree)
    # Hand seen-label sets back via a sidecar log line per detail page;
    # the sweep aggregator can roll these up and warn on any expected
    # label whose presence rate fell below 50% across DETAIL_WATCHDOG_MIN_SAMPLE.
    log.debug(
        "labels seen id=%s bio=%s charge_keys=%s",
        inmate_number,
        sorted(bio.keys()),
        sorted({k for c in _raw_charge_rows(tree) for k in c.keys()}),
    )
    ...
```

```python
# parsers.py: distinguishing "no candidate" from "decode failed" at INFO
# Inside _extract_inline_photo's loop, after the for-loop falls through:
log.debug("no <img> with data: src and width:274px style found on detail page")
return None
```

```python
# sweep.py: scope hint for charge table (Obs 6) using selectolax
# When implementing, find a wrapper element like <section> or <div> whose
# heading or class names contain "charge", then run tree-scoped tr css from
# that node rather than from the global tree.
```

## Findings

### parser-F1. Name heading triple-conjunction is single-property-fragile
- Severity: high
- Confidence: high
- Code: scraper/parsers.py:107-120, `_parse_name`
- Symptom on the live site: detail-side `last_name` / `first_name` go empty on every detail page; site only shows names for new bookings rescued by the sweep.py list-row fallback. `--refresh-known` runs would publish nameless records.
- Watchdog today: catches at <70% via `DETAIL_WATCHDOG_NAME_FLOOR` after the cycle has already run.
- Cross-ref: Obs 1, 8.

### parser-F2. Charge labels are literal strings with no per-label drift detection
- Severity: high
- Confidence: high
- Code: scraper/parsers.py:148-168, `_parse_charges`
- Symptom: a rename of `"Description"` or `"ORC Code"` zeroes all charges; the existing warning at 170-174 fires only when *every* row is skipped. A single-column rename (e.g., `"Bond Amount"`) silently empties that field across the site.
- Watchdog today: no, list watchdog is unaffected; only full-charge-loss has any logging.
- Cross-ref: Obs 2, 5.

### parser-F3. Inline photo width hook lacks a byte-marker fallback
- Severity: high
- Confidence: high
- Code: scraper/parsers.py:178-200, `_extract_inline_photo`
- Symptom: HCSO changes the placeholder width (e.g., 280px) and all photos disappear site-wide.
- Watchdog today: yes, at <50% via `DETAIL_WATCHDOG_PHOTO_FLOOR`, after the cycle has run.
- Cross-ref: Obs 3, 7, 9.

### parser-F4. Detail-ID regex assumes query-string form
- Severity: medium
- Confidence: high
- Code: scraper/parsers.py:17, `_DETAIL_ID`
- Symptom: a WordPress permalink shift to `/inmate-detail/NNNN/` makes every list row id-less; rows get skipped at parsers.py:38-40. List sweep then collapses to zero, `_sweep_looks_healthy` refuses the write, last-good roster persists indefinitely until a parser fix ships.
- Watchdog today: yes, refuses the write but does not auto-recover.
- Cross-ref: Obs 4.

### parser-F5. Bio label regex rejects punctuation/digits in label names
- Severity: medium
- Confidence: medium
- Code: scraper/parsers.py:20, `_BIO_LINE`
- Symptom: an HCSO label addition like `"Class #"` or `"Cell-Block"` is silently absent from the bio dict; field appears empty downstream with no warning.
- Watchdog today: no.
- Cross-ref: Obs 5.

### parser-F6. Charge parser is globally scoped, vulnerable to future labeled tables
- Severity: low
- Confidence: medium
- Code: scraper/parsers.py:142, `_parse_charges`
- Symptom: latent. If HCSO adds a holds/warrants table with `label=`-attributed cells on the detail page, spurious `Charge` entries could appear (only blocked today by the `Description`/`ORC Code` gate at line 150).
- Watchdog today: no.
- Cross-ref: Obs 6.

### parser-F7. Photo helper conflates "no candidate" with "decode failed"
- Severity: low
- Confidence: high
- Code: scraper/parsers.py:185-200, `_extract_inline_photo`
- Symptom: when photos stop, the only log line is the watchdog summary at sweep.py:199-204; the owner can't tell from logs whether the 274px filter matched zero imgs or matched imgs whose base64 failed to decode.
- Watchdog today: yes, aggregate only.
- Cross-ref: Obs 7.

### parser-F8. Detail page that returns zero structured fields produces an empty Inmate without an INFO breadcrumb
- Severity: low
- Confidence: medium
- Code: scraper/parsers.py:75-91, `parse_detail_page`
- Symptom: when HCSO serves an error/interstitial page that still passes `raise_for_status()`, the parser yields an `Inmate` with empty bio, empty name, empty charges. The list-row fallback hides this in normal sweeps. No single log line says "structured-fields zero" for that id.
- Watchdog today: contributes to the name watchdog but is invisible per-record.
- Cross-ref: Obs 7.

## Recommendations

### parser-F1 -> tiered `_parse_name`
- File: scraper/parsers.py
- Function: `_parse_name`
- Before: single all-caps comma-heading scan.
- After: tier 1 = heading scan (current); tier 2 = `meta[property="og:title"]`; tier 3 = `<title>`; tier 4 = caller's list-row fallback (already at sweep.py:262). Each non-tier-1 success logs a debug breadcrumb. Add an `any(c.isalpha() for c in text)` guard to current tier 1 to fix Obs 8.
- Test impact: add `tests/fixtures/detail_titlecase_heading.html` and a pytest case asserting the og:title or title fallback produces the right name. Existing test_parsers.py cases remain green because tier 1 still matches.

### parser-F2 -> per-label coverage telemetry
- File: scraper/parsers.py (emit) and scraper/sweep.py (aggregate)
- Function: `_parse_bio`, `_parse_charges`, sweep `_check_detail_watchdog`
- Before: total-loss warning only.
- After: emit a per-detail debug line of label sets; sweep accumulates counts across the cycle and warns when any `KNOWN_BIO_LABELS` / `KNOWN_CHARGE_LABELS` member dropped to zero across at least `DETAIL_WATCHDOG_MIN_SAMPLE` detail attempts.
- Test impact: new `tests/test_sweep.py::test_label_coverage_warns_on_single_label_drift` using two synthetic detail dicts where `"Bond Amount"` is renamed.

### parser-F3 -> JPEG-SOI fallback
- File: scraper/parsers.py
- Function: `_extract_inline_photo`
- Before: 274px style is the only matcher.
- After: 274px stays the preferred match; on miss, return the first data-URI img whose base64 decodes to bytes starting `\xff\xd8\xff`. Log INFO when the fallback fires.
- Test impact: add `tests/fixtures/detail_alt_width_photo.html` with `width:280px`, asserting bytes still extract.

### parser-F4 -> path-form regex alternative
- File: scraper/parsers.py
- Function: `_DETAIL_ID`
- Before: `r"[?&]id=(\d+)"`.
- After: `r"(?:[?&]id=|/inmate-detail/)(\d+)"`.
- Test impact: extend `test_list_page_skips_rows_without_detail_link` with a row whose `<a href="/inmate-detail/14502205/">` is the only id source.

### parser-F5 -> relaxed `_BIO_LINE`
- File: scraper/parsers.py
- Function: `_BIO_LINE`
- Before: `r"^\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$"`.
- After: `r"^\s*([A-Za-z][A-Za-z0-9 #/_-]*?)\s*:\s*(.*?)\s*$"`.
- Test impact: add `test_parse_bio_accepts_label_with_hash` using a `<li>Class # : A</li>` snippet; existing cases remain green.

### parser-F6 -> scope charges to a containing section
- File: scraper/parsers.py
- Function: `_parse_charges`
- Before: `tree.css("tr")` global.
- After: locate a wrapper around the charges section (search headings for text containing `"Charges"` and run the tr scan only inside that node's parent table block). If no scope found, fall back to current behavior for safety.
- Test impact: add `tests/fixtures/detail_with_holds_table.html` containing a second labeled table; assert no spurious charges appear.

### parser-F7 -> separate breadcrumbs for no-candidate vs decode-failed
- File: scraper/parsers.py
- Function: `_extract_inline_photo`
- Before: silent `None` on no candidate; existing WARNING on decode failure (Obs 7 already partly addressed at line 198).
- After: add a debug-level "no candidate img matched 274px filter on detail page" log when the for-loop completes without returning.
- Test impact: log assertion in a new test, or leave un-asserted as a developer-facing breadcrumb.

### parser-F8 -> empty-parse INFO sentinel
- File: scraper/parsers.py
- Function: `parse_detail_page`
- Before: no per-id breadcrumb for fully empty parses.
- After: if `not bio and not name and not charges`, `log.info("detail page produced no structured fields for id=%s", inmate_number)`. Returns an empty Inmate as today.
- Test impact: small caplog assertion test using a near-empty HTML fixture.

## Remediation plan

1. parser-F4 + parser-F5 + parser-F7 + parser-F8 in one PR (no behavior change for current HCSO HTML; pure additive defense).
   - Touches: scraper/parsers.py (regex and log lines only).
   - Verification: existing pytest stays green; one new test for path-form id.
   - Duration: ~30 min.
   - Rollback: revert single commit.

2. parser-F1 tiered `_parse_name`.
   - Touches: scraper/parsers.py.
   - Verification: existing test_detail_page_extracts_bio_charges_and_inline_photo still passes via tier 1; new fixture for title-case heading exercises tier 2 or 3.
   - Duration: ~45 min.
   - Rollback: revert; sweep.py list-row fallback continues to cover new bookings.

3. parser-F3 JPEG-SOI fallback.
   - Touches: scraper/parsers.py.
   - Verification: existing photo test passes (still hits 274px branch); new fixture without 274px asserts bytes still emerge.
   - Duration: ~30 min.
   - Rollback: revert; `DETAIL_WATCHDOG_PHOTO_FLOOR` still catches future width drift.

4. parser-F2 per-label coverage telemetry.
   - Touches: scraper/parsers.py and scraper/sweep.py.
   - Verification: new sweep-level test with two synthetic detail label sets.
   - Duration: ~60 min.
   - Rollback: revert; the existing zero-charge warning at parsers.py:170 still exists.

5. parser-F6 scope charges parse (lowest priority; only run after 1-4 are stable).
   - Touches: scraper/parsers.py.
   - Verification: add `detail_with_holds_table.html` fixture and assert charge count unchanged.
   - Duration: ~45 min.
   - Rollback: revert; falls back to global tr scan.

Watchdog tuning: none of the above changes the baseline name or photo rates on healthy HCSO HTML, so `DETAIL_WATCHDOG_NAME_FLOOR=0.70` and `DETAIL_WATCHDOG_PHOTO_FLOOR=0.50` stay as-is. The tiered name extractor may raise the named-rate ceiling under drift, which is desirable; if anything, post-deployment the owner could *raise* the name floor to 0.85 after a month of green data because the fallback tiers should rarely fail simultaneously.

## Cross-references
- Detail-watchdog tuning, partial-write semantics, photo prune safety: out of scope here, see jcstream-python-sweep-reliability.
- `data/current.json` shape and changelog invariants when parsers degrade: see jcstream-python-data-integrity.
- HTTP client retry / TLS handling that feeds parsers: see jcstream-python-security-networking.
- Test fixtures and coverage gaps for parser failure modes: see jcstream-python-test-gap-analysis.
- Module-level coupling between parsers and sweep watchdog: see jcstream-python-architecture.

## Confidence and limitations
- Read fully: scraper/parsers.py, scraper/sweep.py, scraper/models.py, tests/test_parsers.py.
- Sampled: tests/fixtures/ filenames only.
- Skipped: client.py (HTTP layer, out of scope), photos.py (downscale), store.py (persistence). Their behavior is treated as black-box.
- Assumptions: HCSO continues to use the responsive-table `label=` attribute pattern; the project keeps selectolax. Both are documented project commitments.
- Live-access caveat: unverified - live source out of scope. Findings are HTML-shape based on the fixtures and inline comments in parsers.py (parsers.py:181-183 documents the JPEG-bytes-as-PNG quirk).

End of report.
