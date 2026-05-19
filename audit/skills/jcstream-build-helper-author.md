# Audit — jcstream-build-helper-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-build-helper-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-build-helper-author.md
- **Verdict**: Yellow
- **One-line summary**: Core contract and named helpers/maps still match code, but model field lists are incomplete and the registration block has grown well past what SKILL.md cites.

## A. Drift
- `web/build.py:79-140` cited as the registration range; actual block runs `web/build.py:111-184` post-2026-05-19 refactor (line 184 registers `all_inmates_total`). The SKILL.md cite is pre-refactor.
- "(~1700 lines)" — file was 1682 lines pre-2026-05-19; now 922 after the classify.py / shape.py split (`web/build.py:922`).
- `Inmate` field list omits `first_seen_utc` and `last_seen_utc` (`scraper/models.py:62-63`) and lists `full_name` as a field, but it is a `@property` on `Inmate` (`scraper/models.py:65-71`).
- `Charge` field list omits `comments` (`scraper/models.py:27`).
- `Snapshot` field list omits `schema_version: int = 1` (`scraper/models.py:101`) and the `_check_snapshot_invariants` model validator that enforces `inmate_count == len(inmates)` (`scraper/models.py:122-143`) — both are load-bearing for any helper that mutates or constructs snapshots.
- `_DEGREE_RE`, `_CHAPTER_LABEL`, `_OFFENSE_CATEGORY`, `_CLS_RANK`, `_parse_book_date`, `_parse_bond_amount`, `_charge_tier`, `_primary_tier`, `_primary_degree` all still exist but moved post-2026-05-19 to `web/classify.py` (`:26,51,101,84,150,173,387,440,461`); `_days_in_custody` moved to `web/shape.py:534`.

## B. Coverage gaps
- 24 env.globals-registered helpers are unmentioned. Registration sites all sit in `web/build.py:111-184`; def sites moved out of build.py in the 2026-05-19 refactor: `primary_charge` (`web/build.py:141`, def `web/shape.py:587`), `primary_chapter` (`web/build.py:142`, def `web/shape.py:602`), `tier_max` (`web/build.py:145`, def `web/classify.py:467`), `tier_ladder` (`web/build.py:146`), `display_date` (`web/build.py:150`, def `web/classify.py:189`), `timeline_markers` (`web/build.py:149`, def `web/shape.py:229`), `similar_by_statute` (`web/build.py:151`, def `web/shape.py:289`), `tier_counts` (`web/build.py:152`, def `web/classify.py:424`), `avatar_initials` (`web/build.py:154`, def `web/classify.py:257`), `card_data` (`web/build.py:155`, def `web/shape.py:471`), `card_tip` (`web/build.py:156`, def `web/shape.py:484`), `expand_race` / `expand_sex` (`web/build.py:157-158`, defs `web/classify.py:275,285`), `approx_age` (`web/build.py:159`, def `web/classify.py:217`), `booking_seq` (`web/build.py:160`, def `web/classify.py:239`), `bond_by_tier` (`web/build.py:164`, def `web/shape.py:352`), `next_court_date` (`web/build.py:165`, def `web/shape.py:371`), `case_numbers` (`web/build.py:166`, def `web/shape.py:445`), `charge_status_summary` (`web/build.py:167`, def `web/shape.py:455`), `bond_total` (`web/build.py:175`, def `web/shape.py:522`), `charges_by_chapter` (`web/build.py:177`, def `web/shape.py:552`), `crimes_of_month` (`web/build.py:178`, def `web/shape.py:77`), `orc_freq` (`web/build.py:181`), `codes_ohio_url` (`web/build.py:182`, def `web/classify.py:352`), `related_inmates` (`web/build.py:183`, def `web/shape.py:60`).
- Key non-registered helper used by every category lookup: `_offense_for_code` (`web/classify.py:369`) — the entry point to the fine→coarse fallback; should be called out alongside the maps.
- Snapshot-shape helpers `_recent_booked_inmates` (`web/shape.py:91`), `_orc_frequency` (`web/classify.py:479`), `_group_by_month` (`web/shape.py:621`), `_short_month_label` (`web/classify.py:199`) — all feed env.globals or templates, none mentioned.
- `giscus`, `css_version`, `base_url`, `site_url`, `inmates_by_id`, `all_chapters` env.globals (`web/build.py:111,115,120-126,130,174,179`) — not Python helpers per se, but worth one line so authors don't reinvent them.

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
