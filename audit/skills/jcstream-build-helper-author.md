# Audit — jcstream-build-helper-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-build-helper-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-build-helper-author.md
- **Verdict**: Yellow
- **One-line summary**: Core contract and named helpers/maps still match code, but model field lists are incomplete and the registration block has grown well past what SKILL.md cites.

## A. Drift
- `web/build.py:79-140` cited as the registration range; actual block runs `web/build.py:79-144` (line 144 registers `all_inmates_total`). Minor numeric drift.
- "(~1700 lines)" — file is 1682 lines (`web/build.py:1682`). Acceptable.
- `Inmate` field list omits `first_seen_utc` and `last_seen_utc` (`scraper/models.py:62-63`) and lists `full_name` as a field, but it is a `@property` on `Inmate` (`scraper/models.py:65-71`).
- `Charge` field list omits `comments` (`scraper/models.py:27`).
- `Snapshot` field list omits `schema_version: int = 1` (`scraper/models.py:101`) and the `_check_snapshot_invariants` model validator that enforces `inmate_count == len(inmates)` (`scraper/models.py:122-143`) — both are load-bearing for any helper that mutates or constructs snapshots.
- `_DEGREE_RE`, `_CHAPTER_LABEL`, `_OFFENSE_CATEGORY`, `_CLS_RANK`, `_parse_book_date`, `_parse_bond_amount`, `_charge_tier`, `_primary_tier`, `_primary_degree`, `_days_in_custody` all still exist as documented (`web/build.py:198,202,221,303,511,546,385,443,487,1005`).

## B. Coverage gaps
- 24 env.globals-registered helpers are unmentioned: `primary_charge` (`web/build.py:104,1061`), `primary_chapter` (`web/build.py:105,1077`), `tier_max` (`web/build.py:108,507`), `tier_ladder` (`web/build.py:109`), `display_date` (`web/build.py:113,529`), `timeline_markers` (`web/build.py:112,706`), `similar_by_statute` (`web/build.py:114,767`), `tier_counts` (`web/build.py:115,412`), `avatar_initials` (`web/build.py:117,815`), `card_data` (`web/build.py:118,938`), `card_tip` (`web/build.py:119,952`), `expand_race`/`expand_sex` (`web/build.py:120-121,830,835`), `approx_age` (`web/build.py:122,840`), `booking_seq` (`web/build.py:123,860`), `bond_by_tier` (`web/build.py:124,871`), `next_court_date` (`web/build.py:125,891`), `case_numbers` (`web/build.py:126,910`), `charge_status_summary` (`web/build.py:127,921`), `bond_total` (`web/build.py:135,991`), `charges_by_chapter` (`web/build.py:137,1024`), `crimes_of_month` (`web/build.py:138,364`), `orc_freq` (`web/build.py:141`), `codes_ohio_url` (`web/build.py:142,357`), `related_inmates` (`web/build.py:143,339`).
- Key non-registered helper used by every category lookup: `_offense_for_code` (`web/build.py:306`) — the entry point to the fine→coarse fallback; should be called out alongside the maps.
- Snapshot-shape helpers `_recent_booked_inmates` (`web/build.py:539`), `_orc_frequency` (`web/build.py:325`), `_group_by_month` (`web/build.py:1120`), `_short_month_label` (`web/build.py:1086`) — all feed env.globals or templates, none mentioned.
- `giscus`, `css_version`, `base_url`, `site_url`, `inmates_by_id`, `all_chapters` env.globals (`web/build.py:81-100,134,139`) — not Python helpers per se, but worth one line so authors don't reinvent them.

## C. Trigger-phrase quality
- Current description (paraphrased): "adding/modifying Python helper functions in web/build.py for Jinja templates; covers env.globals registration, Inmate/Snapshot models, the regex/maps, date helpers; phrases like 'add a helper for X', 'compute Y per inmate', 'expose Z to templates'."
- Issues: Solid coverage. Could miss "compute bond total", "register a Jinja global", "primary charge logic" — which are common real phrasings. Minor.
- Proposed rewording: append phrases "register a Jinja global", "compute bond/tier/category for inmate", "categorize this ORC code". Otherwise leave as-is.

## D. Applicability
- Live and core — `web/build.py` is the sole renderer driving every page; the helper layer is actively expanding (24+ unlisted helpers).

## Recommended fixes (priority order)
1. Add the 24 unlisted env.globals helpers to "Helpers you can build on" (or a new "Currently registered" subsection) so authors don't duplicate work.
2. Fix `Inmate`/`Charge`/`Snapshot` field lists: note `full_name` as `@property`, add `first_seen_utc`/`last_seen_utc`/`comments`/`schema_version`, mention the snapshot invariants validator.
3. Update line range "around `build.py:79-140`" to `79-144` (or drop the literal range).
4. Mention `_offense_for_code` as the dispatcher between `_OFFENSE_CATEGORY` and `_CHAPTER_LABEL`.
5. Optionally append "register a Jinja global" / "compute bond/tier" trigger phrases.
