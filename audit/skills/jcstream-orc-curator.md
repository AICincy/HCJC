# Audit — jcstream-orc-curator

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-orc-curator/SKILL.md
- **Paired agent**: .claude/agents/jcstream-orc-curator.md
- **Verdict**: Yellow
- **One-line summary**: Schemas, conventions, and ladder are all accurate, but the cited log-line location is stale by ~1150 lines and the log level is mischaracterised as a "warning."

## A. Drift
- SKILL.md:46 cites `build.py:139` for the unmapped-codes log; the actual call is at `web/build.py:1287` inside `_warn_about_unmapped_orcs` (defined at `web/build.py:1283`, invoked at `web/build.py:146`). Line 139 is now `env.globals["inmates_by_id"]` (`web/build.py:139`).
- SKILL.md:3, 46 and the agent file (`.claude/agents/jcstream-orc-curator.md:3`) call this a "warning-log" / "warns"; in fact it logs at `log.info` level (`web/build.py:1287`), so a `grep "WARNING"` will miss it. The user-facing string in the verify block (SKILL.md:66) does match: `"ORC titles missing"`.
- SKILL.md:43 names the normalizer `orc_mod.normalize_code`; the function is defined as bare `normalize_code` in `scraper/orc.py:39`. `orc_mod` is only the import alias used inside `web/build.py:24`. Minor but potentially confusing for someone grepping `scraper/orc.py`.

## B. Coverage gaps
- The skill never mentions `lookup()` (`scraper/orc.py:46`), `primary_degree()` (`scraper/orc.py:62`), `codes_without_titles()` (`scraper/orc.py:79`), or the `UNKNOWN = "?"` sentinel (`scraper/orc.py:28`) that returns when a degree is missing. `primary_degree`/`codes_without_titles` are the very functions that drive the curation queue and tier coloring.
- The regex governing what counts as an ORC code, `_CODE_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")` (`scraper/orc.py:24`), accepts a third dotted group (e.g. `2907.323` at `data/orc_offenses.json:30`). SKILL.md says "no subsection" but doesn't acknowledge the legitimate three-part section numbers already in the file.
- The skill doesn't mention that `_load_explainers` (`web/build.py:694-703`) silently swallows JSON errors and that `statute.html:44` falls back to the "No plain-English explainer is on file" copy — useful context for "why did my new entry not appear."
- Current data inventory is uneven: 109 entries in `data/orc_offenses.json` versus 37 in `data/explainers.json` (head/tail counts). The skill could note that explainers cover only the top-of-roster subset rendered by `_render_statute_page` (`web/build.py:1543`, top_n=60).
- No mention that `data/orc_offenses.json:4` carries `_degree_order` as a sibling array that must stay in sync with `DEGREE_ORDER` in `scraper/orc.py:27`.

## C. Trigger-phrase quality
- Current description (paraphrased): maintains ORC mappings; covers normalization, the 10-tier ladder, and the unmapped-codes warning. Triggers: "add an ORC code", "explainer for §...", "missing statute title".
- Issues: triggers are reasonable but narrow. Common phrasings that would *not* match: "what does 2907.05 mean", "fix the tier for §2925.11", "this code shows no title", "add a plain-English explainer", "the chip is grey/unknown for this charge", "update orc_offenses.json".
- Proposed rewording: add triggers like "fix ORC tier/degree", "add explainer", "ORC code shows ?/unknown", "plain-English for §...", "edit orc_offenses.json or explainers.json".

## D. Applicability
Domain is alive: `scraper/orc.py` is referenced 18 times in `web/build.py`, both data files exist with active content, and `statute.html` consumes explainers — keep the skill.

## Recommended fixes (priority order)
1. Update `build.py:139` → `web/build.py:1287` (function `_warn_about_unmapped_orcs`); change "warning-log" wording to "info-log" since it uses `log.info`.
2. Add a sentence explaining `_CODE_RE` permits `\d+\.\d+\.\d+`-style section IDs (e.g. `2907.323`), so three-part keys are legitimate while subsection suffixes (`A2`) are not.
3. Mention `primary_degree`, `codes_without_titles`, and the `UNKNOWN = "?"` sentinel in the "You own" section of SKILL.md.
4. Note the `_degree_order` mirror in `data/orc_offenses.json:4` and the silent-failure behavior of `_load_explainers` (`web/build.py:694`).
5. Broaden trigger phrases per section C.
