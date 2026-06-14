---
name: jcstream-orc-curator
description: Use when maintaining the Ohio Revised Code mappings in the JCStream project — data/orc_offenses.json (code → title, degree) and data/explainers.json (code → plain-English explanation). Covers the base-code normalization in scraper/orc.py, the 10-tier degree ladder (F1…MM), and the info-log of unmapped codes. Trigger phrases: "add an ORC code", "explainer for §...", "missing statute title", "fix ORC tier/degree", "add explainer", "ORC code shows ?/unknown", "plain-English for §...", "edit orc_offenses.json or explainers.json".
---

# JCStream ORC curator

You own:
- `data/orc_offenses.json` — code → `{title, degree}` map
- `data/explainers.json` — code → `{plain, tier_meaning, max_term, typical_bond}` map
- `scraper/orc.py` — loader, `normalize_code`, `lookup`, `title_for`, `degree_for`, `primary_degree` (most-severe across a list of codes), `codes_without_titles` (drives the curation queue), and the `UNKNOWN = "?"` sentinel returned when a degree is missing.

## Schema
`orc_offenses.json`:
```json
{
  "_comment": "...",
  "_source": "Ohio Revised Code, codes.ohio.gov (read manually; we do not scrape that site)",
  "_degree_order": ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "MM"],
  "offenses": {
    "2903.01": {"title": "Aggravated murder", "degree": "F1"},
    ...
  }
}
```
`explainers.json`:
```json
{
  "_about": "Plain-English explainers for top ORC offenses...",
  "explainers": {
    "2903.01": {
      "plain": "...",
      "tier_meaning": "...",
      "max_term": "Life / capital",
      "typical_bond": "No bond, hold"
    },
    ...
  }
}
```

## Key conventions
- **Keys are base codes** (no subsection suffix). `2925.11A2` is normalized to `2925.11` by `normalize_code` (`scraper/orc.py`; imported as `orc_mod` in `web/build.py`) before lookup. Don't add subsection-suffixed keys; they'll never match. Note that `_CODE_RE` (`scraper/orc.py`, `r"\d+\.\d+(?:\.\d+)?"`) permits three-part section IDs like `2907.323` — those are legitimate ORC sections, not subsections, and several already exist in the file.
- **Degree is one of the 10 ladder values** (`F1…MM`). Typos like `F6` or `Misd1` silently miscolor every tier chip site-wide. The `_degree_order` array in `data/orc_offenses.json` is a sibling mirror of `DEGREE_ORDER` in `scraper/orc.py` — keep them in sync if either changes.
- **`title` is the statute's official noun phrase**, sentence-cased ("Aggravated murder", not "AGGRAVATED MURDER" — HCSO shouts; we don't).
- **The site-build logs unmapped codes** every sweep at `log.info` level (`web/build.py`, inside `_warn_about_unmapped_orcs` defined at `web/build.py`, invoked at `web/build.py`). Tail the log for the `"ORC titles missing"` line: those are your curation queue.
- **`_load_explainers` swallows JSON errors silently** (`web/build.py`) and `statute.html` falls back to the "No plain-English explainer is on file" copy. If a new explainer entry doesn't appear, suspect a JSON parse error in `data/explainers.json` first.

## When to add an entry
- A new code shows up in the unmapped-codes warning during a sweep.
- A charge description hints at a statute you haven't seen (e.g. a new traffic chapter).
- An explainer is requested for a code that already exists in `orc_offenses` but not `explainers`.

## Source of truth
Read `codes.ohio.gov` *manually* — the site has anti-scrape protection and we explicitly do not scrape it. Cite the section's official text in the explainer's `plain` field; rephrase in plain language. Do not editorialize.

## Anti-patterns
- Including subsections in keys (e.g. `2925.11A2`).
- Inventing degrees not on the ladder.
- Plain-English explainers that opine on guilt/innocence — every record is presumed innocent. Stick to what the statute *says* and what the *statutory* range is.
- Bumping a degree because "it's usually charged higher" — `degree` is the statutory default; aggravated subsections are reflected in the description suffix at runtime.

## Verify
```sh
python -c "import json; json.loads(open('data/orc_offenses.json').read())"
python -c "import json; json.loads(open('data/explainers.json').read())"
JCSTREAM_SITE_BASE_URL="" JCSTREAM_CNAME="www.aretheyinjail.com" python -m web.build 2>&1 | grep "ORC titles missing" | head -5
python -m pytest -q
```
The "ORC titles missing for N codes" log should shrink with each curation pass.
