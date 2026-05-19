---
name: jcstream-build-helper-author
description: Use when adding or modifying Python helper functions in web/build.py, web/classify.py, or web/shape.py that compute values for Jinja templates in the JCStream project. Covers the env.globals registration pattern (in web/build.py), the Inmate/Snapshot models, the _DEGREE_RE / _CHAPTER_LABEL / _OFFENSE_CATEGORY maps (now in web/classify.py), and the snapshot-shape helpers (now in web/shape.py). Trigger phrases: "add a helper for X", "compute Y per inmate", "expose Z to templates", "register a Jinja global", "compute bond/tier/category for inmate", "categorize this ORC code".
---

# JCStream build-helper author

You own the helper layer split across `web/build.py` (922 lines — orchestration + env.globals registration), `web/classify.py` (537 lines — ORC tier/chapter maps, regexes, date and bond parsing, per-charge helpers), and `web/shape.py` (688 lines — snapshot-shape and per-inmate display helpers). Helpers are Python functions registered as Jinja env globals so templates can call them inline.

## The registration pattern
Every helper follows this contract:

1. Define the function in the right file: tier / charge / date / bond / per-charge helpers belong in `web/classify.py` (near `_primary_tier`, `_parse_book_date`); per-inmate display and snapshot-shape helpers belong in `web/shape.py` (near `_bond_total`, `_recent_booked_inmates`); orchestration-only helpers (file I/O, template wiring) stay in `web/build.py`.
2. Re-export the symbol from `web/build.py` if needed (the import block at `web/build.py:33-49` already pulls in most classify/shape symbols with `# noqa: F401` for tests).
3. Register on `env.globals` inside `build()` (in `web/build.py:111-184`):
   ```python
   env.globals["my_helper"] = _my_helper
   # or lambda-wrapped when you need to bind snapshot or offenses:
   env.globals["bond_context"] = lambda inm: _bond_context(inm, snapshot.inmates, offenses)
   ```
4. Call from a template:
   ```jinja
   {% set ctx = bond_context(inmate) %}
   ```

**Missing either side fails silently.** Forget the registration → Jinja prints `''`. Forget the template call → the helper is dead code. Add both in the same commit.

## Models you'll work with
- `Inmate` — `scraper/models.py`. Fields: `inmate_number`, `booking_number`, `last_name`, `first_name`, `middle_name`, `date_of_birth`, `sex`, `race`, `booking_date`, `projected_release_date`, `holder_status`, `photo_filename`, `charges: list[Charge]`, `first_seen_utc`, `last_seen_utc`. Note: `full_name` is a `@property` (joined + per-part 80-char cap, total cap 256), not a stored field.
- `Charge` — `orc_code`, `description`, `court_date`, `bond_type`, `bond_amount`, `disposition`, `common_pleas_case`, `municipal_case`, `other_case`, `comments`.
- `Snapshot` — `schema_version: int = 1`, `generated_utc`, `inmate_count`, `inmates`. A `@model_validator` (`_check_snapshot_invariants`) enforces `inmate_count == len(inmates)` and unique `inmate_number`s on both read and write — any helper that constructs or mutates a Snapshot must keep these invariants intact.

## Helpers you can build on
- `_parse_book_date(s)` — parses M/D/YY or M/D/YYYY, rejects sentinel dates > 15 years old. Returns `datetime | None`.
- `_parse_bond_amount(s)` — parses `$25,000` → `25000`. Returns `int | None`.
- `_charge_tier(c, offenses)` — degree resolution: description suffix > ORC default > venue.
- `_primary_tier(inmate)` — most-severe tier label for the corner badge.
- `_primary_degree(inmate)` — F1/F2/.../MM picker.
- `_days_in_custody(inmate)` — filtered for sentinel dates.
- `_offense_for_code(code)` (`web/classify.py`) — the dispatcher between `_OFFENSE_CATEGORY` (fine, per-code) and `_CHAPTER_LABEL` (coarse, per-chapter); returns `{label, cls}` or `None`. Use this rather than reaching into either map directly.

## Currently registered env.globals
Before writing a new helper, check whether one of these already covers the need (search `env.globals[` in `web/build.py`):

- Charge/offense lookup: `primary_charge`, `primary_chapter`, `charge_tier`, `tier_max`, `tier_ladder`, `tier_counts`, `bond_by_tier`, `charges_by_chapter`, `crimes_of_month`, `orc_freq`, `orc_title`, `codes_ohio_url`, `card_tip`.
- Inmate display/derivation: `primary_tier`, `primary_degree`, `avatar_initials`, `card_data`, `expand_race`, `expand_sex`, `approx_age`, `booking_seq`, `next_court_date`, `case_numbers`, `charge_status_summary`, `bond_total`, `days_in_custody`, `bond_context`.
- Snapshot-level: `recent_booked_inmates`, `inmates_by_id`, `all_chapters`, `all_inmates_total`, `similar_by_statute`, `related_inmates`, `timeline_markers`, `display_date`.
- Site/template plumbing (not Python helpers, but live in the same registration block — don't reinvent): `base_url`, `site_url`, `css_version`, `giscus`, `cck_name_search`, `cck_case_summary`.

Snapshot-shape helpers feeding the above (call these when composing your own): `_recent_booked_inmates` (`web/shape.py`), `_orc_frequency` (`web/classify.py`), `_group_by_month` (`web/shape.py`), `_short_month_label` (`web/classify.py`).

## Static maps
- `_DEGREE_RE` — matches `F1` … `MM` suffix in a description.
- `_CHAPTER_LABEL` — coarse fallback (Ch. 2903 → "offense against persons").
- `_OFFENSE_CATEGORY` — fine-grained per-code label + chapter color class.
- `_CLS_RANK` — chapter color severity rank for picking a primary.

When adding a new ORC code's category, edit `_OFFENSE_CATEGORY`, not the chapter map — the chapter map is intentionally coarse.

## Anti-patterns
- Hardcoding paths — use `Path("data/...")`.
- Mutating `Snapshot.inmates` — treat as read-only.
- Forgetting to handle `None` from `_parse_book_date` — sentinel dates return `None` by design.
- Inline `re.search` for bond amounts — call `_parse_bond_amount` for consistency.

## Verify
```sh
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build
python -m pytest -q
```
For a non-trivial helper, also add a unit test (hand off to **jcstream-test-author**).
