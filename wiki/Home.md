# JCStream

JCStream is a static, public-records mirror of the **Hamilton County, Ohio Justice
Center** inmate roster. It republishes what the Hamilton County Sheriff's Office
(HCSO) already publishes at [hcso.org](https://www.hcso.org/justice-center-services/inmate-search/),
in a structured, searchable, linkable form — under the Ohio Public Records Act,
[ORC § 149.43](https://codes.ohio.gov/ohio-revised-code/section-149.43).

- **Live site:** https://www.aretheyinjail.com
- **Source:** https://github.com/AICincy/JCStream (MIT)
- **Corrections / sealing / removal:** open an [issue](https://github.com/AICincy/JCStream/issues) — there is never a fee.

> **Arrest is not conviction.** Everyone listed is legally presumed innocent until
> proven guilty in a court of law. The charges shown are accusations only.
> JCStream keeps **no historical archive** — when HCSO removes a record, it is
> removed here on the next update cycle. JCStream is an independent, non-governmental
> project; it is not affiliated with HCSO or any government entity, and it is **not a
> consumer reporting agency** (do not use it for FCRA-governed screening). See
> **[[Legal]]** and the site's [legal notices](https://www.aretheyinjail.com/data/#legal).

## Wiki contents

- **[[Architecture]]** — how the scrape → build → publish pipeline works.
- **[[Data]]** — the published JSON, the RSS feeds, search/dispatch indexes, the ORC lookup.
- **[[Operations]]** — building locally, tests, the sweep health guard, optional features (comments, PRA email).
- **[[Legal]]** — the legal posture, in brief, and how corrections/sealing work.
- **[[Roadmap]]** — what's done, what's in flight, what's been considered and rejected.

## How it works in one paragraph

A GitHub Actions cron (every ~30 min) runs the HCSO scraper (`scraper/`), pulls four
Cincinnati Open Data feeds, diffs against the previous snapshot, then `web/build.py`
regenerates the static site into `docs/`, and the workflow commits `data/` + `docs/`.
GitHub Pages serves `docs/` from the branch at the custom domain. There is no server,
no database, and no service worker — a stale cached jail roster would be misleading.

---

*This `wiki/` directory in the main repo is the source of truth for the
[GitHub wiki](https://github.com/AICincy/JCStream/wiki); see [[Operations]] for how
to publish it.*
