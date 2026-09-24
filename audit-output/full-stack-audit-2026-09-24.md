# HCJC full-stack audit: workflow cleanup and live-parity HTML freshness

**Audit date:** 2026-09-24 UTC  
**Audited checkout:** `arena/01a0d128-hcjc` at the start of the audit (`291deba`)  
**Repository:** [AICincy/HCJC](https://github.com/AICincy/HCJC)  
**Scope:** CI/CD entry points, static build, generated HTML, freshness probe, and failure-mode tests.

## Executive verdict

**Conditional pass.** The implementation now has a strict, fail-closed HTML freshness probe, a sequential JSON-contract/HTML-parity workflow, a machine-readable stamp on all 1,214 generated HTML files, an accessible static footer timestamp, and 803 passing tests. The audit found two operational blockers that remain visible rather than silently waived:

1. The sandbox's live HTTPS probe failed with `TLS/SSL connection has been closed (EOF)`, so this run cannot claim fresh production evidence. The failure is recorded in the evidence log and the probe exits non-zero as designed.
2. A repeated build is not completely byte-idempotent: `docs/data/transparency_metrics.json` and the transparency page contain wall-clock-derived `computed_utc` and age values. The source is `web.transparency.compute_transparency_metrics()`'s default `datetime.now()` path. The main index and representative inmate page were stable in the immediate repeat, but the whole `docs/` tree is not yet stable by the stated audit criterion.

The exact phrase "v7.0.1 across all actions" is also not a safe literal requirement: every active action reference is pinned to a full SHA, and each repeated action uses one SHA, but upstream currently labels `setup-python` and `setup-node` as `v7.0.0`; Pages/CodeQL/Deno actions have their own release lines. No floating or unpinned active reference was found.

## Status legend

- **PASS**: directly verified by source inspection and/or a local automated test.
- **PARTIAL**: source is correct, but a live/external assertion could not be completed here.
- **FAIL**: the requested invariant is not true in the current tree.
- **N/A**: not applicable to this static deployment path.

## 1. CI/CD workflow audit

### 1.1 Action pin consistency — **PASS with version-target exception**

The repository contains exactly these 12 workflow files:

```text
archive-evidence.yml       ci.yml                 clerk_pra_packets.yml
codeql.yml                 deno.yml               ingest_case_data.yml
lint.yml                   live-parity.yml        pages.yml
rebuild.yml                refresh_caselaw.yml    sweep.yml
```

The active workflow scan found 38 `uses:` references. All 38 use a 40-character commit SHA. No active `@v4`, `@latest`, `@main`, tag-only, or branch-only reference was found. Repeated actions are consistent:

| Action | Active SHA | Commented release label | Result |
| --- | --- | --- | --- |
| `actions/checkout` | `3d3c42e5aac5ba805825da76410c181273ba90b1` | v7.0.1 | PASS |
| `actions/setup-python` | `5fda3b95a4ea91299a34e894583c3862153e4b97` | v7.0.0 | PASS pin consistency; not literal v7.0.1 |
| `actions/upload-artifact` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | v7.0.1 | PASS |
| `actions/setup-node` | `820762786026740c76f36085b0efc47a31fe5020` | v7.0.0 | PASS pin consistency; not literal v7.0.1 |

The single-use actions are also SHA-pinned. There are zero same-action exceptions. The report does **not** relabel a SHA as v7.0.1 when the upstream tag is v7.0.0; doing so would create false provenance.

### 1.2 `lint.yml` — **PASS**

- The file is `lint.yml`; `pylint.yml` is absent.
- `push.branches-ignore: [main]` covers side-branch pushes, and `pull_request:` covers PR events.
- `ci.yml` is now `push.branches: [main]` only; it no longer repeats Ruff/pytest on PRs.
- Python `3.14`, `pip install -r requirements.txt`, `ruff==0.16.7`, concurrency, and a 10-minute timeout are present.
- The workflow intentionally runs Ruff and pytest; the full matrix/mypy/audit gates remain on main in `ci.yml`.

### 1.3 `live-parity.yml` — **PASS statically; PARTIAL live evidence**

The workflow now has an explicit dependency chain:

1. **Check published JSON contract**: builds the candidate, verifies local JSON, and probes production JSON.
2. **Check published JSON contract and HTML freshness**: `needs: contract`, rebuilds from checked-out tip data, and invokes:

```text
python scripts/verify_live_html_freshness.py
  --site https://www.aretheyinjail.com
  --local docs
  --data data/current.json
  --max-lag-hours 26
  --timeout 10
  --fail-on-live-newer
  --page index.html
  --page data/index.html
  --page help/index.html
  --page stats/index.html
  --page transparency/index.html
```

The probe has no retry-forever/recovery mode and the workflow has read-only contents permission. There is no deployment step. It is scheduled Monday at `04:40 UTC` and supports `workflow_dispatch`.

The sandbox execution of the same command failed closed on all five pages with TLS EOF. That is an external availability/certificate observation, not a code-pass claim; see the evidence log.

### 1.4 `sweep.yml` — **PARTIAL**

- Hourly cron: `0 * * * *`; manual dispatch is available.
- The sweep builds into `docs/` and publishes both `data/` and `docs/` through `commit_generated_changes.sh`.
- The build uses a temp directory and rename-based last-good swap. Existing integration tests cover render failure, promote failure, cleanup, and preserved files.
- Corrupt/missing source JSON raises before the swap, so a failed build cannot publish a partially rendered tree.
- Success logging includes `site built: <count> inmates, <count> recent events -> docs`.
- The local build also emitted clear-but-noisy missing optional tab-feed paths (`jury.json`, `rules.json`, `forms.json`, `services-programs.json`) and continued. Those are useful on-call signals, but should be classified as warnings or made explicit optional inputs rather than logged as stack-trace errors.
- **FAIL for whole-tree idempotency:** transparency metrics use wall-clock time. See §4.1.

## 2. User-visible HTML audit

### 2.1 Stamp and footer — **PASS**

`web/templates/base.html` places the marker immediately after `<meta charset>` and before viewport/SEO metadata:

```html
<meta name="jcstream:generated-utc" content="2026-09-23T23:35:42Z">
```

The value comes from `Snapshot.generated_utc` / the build global, not a template-time clock. The footer is static HTML and now exposes:

```html
Last updated: <time datetime="2026-09-23T23:35:42Z">Sep 23, 2026, 7:35 PM ET</time>
```

The `<time>` `datetime` is the full machine value; the visible text clearly labels Eastern Time (`ET`). The generated build checked 1,214 HTML files and found the marker in all 1,214.

### 2.2 Missing stamp — **PASS**

- A page with no marker still renders a useful footer (`Last updated: ...` from the source context, or `Last updated: unavailable` for an empty bootstrap context).
- The machine consumer does not treat that gracefully as success: missing live or candidate markers are explicit errors and return exit code 1.
- The error says the live tree likely predates deployment of the feature and recommends a newer deploy.

### 2.3 Malformation — **PASS**

The probe rejects malformed values, missing `Z`, space separators, invalid dates, and numeric offsets. It identifies the offending value. Attribute order is parsed independently, so valid HTML with `content` before `name` is not falsely treated as missing. Fractional seconds up to six digits are accepted and compared without truncation.

### 2.4 User perception/accessibility — **PASS for static behavior; PARTIAL visual device test**

The timestamp is in server-rendered HTML, not JavaScript or an async request. It therefore remains present with JavaScript disabled and on a low-bandwidth connection. `<time datetime>` supplies semantic/assistive technology information. A real mobile browser/screenshot run was not available in this shell; no screenshot is fabricated.

## 3. Freshness stress matrix

The new `tests/test_live_html_freshness.py` covers 32 focused cases (including existing cases) with a monkeypatched network boundary. Combined with the eight workflow-audit tests, the focused run was **40 passed**.

| Scenario | Expected policy | Result |
| --- | --- | --- |
| Live one hour ahead | Negative lag; diagnostic warning | PASS |
| Live 10 hours behind | Pass under 26 h | PASS |
| Exactly 26 hours behind | Pass at inclusive boundary | PASS |
| 26.00001 hours behind | Fail | PASS |
| 25.99999 hours behind | Pass | PASS |
| 72 hours behind | Fail with stale/deploy message | PASS |
| Microsecond timestamps | Preserve precision | PASS |
| DST/offset ambiguity | Strict `Z`; numeric offset rejected | PASS |
| Missing `Z`, space format, invalid date, offset | Reject clearly | PASS |
| Missing live stamp | Fail with predates-rollout message | PASS |
| Candidate vintage != tip | Fail | PASS |
| Candidate older than live | Production flag fails; diagnostic default warns | PASS |
| 404/500 | Fail with path/DNS or health hint | PASS |
| TLS failure | Fail with certificate/domain hint | PASS |
| Timeout | Fail at request timeout with unresponsive message | PASS |
| JSON/non-HTML response | Fail with Content-Type | PASS |
| Redirect | Fail; redirects are not followed | PASS |
| Multi-page drift | Any stale sampled page fails | PASS |
| Future 2099 stamp | Warning only, not freshness proof | PASS |
| Epoch stamp | Fail as suspiciously old/tampered | PASS |
| Mid-sweep old live tree | Immediate fail; no retry loop | PASS |

The reusable CLI defaults to a warning for live newer than tip because diagnostics often inspect a checkout behind production. The production workflow adds `--fail-on-live-newer`, making a candidate regression blocking while retaining the explicit 2099 tamper warning policy.

## 4. HTML drift and sweep audit

### 4.1 Hash stability — **PARTIAL / FAIL for full tree**

Immediate repeated builds produced stable hashes for the homepage and representative inmate page:

```text
docs/index.html                 84fd82bac22127643c86a1887060ea18726fde2826daaf0d6148dd5b369847ef
docs/inmate/1027921/index.html  ef9a1fe2da40794b7339c2b77c4ce585c83ebd5d8b1cf536ffeeb0cc027bc82b
```

The whole tree is not byte-identical. `docs/data/transparency_metrics.json` and `docs/transparency/index.html` change between runs because `web.transparency.compute_transparency_metrics()` records `computed_utc`, freshness age, and denial duration from `datetime.now(timezone.utc)`. The resulting `docs/data/SHA256SUMS` also changes. This is a real audit finding, not an acceptable “CSS minifier reorder”: it is semantic telemetry drift. Fix options are to inject a single documented build reference clock or stop committing time-relative derived metrics in the generated tree.

### 4.2 Semantic stamp isolation — **PARTIAL**

The template change itself is isolated to the head marker and the footer `<time>` presentation. Asset content hashes and generated CSS/JS query fingerprints remain content-derived. Once the output is regenerated, unchanged pages retain the same roster content. A complete byte-for-byte no-other-diff assertion is blocked by the transparency clock finding above.

### 4.3 Rebuild idempotency — **FAIL for `docs/`**

The build's temp swap protects atomicity, but atomicity is not determinism. Repeat the test after installing the pinned requirements:

```bash
JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com python -m web.build
cp -a docs /tmp/docs-run-1
JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com python -m web.build
diff -qr /tmp/docs-run-1 docs
```

Expect transparency telemetry differences until §4.1 is fixed. The failure source is identified; no random asset fingerprinting was observed.

### 4.4 Fingerprints — **PASS**

`style.css`, `fold-chrome.css`, `main.js`, and `theme-init.js` versions are content SHA prefixes. The same source therefore produces the same asset query fingerprints; they are not random or timestamp-derived.

### 4.5 Position/format — **PASS**

The marker is after charset, before viewport, uses the exact `name` value, and uses a strict `Z`-terminated source value. It is not injected into body content.

### 4.6 Multiple sweeps — **PASS by source design**

Each hourly sweep rebuilds and commits `docs/`; Pages workflows are triggered from main. Since the marker follows the current source `data/current.json` vintage, a later sweep's committed docs carries the later stamp. A live Actions run after this audit was not triggered from the unpushed audit branch.

### 4.7 Corrupt data — **PASS**

`Snapshot`/JSON loading fails before the successful temp-tree promotion. Existing `tests/test_integration_smoke.py` verifies last-good preservation on render and swap failure. No broken `docs/` tree is committed by the build itself.

## 5. Integration and rollout validation

### 5.1–5.3 Timeline and scheduled/manual gates — **PARTIAL**

The hourly cadence, Monday schedule, manual dispatch, and read-only alert-only policy are statically verified. Existing historical run links are listed in the evidence log. Those pre-audit runs cannot prove the newly added HTML-freshness job, and the sandbox could not complete a live HTTPS probe due TLS EOF. A post-merge/manual run on the updated workflow is required before calling rollout validated.

### 5.4 Failure scenarios — **PASS in unit tests; PARTIAL live**

Down live, stale data, missing stamp, malformed stamp, HTTP failures, TLS, timeout, content type, and candidate regression all have non-zero paths and tests. The production parity workflow contains no recovery/deploy path. Actual alert delivery and the current production certificate need an Actions run or an owner-controlled network check.

## Remediation priorities

1. **P0:** Run the updated `live-parity.yml` manually from the merged branch and resolve the observed TLS EOF/certificate/DNS issue before treating live freshness as green.
2. **P1:** Make transparency metrics deterministic or explicitly untracked/ephemeral; add a whole-tree two-build `diff -qr` CI assertion if byte idempotency is a release requirement.
3. **P1:** Decide whether the exact v7.0.1 wording means a release label or only immutable SHA pinning. Do not relabel upstream v7.0.0 refs without an actual matching tag.
4. **P2:** Downgrade known optional tab-feed stack traces to actionable warnings with the missing path and fallback behavior.

See [`runbooks/live-parity-failure.md`](../runbooks/live-parity-failure.md) for on-call response.
