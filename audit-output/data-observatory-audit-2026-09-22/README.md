# Data Observatory post-change audit

Audit target: generated `/data/` page after the Civic Data Observatory redesign.

## Results

- axe-core 4.13.0: **0 violations** at 1440px dark, 390px dark, and 320px light.
- Global document width matched viewport width at all three sizes:
  - desktop: 1440 / 1440
  - mobile: 390 / 390
  - narrow: 320 / 320
- Three featured learning/research cards rendered.
- Eight purpose-oriented stream cards rendered.
- Progressive disclosure test passed: activating “Show every published file and schema” opened the details region and exposed 19 published-file rows.
- Pipeline navigation target resolves to the “How it’s built” section.
- Existing full schema table remains available and was not removed.

## Files

- `report.json`: rendered measurements and axe results.
- `desktop-dark.png`: full desktop render.
- `mobile-dark.png`: full 390px render.
- `narrow-light.png`: full 320px render.

## Build note

`python -m web.build` completed successfully and regenerated `docs/`. It emitted the repository's existing warnings about unavailable optional Firecrawl tab-feed files under `/home/user/firecrawl-zips/tab-build-2026-09-21/feeds/`; the build still completed with exit code 0 and preserved the site.
