# tests - Test Gap Analysis

## Audit metadata
- Skill: jcstream-python-test-gap-analysis
- Commit: 8355cc81463433ecdc869685e1e16d652f662863
- Files scanned: 33 (tests/test_build.py 256, tests/test_cincy_open.py 28, tests/test_client.py 64, tests/test_courtclerk.py 30, tests/test_ingest_issue.py 85, tests/test_match.py 47, tests/test_models.py 19, tests/test_open_data.py 120, tests/test_orc.py 39, tests/test_parsers.py 51, tests/test_photos.py 31, tests/test_pra.py 65, tests/test_pra_send.py 117, tests/test_store.py 74, tests/test_sweep.py 56, tests/fixtures/detail_inmate.html, tests/fixtures/detail_no_photo.html, tests/fixtures/list_smith.html, scraper/sweep.py 355, scraper/parsers.py 208, scraper/store.py 150, scraper/client.py 110, scraper/photos.py 37, scraper/models.py 80, scraper/match.py 84, scraper/pra.py 118, scraper/pra_capias.py 127, scraper/pra_jms_vendor.py 132, scraper/cfs.py 89, scraper/cfs_pdi.py 78, scraper/incidents.py 76, scraper/shootings.py 76, scraper/cincy_open.py 56, scraper/ingest_issue.py 134, scraper/courtclerk.py 43, scraper/orc.py 89, web/build.py 1282, pyproject.toml)
- Time: 2026-05-14T01:43:48Z

## Observations
- Pytest baseline collects 102 tests; CLAUDE.md still says "currently 34 tests". Stale comment, not a defect.
- `web/build.py` is 1282 lines. `test_build.py` covers helpers (tier, bond, age, events window). The `build()` entrypoint itself, `_write_search_json`, `_write_well_known`, `_write_checksums`, `_render_*`, `_compute_stats`, and `_dispatch_points` have no direct tests.
- `scraper/sweep.py::run()` is exercised only at the `_sweep_looks_healthy` / `_prune_photos` helper level. `_check_detail_watchdog`, `_fetch_one` (name fallback, photo carry-forward), and `_sweep_list` parallel aggregation are untested.
- `scraper/parsers.py` private helpers `_split_name`, `_parse_name`, `_parse_charges` label-drift fallback, and `_extract_inline_photo` width gate have no direct tests. Existing parser tests assert on the assembled `Inmate` only.
- Boundary conditions of `_sweep_looks_healthy` are untested: failure ratio exactly 0.10, roster ratio exactly 0.5, `prev_count` exactly 50. Same for `_prune_photos` doomed fraction exactly 0.5 (code uses `>`, so 0.5 still prunes).
- PRA send tests skip header-injection defense entirely: a record with CR/LF in any envelope field is never tested. `EmailMessage` does set-time validation that should reject the line break, but there is no asserting test.
- Test fixtures contain real-seeming production names: KHAN, HAMMAD ALI; SMITH, JEFFREY; SMITH, MICOLE; SMITH, CHRISTOPHER. Per skill rule 5 these should be scrubbed to `DOE, JOHN` style. `detail_no_photo.html` already uses `DOE, JANE`.
- `scraper/store.py::diff` is partially covered. `_materially_changed` charge-order change (same content, different order) is not asserted; per the skill brief it should fire `updated` and that behaviour is undocumented.
- `scraper/client.py::make_client` env-var override (`JCSTREAM_BASE_URL`, `JCSTREAM_USER_AGENT`, `JCSTREAM_CRAWL_DELAY`) is not tested. Easy to regress in a refactor.
- No module is wholly uncovered: every scraper file has at least transitive coverage. The gap shape is depth, not breadth.

## Analysis

The suite has good breadth. Every module under `scraper/` has at least one direct test file or shared parametrised coverage through `test_open_data.py`. The four Cincinnati Open Data feeds (`cfs`, `cfs_pdi`, `incidents`, `shootings`) are covered via parametrised round-trip and fallback tests, which is the right shape for those near-identical modules. `test_client.py` correctly uses `httpx.MockTransport` so no network call happens. The PRA send paths are mocked at `smtplib.SMTP`. The `_sweep_looks_healthy` heuristic and the `_prune_photos` safety floor each get their boundary intent expressed in two named tests.

