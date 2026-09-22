# JCStream

[![CI](https://github.com/AICincy/HCJC/actions/workflows/ci.yml/badge.svg)](https://github.com/AICincy/HCJC/actions/workflows/ci.yml)

Static mirror of the Hamilton County (Ohio) Justice Center inmate roster.
Scrapes the public HCSO roster and Cincinnati Open Data feeds, then builds a
fully static, searchable site. No database server, no backend, no tracking.

- **Live site:** https://www.aretheyinjail.com
- **Source:** https://github.com/AICincy/HCJC (MIT)
- **Corrections, sealing, or removal:** https://github.com/AICincy/HCJC/issues - no fee, ever

## Status as of 2026-09-22

- **1,213 people** listed in custody, data current as of **2026-09-22T15:06:59Z**
  (live `/data/current.json` `inmate_count` and `inmates` length both 1,213;
  live site verified HTTP 200).
- Deploys from the tip of `main` via GitHub Pages. No commit hash is pinned
  here by design; the live commit is always the current `origin/main` tip.
  CI and the Pages build run green on every push to `main`.
- **137,807-record** append-only SHA-256 hash-chained WAF evidence log
  (docs/data/waf_block_log.json), chain verified in CI. The log lives in
  both `data/` (the sweep's working copy) and `docs/data/` (the published
  mirror); the two are byte-identical and CI asserts they stay that way.
- 702 tests, ruff and mypy clean (verified 2026-09-21).
- Deep-audit wave (2026-09-20): the 2 critical and 3 major findings were
  fixed fail-closed (corrupt evidence/changelog can no longer be silently
  replaced; detail-page blocks are deduped; outage probes use 3 roster IDs
  with a content-size recovery rule; the `-X ours` merge fallback is gone),
  plus all 16 minor findings (stale-ref fetch race, CI WAF presence guard,
  timestamp commit churn, `%y` pivot and offset-timestamp handling, UI label
  and timestamp fixes, canonical tags). See the audit report.
- Dark theme is live with a header toggle (persists via localStorage).
  Felony F1-F5 red-to-amber severity scale unchanged.
- 1,126 inmates in that snapshot carry a `photo_filename`; the gap is upstream
  photo-fetch failures during HCSO blocks, not pruning.
