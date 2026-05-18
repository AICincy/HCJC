# Audit Pass 2 — jcstream-build-helper-author

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five recommended fixes landed cleanly; the skill now matches `web/build.py:79-144` and `scraper/models.py` precisely.

## Pass-1 recommendation status
1. Add 24 unlisted env.globals helpers: **Done** — new "Currently registered env.globals" section enumerates them grouped by domain (`.claude/skills/jcstream-build-helper-author/SKILL.md:41-47`); spot-checked `primary_charge`, `card_data`, `crimes_of_month`, `all_inmates_total`, `related_inmates` against `web/build.py:104,118,138,144,143`.
2. Fix Inmate/Charge/Snapshot field lists: **Done** — `full_name` flagged as `@property` and added `first_seen_utc`/`last_seen_utc` (`SKILL.md:28`); `comments` added to Charge (`SKILL.md:29`); `schema_version: int = 1` and the `_check_snapshot_invariants` model validator both called out (`SKILL.md:30`). All match `scraper/models.py:27,62-63,65-71,101,122-143`.
3. Update line range `79-140` → `79-144`: **Done** — `SKILL.md:14` and `SKILL.md:42` both cite `build.py:79-144`, matching the actual range (last entry at `web/build.py:144`).
4. Mention `_offense_for_code` as the fine→coarse dispatcher: **Done** — added with file:line citation (`SKILL.md:39`).
5. Append trigger phrases "register a Jinja global" / "compute bond/tier": **Done** — front-matter description now includes "register a Jinja global", "compute bond/tier/category for inmate", "categorize this ORC code" (`SKILL.md:3`).

## New issues found in pass 2
- None. The line range correction (1682) at `SKILL.md:8` matches `wc -l` output.
- Bonus: SKILL.md:49 also picks up the unregistered snapshot-shape helpers (`_recent_booked_inmates`, `_orc_frequency`, `_group_by_month`, `_short_month_label`) that pass-1 listed under coverage gap B — a fix not explicitly requested but welcome.
- Paired agent (`/.claude/agents/jcstream-build-helper-author.md`) was not updated, but its content is a high-level pointer to the skill and contains no specific claims that drifted — acceptable.

## Pass-2 lens checks
- **Drift**: Clean. Line range, model fields, and helper names all reconcile with `web/build.py:79-144` and `scraper/models.py:17-143`.
- **Coverage**: Clean. The "Currently registered env.globals" inventory closes the 24-helper gap; the `_offense_for_code` dispatcher is documented; site/template plumbing (`base_url`, `site_url`, `css_version`, `giscus`, `cck_*`) explicitly listed with a "don't reinvent" note (`SKILL.md:47`).
- **Triggers**: Clean. Description now ends with "compute bond/tier/category for inmate", "categorize this ORC code", "register a Jinja global" — should fire on common phrasings like "register a Jinja global for X" and "compute bond total per inmate".
- **Applicability**: Still live and central — `web/build.py` remains the sole renderer driving every page and is actively growing.
