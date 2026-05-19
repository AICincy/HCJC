# JCStream skills

Fifteen project-specific Claude Code skills, one per recurring domain. Each skill
is auto-discovered by description (frontmatter `description:` field) and is
paired with a same-named subagent in `../agents/`.

| Skill | Owns | Fires on |
|---|---|---|
| [jcstream-template-author](jcstream-template-author/SKILL.md) | `web/templates/*.html` | edits to Jinja templates |
| [jcstream-stylesheet-author](jcstream-stylesheet-author/SKILL.md) | `web/static/style.css` | CSS work, palette / tier tuning, mobile rules |
| [jcstream-build-helper-author](jcstream-build-helper-author/SKILL.md) | helpers in `web/build.py` | new computed values for templates |
| [jcstream-orc-curator](jcstream-orc-curator/SKILL.md) | `data/orc_offenses.json`, `data/explainers.json` | missing ORC titles, new explainers |
| [jcstream-scraper-author](jcstream-scraper-author/SKILL.md) | `scraper/*.py`, `.github/workflows/sweep.yml` | new data feeds, HCSO fixes, threshold tuning |
| [jcstream-test-author](jcstream-test-author/SKILL.md) | `tests/*.py`, `tests/conftest.py` | new coverage, flaky-test fixes |
| [jcstream-design-interpreter](jcstream-design-interpreter/SKILL.md) | orchestration of design ports | uploaded design zips / Figma / JSX / screenshots |
| [jcstream-legal-copy-author](jcstream-legal-copy-author/SKILL.md) | legal language across public templates | disclaimer edits, FCRA, ORC § 149.43 / § 2953.32 |
| [jcstream-a11y-auditor](jcstream-a11y-auditor/SKILL.md) | accessibility audit reports (read-only) | WCAG checks, contrast issues, ARIA review |
| [jcstream-sweep-debugger](jcstream-sweep-debugger/SKILL.md) | diagnostic reports for sweep failures (read-only) | flat roster counts, silent fallback events |
| [jcstream-python-reviewer](jcstream-python-reviewer/SKILL.md) | python code-review reports (read-only) for `scraper/`, `web/`, `tests/` | PR review, lint / type / regex / thread-safety review |
| [jcstream-template-reviewer](jcstream-template-reviewer/SKILL.md) | template-layer review reports (read-only) for `web/templates/`, `feed.xml`, `feed.xsl`, `main.js` | XSS / JSON-LD / RSS / progressive-enhancement / third-party hygiene review |
| [jcstream-css-reviewer](jcstream-css-reviewer/SKILL.md) | CSS code-review reports (read-only) for `web/static/style.css` | dead rules, dupe selectors, tier ladder consistency, breakpoint hand-offs, focus rings, print rule, dead tokens |
| [jcstream-security-reviewer](jcstream-security-reviewer/SKILL.md) | JCStream-specific compliance review reports (read-only) cross-cutting | FCRA boundary, ORC § 149.43 / § 2953.32, `_headers` CSP / HSTS, no-fee guarantee, presumed-innocent banner, JCSTREAM_* secret hygiene, dependency CVEs |
| [jcstream-code-reviewer](jcstream-code-reviewer/SKILL.md) | Orchestrator (read-only); fans out to python/template/css/security reviewers in parallel and emits a consolidated PR-style review | PR review, branch review, full-repo audit |

## Handoff topology

```
                    design-interpreter
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   template-author   stylesheet-author   build-helper-author
        │                 │                 │
        │                 │                 ▼
        │                 │             test-author
        │                 │
        └────────┬────────┘
                 ▼
            a11y-auditor

   scraper-author ──── sweep-debugger
        │
        ▼
   test-author

   python-reviewer ───┬─► scraper-author
                      ├─► build-helper-author
                      ├─► test-author
                      ├─► orc-curator
                      └─► sweep-debugger

   template-reviewer ──┬─► template-author
                       ├─► a11y-auditor
                       ├─► legal-copy-author
                       ├─► stylesheet-author
                       ├─► build-helper-author
                       └─► test-author

   css-reviewer ──┬─► stylesheet-author
                  ├─► a11y-auditor
                  ├─► template-author
                  └─► test-author

   security-reviewer ──┬─► legal-copy-author
                       ├─► scraper-author
                       ├─► template-author
                       ├─► build-helper-author
                       └─► test-author

   code-reviewer (orchestrator)
       │
       ├─► python-reviewer ────┐
       ├─► template-reviewer ──┤  in parallel; merged report
       ├─► css-reviewer ───────┤  routes to the authors above
       └─► security-reviewer ──┘

   orc-curator     legal-copy-author     (mostly terminal)
```

Every code-path chain ends at **test-author** (for verification);
diagnostic / review chains (a11y-auditor, sweep-debugger, python-reviewer,
template-reviewer, css-reviewer, security-reviewer, code-reviewer
orchestrator) end with a written report referencing `file:line` evidence
and a hand-off to the relevant author skill.

## Conventions

- Skills carry **what to know** (conventions, files owned, patterns, anti-patterns).
- Agents carry **how to behave** (tool allowlist, when to summon the skill, who to hand off to).
- Both live under `.claude/`, which is gitignored *except* for these two
  subdirectories (`.claude/*` + `!.claude/skills/` + `!.claude/agents/` in
  `.gitignore`).

## Adding a new specialist

1. Create the skill: `.claude/skills/<name>/SKILL.md` with YAML frontmatter
   (`name`, `description`).
2. Create the agent: `.claude/agents/<name>.md` with frontmatter (`name`,
   `description`, `tools:`) and a body that invokes the skill at task start.
3. Add a row to this index and to `.claude/agents/README.md`.
4. If the new specialist hands off to others, update the topology diagram
   above.
