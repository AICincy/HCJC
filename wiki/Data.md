# Data, feeds & APIs

Everything the site is built from is published as plain files under
`https://www.aretheyinjail.com/data/` (and most of it is also in `data/` in the repo).
The full, canonical list with field-by-field descriptions is on the live site:
**[Data & methodology](https://www.aretheyinjail.com/data/)**. Summary:

## JSON files (`/data/`)

| File | What it is |
|---|---|
| `current.json` | The authoritative current-roster snapshot: `{generated_utc, inmate_count, inmates: [{inmate_number, booking_number, last_name, first_name, middle_name, date_of_birth, sex, race, booking_date, projected_release_date, holder_status, charges: [{common_pleas_case, municipal_case, other_case, court_date, orc_code, description, bond_type, bond_amount, disposition, comments}], photo_filename, first_seen_utc, last_seen_utc}]}` |
| `changelog.json` | Last ~500 change events: `{event: "booked"\|"released"\|"updated", inmate_number, name, timestamp_utc, note}`. `note` for a booking is `"booked M/D/YY"`. |
| `history.json` | Daily roster-size series (counts only — no individuals): `[{date, count, booked_24h, released_24h}, …]`, last ~400 days. Drives the homepage / stats sparklines. |
| `orc_offenses.json` | Hand-curated ORC criminal sections → `{title, degree}`. `degree` (F1…MM) is the statute's **default** classification; the degree actually charged can vary by subsection. |
| `cfs_recent.json` | Cincinnati Open Data — CPD/CFD Calls For Service (Socrata `qiik-bpks`), last ~7 days, arrest/citation/offense-report dispositions only. |
| `cfs_pdi_recent.json` | Cincinnati Open Data — PDI Police CFS / CAD (Socrata `gexm-h6bt`), last ~7 days, arrest/citation/offense-report dispositions. |
| `shootings_recent.json` | Cincinnati Open Data — CPD Reported Shootings (Socrata `sfea-4ksu`), last ~14 days. |
| `incidents_recent.json` | Cincinnati Open Data — PDI Crime Incidents (Socrata `k59e-2pvf`), last ~7 days. |
| `courtclerk_cases.json` | Crowdsourced case data submitted via the [case-data issue form](https://github.com/AICincy/JCStream/issues/new?template=case-data.yml). May be empty. |
| `SHA256SUMS` | SHA-256 of every file in `/data/`, regenerated each build — cheap tamper-evidence on top of the authenticated git history. |

## Indexes (site root)

- **`/search.json`** — `{generated_utc, count, rows: [{n: name, c: primary offense category, t: tier, b: booking date, id}]}`. Powers the type-ahead search box; handy for API consumers.
- **`/dispatches.json`** — `{generated_utc, count, points: [{la, lo, k: "cfs"\|"shooting", d: disposition/type, a: address/block, n: neighborhood, t: time}]}`. The points behind the homepage map. **Cincinnati Open Data only — not matched to anyone on the roster.**

## Feeds (RSS 2.0)

- **`/feed.xml`** — all changes (booked / released / updated), newest first, ~50 items.
- **`/booked.xml`** — new bookings only (filtered to events whose HCSO booking date is within ~21 days, so a sweep re-discovering older records can't fill it with stale "new bookings").
- **`/released.xml`** — releases only.

## Photos

`/photos/<inmate_number>.jpg` — the same image HCSO embeds (base64) on its `inmate-detail`
page, re-encoded to a 250×312 JPEG. Present only if HCSO published one; removed when the
person leaves the public roster.

## Robots / no-index

The site asks search engines not to index it (`<meta name="robots" content="noindex">` on
every page, plus `robots.txt: Disallow: /`). RSS readers don't honour `robots.txt`, so the
feeds remain usable. Social-card unfurlers get a **site-level** OpenGraph card only (a
per-page link unfurls as the generic project card, not an individual's name/photo).
`/.well-known/security.txt` and `/humans.txt` point at the no-fee corrections issue tracker.

## ORC offense categorisation

`web/classify.py` (via the `_OFFENSE_CATEGORY` and `_CHAPTER_LABEL` maps; `web/build.py`
re-exports the symbols for `tests/test_build.py` access, while templates reach the same
data through env.globals helpers like `primary_chapter` and `primary_charge`) maps each
ORC section to a **fine-grained offense category** with a colour class (homicide /
felonious assault / robbery / drug trafficking / domestic violence / …) keyed on the
section number — so Aggravated Murder and simple Assault never share a tag. The
colour tracks *severity feel*, not chapter number. Charge **tier** (F1…MM) uses the most
authoritative signal available per charge: an explicit degree suffix in the HCSO description >
the ORC default degree from `orc_offenses.json` > the court venue (Common Pleas = felony,
Municipal = misdemeanor). It is a label, not a judicial finding.
