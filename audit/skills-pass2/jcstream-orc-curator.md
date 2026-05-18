# Audit Pass 2 — jcstream-orc-curator

- **Date**: 2026-05-14
- **Pass-1 verdict**: Yellow
- **Pass-2 verdict**: Green
- **One-line summary**: All five pass-1 recommended fixes landed cleanly in SKILL.md with no new drift.

## Pass-1 recommendation status
1. Fix `build.py:139` → `web/build.py:1287`, "warning-log" → "info-log": **Done** — SKILL.md:46 now cites `web/build.py:1287`, `_warn_about_unmapped_orcs` at `web/build.py:1283`, invoked at `web/build.py:146`, and labels the level `log.info`. Verified against `web/build.py:1283-1287` and `web/build.py:146`. The paired agent file also updated to "info-log line" (`.claude/agents/jcstream-orc-curator.md:3`).
2. Document `_CODE_RE` permitting three-part IDs like `2907.323`: **Done** — SKILL.md:43 spells out `_CODE_RE` location (`scraper/orc.py:24`), the regex `r"\d+\.\d+(?:\.\d+)?"`, and explicitly notes three-part section IDs are legitimate while subsection suffixes are not. Matches `scraper/orc.py:24`.
3. Mention `primary_degree`, `codes_without_titles`, `UNKNOWN = "?"`: **Done** — SKILL.md:11 lists `lookup`, `title_for`, `degree_for`, `primary_degree`, `codes_without_titles`, and the `UNKNOWN = "?"` sentinel, with correct one-liner descriptions ("most-severe across a list of codes" and "drives the curation queue"). Matches `scraper/orc.py:46,54,58,62,79` and `scraper/orc.py:28`.
4. Note `_degree_order` mirror and `_load_explainers` silent-failure: **Done** — SKILL.md:44 calls out the `_degree_order` sibling mirror at `data/orc_offenses.json:4` vs `DEGREE_ORDER` at `scraper/orc.py:27`; SKILL.md:47 covers the silent JSON-error swallow at `web/build.py:694-703` and the `statute.html:44` fallback copy. Both citations check out.
5. Broaden trigger phrases: **Done** — SKILL.md:3 now includes "fix ORC tier/degree", "add explainer", "ORC code shows ?/unknown", "plain-English for §...", "edit orc_offenses.json or explainers.json" alongside the original three.

## New issues found in pass 2
- None.

## Pass-2 lens checks
- **Drift**: Clean. SKILL.md:46 line numbers match `web/build.py:1283-1287, 146` exactly; SKILL.md:11 matches `scraper/orc.py:46,54,58,62,79`; SKILL.md:43 matches `scraper/orc.py:24`; SKILL.md:44 matches `data/orc_offenses.json:4` and `scraper/orc.py:27`; SKILL.md:47 matches `web/build.py:694-703`.
- **Coverage**: Clean. All five gap items from pass 1 are addressed. The schema block (SKILL.md:14-40) now also reflects `_degree_order` at row 19 — consistent with `data/orc_offenses.json:4`.
- **Triggers**: Clean. The expanded trigger list at SKILL.md:3 covers the previously-missed phrasings ("fix the tier for §…", "code shows ?/unknown", "edit orc_offenses.json").
- **Applicability**: Domain remains alive — `scraper/orc.py` is imported by `web/build.py:24` and consumed throughout, both data files are populated, and `statute.html:44` still renders explainers; keep the skill.
