# Contributing

## Corrections, sealing, expungement, removal — no fee, ever

If something about a record is wrong, or a court has ordered it sealed or expunged, or you
want it removed: **open a [GitHub issue](https://github.com/AICincy/JCStream/issues).** There
is no fee for review, correction, or removal, and there never will be. A record also drops off
automatically on the next update once HCSO removes it from its public roster — the issue just
lets us act sooner if needed. See **[[Legal]]** for the policy in full.

## Adding case data (crowdsourced)

courtclerk.org's `robots.txt` disallows scraping its data, so JCStream **links** to case
records but doesn't pull them. If you've looked a case up yourself, you can add what you found
via the **["case data" issue form](https://github.com/AICincy/JCStream/issues/new?template=case-data.yml)** —
`scraper/ingest_issue.py` parses it into `data/courtclerk_cases.json`.

## Code contributions

```bash
git clone https://github.com/AICincy/JCStream.git
cd JCStream
pip install -r requirements.txt
python -m pytest -q                                          # must stay green
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
# open docs/index.html in a browser
```

- Keep the test suite green. Add tests for new pure logic (see `tests/test_*.py`, e.g.
  `test_sweep.py` for the sweep health heuristic).
- The site must remain **usable without JavaScript** — JS is progressive enhancement only
  (the filter bar, the search dropdown, the lightbox, the badge tooltip, the map).
- Don't break the **no-archive** invariant: nothing should persist a record after HCSO removes
  it (the daily `history.json` is counts only, no individuals — that's the line).
- Watch the don't-revert footguns in **[[Operations]]** (`data/surnames.txt`, the CSS
  cache-buster, blanket `git checkout -- data/`).
- New runtime dependencies (anything fetched in the browser) need a strong reason, SRI pinning,
  and a graceful fallback — the Leaflet map is the model (and the only one so far).

## Style

Editorial dark theme; serif headlines; restrained palette where saturated red/amber means
"severity", not decoration. The site does not editorialise about guilt — language stays
factual ("charges", "accusations", "presumed innocent"), never "criminal" / "offender".

## Reporting a security or privacy issue

`/.well-known/security.txt` points at the issue tracker. For something you'd rather not file
publicly, say so in the issue and we'll arrange a private channel.