The risk concentration is depth in three modules: `sweep.py`, `parsers.py`, and `web/build.py`. In `sweep.py`, the watchdog and `_fetch_one` (the name fallback and photo carry-forward) are the exact paths the skill brief flags as "silent parser drift" and "mass photo loss". A regression there would publish nameless or photoless records without flipping any test red. In `parsers.py`, the private helpers carry the HTML-shape assumptions (uppercase comma heuristic, 274px style hook, `_BIO_LINE` regex). The existing tests assert the assembled `Inmate` against two fixtures, which is good as integration but does not pin down individual fallback branches. A drift in HCSO markup that quietly makes `_parse_name` always return `""` would still be caught by the list-row fallback in `_fetch_one`, masking the parser failure unless the watchdog fires; the watchdog has no tests, so the masking is silent in CI.

`web/build.py` is the largest single file and the test file for it has stayed strictly at the helper level. That is a reasonable design choice for now (E2E builds touch templates and disk), but several pure helpers near the top of the file remain untested: `_compute_stats` (median bond, photo coverage, days-in-custody summary), `_dispatch_points` (de-dup + truncation), `_write_search_json` (the `n`/`c`/`t` row shape), and `_resolve_base_url`/`_resolve_site_url` (env-var precedence). These are all stdlib-only, easy to unit-test, and ship as published output.

The PRA test surface is well thought out. `test_pra_send.py` distinguishes the STARTTLS (587) and implicit-TLS (465) paths and asserts login skip on missing credentials. The two gaps are header-injection defense (a defendant or window value with `\r\n` would otherwise reach `set_content` and could split headers if the build template ever surfaced one) and retry behavior. `EmailMessage` itself rejects line breaks in headers, but there is no test that asserts that protection, so a refactor that swapped to raw `sendmail` would silently regress.

Test isolation is good. `tmp_path` is used in `test_sweep.py::_prune_photos`, `test_store.py`, and `test_open_data.py`. `monkeypatch.setenv` / `delenv` is used for SMTP env. There is no test that writes under repo `data/`. `test_pra_send.py` makes the recorder list per-test (the docstring calls this out explicitly), avoiding cross-test bleed.

Fixture hygiene is the one concrete privacy concern. `detail_inmate.html` and `list_smith.html` carry surnames and first-name combinations that read like real HCSO bookings. The skill rule is to scrub them to `LAST=DOE FIRST=JOHN` style and add a fixture README. The data in question is public, but committing it as a test fixture perpetuates it past HCSO's removal lifecycle, which contradicts the no-archive policy in CLAUDE.md.

Lack of property-based testing (Hypothesis) is correctly out of scope. Coverage thresholds are also correctly absent; the suite optimises for green-on-green, not percent.

## Technical notes

```text
$ python -m pytest --collect-only -q | tail -1
102 tests collected in 0.20s
```

```python
# scraper/sweep.py - watchdog never asserted in tests
def _check_detail_watchdog(attempts: int, named: int, with_photo: int) -> None:
    if attempts < DETAIL_WATCHDOG_MIN_SAMPLE:
        return
    name_rate = named / attempts
    photo_rate = with_photo / attempts
    if name_rate < DETAIL_WATCHDOG_NAME_FLOOR: log.warning(...)
    if photo_rate < DETAIL_WATCHDOG_PHOTO_FLOOR: log.warning(...)
```

```python
# scraper/sweep.py - _prune_photos uses strict >, so doomed/total == 0.5 still prunes
if doomed and len(doomed) / len(existing) > PHOTO_PRUNE_MAX_FRACTION:
    return
```

```python
# scraper/parsers.py - _split_name; no test for "SMITH" (no comma), "SMITH JR, JOHN", or trailing space
def _split_name(formal: str) -> tuple[str, str, str]:
    if "," not in formal:
        return (formal.strip(), "", "")
    last, _, rest = formal.partition(",")
    parts = rest.strip().split()
    first = parts[0] if parts else ""
    middle = " ".join(parts[1:]) if len(parts) > 1 else ""
    return (last.strip(), first, middle)
```

