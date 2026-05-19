# Operations

## Build & test locally

```bash
# Regenerate docs/ from data/current.json (root-relative links + CNAME file)
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build

# Run the test suite (must stay green)
python -m pytest -q
```

If you've never run a sweep, `data/current.json` may not exist — the build renders an empty
site rather than failing. To pull a fresh roster (slow — full A–Z sweep is ~5–15 min):

```bash
python -m scraper.sweep                 # full sweep
python -m scraper.sweep --max-surnames 3   # quick partial, for development
python -m scraper.sweep --refresh-known    # also re-fetch detail pages we already have
python -m scraper.cfs --hours 168          # Cincinnati Open Data calls-for-service
```

## The automated cron

`.github/workflows/sweep.yml` runs every 30 minutes (`workflow_dispatch` too): sweep → pull
the four Cincinnati feeds → `python -m web.build` (with `JCSTREAM_SITE_BASE_URL=""` /
`JCSTREAM_CNAME=www.aretheyinjail.com`) → commit `data/ docs/` → push. GitHub Pages serves
`docs/` from the branch, so the push *is* the deploy. Other workflows: `ci.yml` (tests on PR),
`pra_daily.yml` (the optional PRA email loop), `ingest_case_data.yml` (the case-data issue form).

GH Actions cron is best-effort — expect 30–50 min cadence under load. The sweep step has a
50-minute timeout; `concurrency` prevents two sweeps overlapping.

## The sweep health guard

`scraper.sweep_guards.sweep_looks_healthy(prev_count, seen_count, n_surnames, n_failed)`
(also exported from `scraper.sweep` as a back-compat alias `_sweep_looks_healthy`): a sweep
is rejected (the last-good `current.json` is kept, the run exits 0) if more than 10 % of the
26 surname list-fetches errored, or the resulting roster is below half of last cycle. This is
what keeps the public count stable when HCSO rate-limits a sweep — otherwise a partial roster
makes everyone-not-in-it look "released", then the next complete sweep re-adds them as
"booked", churning the changelog and the count. Bootstrap runs (prior count < 50) are always
accepted. Covered by `tests/test_sweep.py`.

## Don't-revert footguns

- `data/surnames.txt` is **A–Z, 26 single letters, on purpose** (substring search). Don't "fix" it to full surnames.
- The stylesheet is cache-busted by **content hash** (`css_version` in `build.py`). Don't key it off the data timestamp.
- When rebasing onto a fresh cron commit, don't `git checkout -- data/` blanket-style — it will revert hand-edits to `data/orc_offenses.json` / `data/surnames.txt`.

## Optional features (owner-side setup)

These render their "policy" / "dry-run" form until you configure them:

### Giscus comments (GitHub-Discussions-backed) on inmate pages

1. Repo → Settings → General → Features → enable **Discussions**.
2. Pick (or create) a Discussions **category** for the threads.
3. Install the **Giscus GitHub App** (https://github.com/apps/giscus) on the account/repo.
4. Go to https://giscus.app, enter `AICincy/JCStream`, pick the category → it prints `data-repo-id` and `data-category-id`.
5. Repo → Settings → Secrets and variables → Actions → **Variables**: add `JCSTREAM_GISCUS_REPO_ID`, `JCSTREAM_GISCUS_CATEGORY_ID` (optionally `JCSTREAM_GISCUS_REPO`, `JCSTREAM_GISCUS_CATEGORY` to override the defaults).
6. The next sweep renders the comment widget on every inmate page. Clear the variables to turn it off.

### PRA email loop (capias / mugshot-fallback public-records requests)

Dry-runs (logs only) until SMTP is configured. Repo → Settings → Secrets and variables →
Actions → **Secrets**: `JCSTREAM_PRA_SMTP_HOST`, `JCSTREAM_PRA_SMTP_PORT`,
`JCSTREAM_PRA_SMTP_USER`, `JCSTREAM_PRA_SMTP_PASS`, `JCSTREAM_PRA_FROM_EMAIL` (optionally
the per-loop recipient overrides `JCSTREAM_PRA_TO_CAPIAS_EMAIL` for `scraper/pra_capias.py`
and `JCSTREAM_PRA_TO_PHOTOS_EMAIL` for `scraper/pra.py`; both default to
`HCAdmin@hamilton-co.org`). With `JCSTREAM_PRA_SMTP_HOST` + `JCSTREAM_PRA_FROM_EMAIL` set,
it sends for real.

## Publishing this wiki

The GitHub wiki is its own git repo (`https://github.com/AICincy/JCStream.wiki.git`). To push
these pages to it:

```bash
git clone https://github.com/AICincy/JCStream.wiki.git
cp /path/to/JCStream/wiki/*.md JCStream.wiki/
cd JCStream.wiki
git add -A && git commit -m "Sync wiki from main repo" && git push
```

(`_Sidebar.md` becomes the wiki's sidebar; `Home.md` is the landing page.) Keeping the source
of truth here in `wiki/` means the wiki is reviewable in PRs alongside code changes.
