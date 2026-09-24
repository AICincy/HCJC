# Full-stack audit evidence log — 2026-09-24 UTC

This is a reproducible command/output log for the audit report. It records both passes and blocked external checks; it does not convert a network failure into a pass.

## Identity and inventory

```text
checkout: arena/01a0d128-hcjc
baseline: 291deba46ed57398aecc8e6d0fda7005f0f5853
workflow files: 12
active action uses: 38
active refs with 40-hex SHA: 38
repeated actions with >1 SHA: 0
```

Workflow source links:

- [lint.yml](https://github.com/AICincy/HCJC/blob/main/.github/workflows/lint.yml)
- [live-parity.yml](https://github.com/AICincy/HCJC/blob/main/.github/workflows/live-parity.yml)
- [sweep.yml](https://github.com/AICincy/HCJC/blob/main/.github/workflows/sweep.yml)
- [ci.yml](https://github.com/AICincy/HCJC/blob/main/.github/workflows/ci.yml)

## Local automated checks

### YAML parsing

```text
PyYAML safe_load: 12/12 workflow files OK
```

### Focused audit/freshness tests

```text
.venv/bin/python -m pytest -q tests/test_full_stack_audit.py tests/test_live_html_freshness.py
40 passed (32 freshness cases + 8 workflow audit cases)
```

### Full suite and static checks

```text
.venv/bin/python -m pytest -q
803 passed in 19.00s

.venv/bin/ruff check web scraper tests scripts
All checks passed!

.venv/bin/mypy scraper web
Success: no issues found in 45 source files
```

The suite count is higher than the 779-test context because this audit adds the workflow inventory checks and expanded freshness matrix.

## Generated HTML evidence

The build was run with the production custom-domain environment:

```text
JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com python -m web.build
site built: 1194 inmates, 10000 recent events -> docs
```

The source snapshot is `2026-09-23T23:35:42Z`. Local output checks:

```text
HTML files: 1214
HTML files containing jcstream:generated-utc: 1214
sample docs/index.html marker:
<meta name="jcstream:generated-utc" content="2026-09-23T23:35:42Z">

sample footer:
Last updated: <time datetime="2026-09-23T23:35:42Z">Sep 23, 2026, 7:35 PM ET</time>

python scripts/verify_public_data.py
public data manifest and source mirrors: OK
```

## Local contract/freshness fixture coverage

The unit fixtures exercise strict parsing and all requested network classes without making network calls. The production workflow samples `index.html`, `data/index.html`, `help/index.html`, `stats/index.html`, and `transparency/index.html`.

Notable boundary assertions:

```text
lag == 26.00000 h       PASS (inclusive threshold)
lag == 26.00001 h       FAIL
lag == 25.99999 h       PASS
live one hour newer     warning, lag -1.00 h, diagnostic exit 0
live newer + strict flag candidate regression, exit 1
2099 future stamp       warning only
1970 stamp              suspiciously old, exit 1
```

## Live network evidence

Command:

```text
.venv/bin/python scripts/verify_live_html_freshness.py \
  --site https://www.aretheyinjail.com --local docs --data data/current.json \
  --max-lag-hours 26 --timeout 10 --fail-on-live-newer \
  --page index.html --page data/index.html --page help/index.html \
  --page stats/index.html --page transparency/index.html
```

Observed result:

```text
::error title=Live HTML freshness::/index.html: TLS verification failed; check certificate or domain (TLS/SSL connection has been closed (EOF) (_ssl.c:992))
... same TLS EOF for all five sampled pages ...
live HTML freshness failed: 5 error(s) across 5 page(s)
exit code: 1
```

The JSON probe showed the same TLS EOF for all 17 manifest URLs and exited 1. This is evidence that the gate fails closed in this environment, not evidence that the public domain is stale. Re-run from GitHub Actions or an owner-controlled network before rollout sign-off.

## Workflow run links

These are the most recent GitHub runs visible during the audit. The first two workflows predate the new two-job HTML gate, so they are provenance links, not acceptance of the new implementation:

- [live-parity run 35799729427](https://github.com/AICincy/HCJC/actions/runs/35799729427) — success, 2026-09-22, pre-audit workflow
- [live-parity run 35799543849](https://github.com/AICincy/HCJC/actions/runs/35799543849) — success, 2026-09-22, pre-audit workflow
- [sweep run 35933680491](https://github.com/AICincy/HCJC/actions/runs/35933680491) — success, 2026-09-23
- [CI run 35944809729](https://github.com/AICincy/HCJC/actions/runs/35944809729) — success, baseline commit
- [CI failure run 35944527682](https://github.com/AICincy/HCJC/actions/runs/35944527682) — useful historical failure signal

No new workflow was dispatched against the unpushed audit changes; doing so would not prove the eventual merged source.

## Idempotency evidence

Two immediate normal-clock builds kept these representative hashes stable:

```text
docs/index.html                 84fd82bac22127643c86a1887060ea18726fde2826daaf0d6148dd5b369847ef
docs/inmate/1027921/index.html  ef9a1fe2da40794b7339c2b77c4ce585c83ebd5d8b1cf536ffeeb0cc027bc82b
```

The complete tree was not stable. `docs/data/transparency_metrics.json` changed between build observations, including `computed_utc` and rounded age fields; `docs/transparency/index.html` and its checksum changed with it. The responsible code path is `web/transparency.py:compute_transparency_metrics()` using the wall clock by default. Optional tab feeds also produced missing-path stack traces in the build log, but the build completed and preserved the last-good swap contract.

## Screenshots

No browser screenshot was captured in this shell. The static HTML excerpts, file counts, hashes, and test output above are the available evidence; a maintainer should attach a mobile/desktop screenshot to the post-merge rollout record.