```python
# scraper/parsers.py - 274px width gate; no test for an inmate page with the placeholder
# at a different width (regression mode if HCSO retags the style attr)
style = img.attributes.get("style", "")
if "274px" not in style:
    continue
```

```python
# scraper/store.py - _materially_changed; charge LIST equality is order-sensitive
keys = ("booking_number", "projected_release_date", "holder_status", "charges")
return any(getattr(a, k) != getattr(b, k) for k in keys)
```

```python
# scraper/client.py - make_client env override; untested
def make_client() -> HcsoClient:
    return HcsoClient(
        base_url=os.environ.get("JCSTREAM_BASE_URL", DEFAULT_BASE),
        user_agent=os.environ.get("JCSTREAM_USER_AGENT", DEFAULT_UA),
        crawl_delay=float(os.environ.get("JCSTREAM_CRAWL_DELAY", DEFAULT_CRAWL_DELAY)),
    )
```

```html
<!-- tests/fixtures/detail_inmate.html line 3 - real-seeming name -->
<h1>KHAN, HAMMAD ALI</h1>
```

```html
<!-- tests/fixtures/list_smith.html - real-seeming first names with SMITH -->
SMITH JEFFREY 7/4/24
SMITH MICOLE 3/15/25
SMITH CHRISTOPHER ...
```

## Findings

### tests-F1 - Watchdog branches in `_check_detail_watchdog` are not asserted
- Severity: High. Confidence: High.
- The watchdog is the only in-CI signal that HCSO detail-page markup has drifted (nameless or photoless records). It writes WARNING logs but has no test, so a refactor that mutes the warning would be invisible. The risk this guards (silent parser drift after HCSO JMS cutover) is exactly the scenario CLAUDE.md and the JMS-vendor PRA module call out.

### tests-F2 - `_fetch_one` name fallback + photo carry-forward is untested
- Severity: High. Confidence: High.
- The list-row name fallback and the on-disk photo carry-forward are the user-visible difference between "minor drift" and "site rendered blank cards". No test pins down that the fallback runs only when the detail-page heading is empty, or that a disk photo survives a detail-page page without an inline image.

### tests-F3 - `_split_name` and `_parse_name` heading-shape assumptions are unpinned
- Severity: Medium. Confidence: High.
- The all-caps comma heuristic is HCSO-specific. Edge cases `"SMITH"` (no comma), `"SMITH, "` (trailing space), `"SMITH JR, JOHN"` (suffix in last), and a mixed-case heading are not asserted. A heading drift that quietly returns empty would be masked by the (also untested) list-row fallback in `_fetch_one`.

### tests-F4 - Boundary cases of `_sweep_looks_healthy` and `_prune_photos` are off-by-one risks
- Severity: Medium. Confidence: High.
- `prev_count == 50` exactly (the bootstrap floor edge), failure fraction exactly 0.10, seen_count exactly 0.5 * prev_count, and prune doomed fraction exactly 0.5 each sit on a strict-inequality boundary. The current tests use comfortable margins (~19% failed, 500/1200 seen). A constant tweak could flip behavior with no failing test.

### tests-F5 - Fixtures embed real-seeming HCSO names
- Severity: Medium. Confidence: Medium.
- `detail_inmate.html` and `list_smith.html` carry names that look like production bookings (KHAN HAMMAD ALI, SMITH MICOLE, SMITH CHRISTOPHER, SMITH JEFFREY). Per skill rule 5, this contradicts JCStream's no-archive policy because git history pins them indefinitely. `detail_no_photo.html` already shows the right pattern with DOE JANE.

### tests-F6 - PRA header-injection defense is implicit, not asserted
- Severity: Medium. Confidence: High.
- `EmailMessage.__setitem__` raises on CR/LF in headers. No test asserts that protection. A refactor away from `EmailMessage` (e.g. raw `sendmail` with f-strings) would silently re-introduce header-splitting risk. Since the build is the only thing populating window strings, the risk is currently low, but the test is one line.

### tests-F7 - `_materially_changed` charge-order semantics are undocumented
- Severity: Low. Confidence: High.
- `getattr(a, "charges") != getattr(b, "charges")` is order-sensitive because Pydantic list equality is order-sensitive. A re-fetch where HCSO returns the same charges in a different order fires `updated`. The skill brief flags this as either "document or fix"; today there is neither a docstring nor a test.

### tests-F8 - `make_client` env-var override is untested
- Severity: Low. Confidence: High.
- A typo in any of `JCSTREAM_BASE_URL`, `JCSTREAM_USER_AGENT`, `JCSTREAM_CRAWL_DELAY` would silently fall back to default. The factory is the seam between local dev and CI, exactly where regressions are easy.

## Recommendations

### R1 (-> tests-F1). Watchdog log assertions
Add three pytest functions in `tests/test_sweep.py`:
- `test_watchdog_silent_below_sample(caplog)`: call `sweep._check_detail_watchdog(5, 0, 0)`; assert no records with `"detail watchdog"` in message.
- `test_watchdog_warns_on_low_name_rate(caplog)`: call `sweep._check_detail_watchdog(20, 5, 20)` at WARNING level; assert one record containing `"parsed a name"`.
- `test_watchdog_warns_on_low_photo_rate(caplog)`: call `sweep._check_detail_watchdog(20, 20, 5)`; assert one record containing `"yielded a photo"`.
No fixtures. `caplog.set_level(logging.WARNING, logger="jcstream.sweep")`.

### R2 (-> tests-F2). `_fetch_one` fallback paths
Add in `tests/test_sweep.py` (or new `test_fetch_one.py`):
- `test_fetch_one_uses_list_row_name_when_heading_missing(monkeypatch, tmp_path)`: stub `client.get` to return `detail_no_photo.html`-style HTML with the `<h1>` blanked; pass a `ListRow(last_name="DOE", first_name="JANE")`; assert returned `Inmate.last_name == "DOE"`.
- `test_fetch_one_carries_existing_photo_when_no_inline_image(tmp_path, monkeypatch)`: pre-seed `tmp_path / "1.jpg"`; `monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)`; stub `client.get` to return HTML with no `data:` img; assert `inm.photo_filename == "1.jpg"`.
Minimal fixture: reuse `detail_no_photo.html`.

### R3 (-> tests-F3). Name-split edge cases
Add in `tests/test_parsers.py`:
- `test_split_name_no_comma_keeps_value_in_last()`: assert `parsers._split_name("SMITH") == ("SMITH", "", "")`.
- `test_split_name_trailing_space_after_comma()`: assert `parsers._split_name("SMITH, ") == ("SMITH", "", "")`.
- `test_split_name_with_middle()`: assert `parsers._split_name("DOE, JOHN QUINCY ADAMS") == ("DOE", "JOHN", "QUINCY ADAMS")`.
- `test_parse_name_skips_mixed_case_heading()`: feed HTML with `<h1>Doe, John</h1>`; assert `parsers._parse_name(HTMLParser(html)) == ""`.
No new fixture files; inline HTML strings.

### R4 (-> tests-F4). Boundary assertions
Add in `tests/test_sweep.py`:
- `test_sweep_healthy_at_failure_fraction_boundary()`: assert `_sweep_looks_healthy(1000, 900, 10, 1)` is True (10% exact); assert `_sweep_looks_healthy(1000, 900, 10, 2)` is False (20%).
- `test_sweep_healthy_at_roster_fraction_boundary()`: assert `_sweep_looks_healthy(1000, 500, 26, 0)` is False; assert `_sweep_looks_healthy(1000, 501, 26, 0)` is True.
- `test_sweep_bootstrap_floor_edge()`: assert `_sweep_looks_healthy(49, 0, 26, 26)` is True; `_sweep_looks_healthy(50, 0, 26, 26)` is False (one-above-floor must enforce the guard).
- `test_prune_photos_at_exact_half(tmp_path, monkeypatch)`: 10 photos, 5 doomed; assert prune ran (the `> 0.5` semantics).
No new fixtures.

### R5 (-> tests-F5). Scrub fixtures
- Rename names in `tests/fixtures/detail_inmate.html` and `tests/fixtures/list_smith.html` to `DOE / ROE / VOE` style and update the matching expected values in `tests/test_parsers.py`.
- Add `tests/fixtures/README.md` with the rule: "All names are placeholders. Real HCSO records must never be committed; scrape, scrub, then commit."
- Not a new test; a content edit plus a one-line policy doc.

### R6 (-> tests-F6). Header-injection test
Add in `tests/test_pra.py`:
- `test_build_message_rejects_crlf_in_window()`: `with pytest.raises(ValueError): pra_capias._build_message(since="2026-05-10\r\nBcc: x@y", until="x", to_addr="a@b", from_addr="c@d")`.
This pins the implicit `EmailMessage` defense.

### R7 (-> tests-F7). Document `_materially_changed` charge-order behavior
Add in `tests/test_store.py`:
- `test_diff_fires_updated_when_charges_reordered()`: same two `Charge` objects in swapped order; assert one `updated` event.
- Either accept this as the contract (and the test documents it) or change `_materially_changed` to compare a frozen-set of charge tuples. Recommendation: accept and document, because order signals the lead-charge ranking on the detail page.

### R8 (-> tests-F8). `make_client` env smoke test
Add in `tests/test_client.py`:
- `test_make_client_respects_env(monkeypatch)`: set `JCSTREAM_BASE_URL=https://example.test`, `JCSTREAM_CRAWL_DELAY=1.5`; assert `client_mod.make_client().base_url == "https://example.test"` and `crawl_delay == 1.5`.
One assertion each, no fixtures.

## Remediation plan
1. Land R1 + R4 in one PR (sweep depth). Pure unit tests, no fixtures, locks down the watchdog and boundary semantics that protect the cron.
2. Land R3 in the same week (parser unit tests). Pure inline HTML, four tests, ~30 lines.
3. Land R2 (fetch_one path) next. Slightly larger because of `client.get` stubbing; reuse `detail_no_photo.html`.
4. Land R5 (fixture scrub) in a single content commit. Update `test_parsers.py` expected names to match. Add `tests/fixtures/README.md`.
5. Land R6 + R7 + R8 together as miscellaneous coverage; each is a one-or-two-line test.

## Cross-references
- Watchdog and prune semantics overlap the sweep-reliability audit scope (`jcstream-python-sweep-reliability`). Findings tests-F1, tests-F2, tests-F4 are coverage gaps for guards that audit reviews on its side.
- Parser heading and base64 photo assumptions overlap the parser-robustness audit (`jcstream-python-parser-robustness`). tests-F3 is a coverage gap for parser drift that audit catalogues at the code-fix level.
- `_materially_changed` order semantics overlap the data-integrity audit (`jcstream-python-data-integrity`). tests-F7 is a coverage gap for changelog correctness invariants.
- PRA header-injection defense overlaps the security-networking audit (`jcstream-python-security-networking`). tests-F6 is the test side of a defense that audit reviews at the SMTP-trust-boundary level.
- Fixture scrub overlaps the legal-posture / no-archive policy audit (`jcstream-html-content-governance`). tests-F5 is the test-repo expression of the no-archive promise.

## Confidence and limitations
- I read every test file under `tests/` and every Python source file under `scraper/`. I sampled `web/build.py` at the entry point, helper definitions, and the `_compute_stats` / `_write_*` block, but not every helper body in that 1282-line file.
- I did not run mutation testing or coverage instrumentation. The "untested" claims are based on grep across `tests/*.py` for the symbol name and on reading the existing tests' assertions.
- I trusted the pytest baseline given in the prompt (102 passed, green) and re-confirmed the 102 collection count via `pytest --collect-only -q`.
- The fixture privacy concern (tests-F5) is medium-confidence: the names look real but I have no way from this sandbox to verify against the live HCSO roster. The remediation is cheap regardless.
- Recommendations stay below the skill's "10 lines or fewer" rule and use stdlib `unittest.mock` / `monkeypatch` / `caplog`. No new dev dependency is proposed.

End of report.
