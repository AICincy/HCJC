# JCStream subagents

Fourteen project-specific specialist subagents, each paired with a same-named
skill in `../skills/<name>/SKILL.md`. Spawn one via the `Agent` tool with
`subagent_type: jcstream-<name>` when working in its domain.

| Subagent | Allowed tools | Pair with skill |
|---|---|---|
| [jcstream-template-author](jcstream-template-author.md) | Read, Edit, Write, Bash, Grep, Glob | `jcstream-template-author` |
| [jcstream-stylesheet-author](jcstream-stylesheet-author.md) | Read, Edit, Write, Bash, Grep, Glob | `jcstream-stylesheet-author` |
| [jcstream-build-helper-author](jcstream-build-helper-author.md) | Read, Edit, Write, Bash, Grep, Glob | `jcstream-build-helper-author` |
| [jcstream-orc-curator](jcstream-orc-curator.md) | Read, Edit, Write, Bash, Grep | `jcstream-orc-curator` |
| [jcstream-scraper-author](jcstream-scraper-author.md) | Read, Edit, Write, Bash, Grep, Glob | `jcstream-scraper-author` |
| [jcstream-test-author](jcstream-test-author.md) | Read, Edit, Write, Bash, Grep, Glob | `jcstream-test-author` |
| [jcstream-design-interpreter](jcstream-design-interpreter.md) | Read, Edit, Write, Bash, Grep, Glob, WebFetch | `jcstream-design-interpreter` |
| [jcstream-legal-copy-author](jcstream-legal-copy-author.md) | Read, Edit, Grep, Bash | `jcstream-legal-copy-author` |
| [jcstream-a11y-auditor](jcstream-a11y-auditor.md) | Read, Bash, Grep, Glob, WebFetch | `jcstream-a11y-auditor` |
| [jcstream-sweep-debugger](jcstream-sweep-debugger.md) | Read, Bash, Grep, Glob | `jcstream-sweep-debugger` |
| [jcstream-python-reviewer](jcstream-python-reviewer.md) | Read, Bash, Grep, Glob | `jcstream-python-reviewer` |
| [jcstream-template-reviewer](jcstream-template-reviewer.md) | Read, Bash, Grep, Glob, WebFetch | `jcstream-template-reviewer` |
| [jcstream-css-reviewer](jcstream-css-reviewer.md) | Read, Bash, Grep, Glob | `jcstream-css-reviewer` |
| [jcstream-security-reviewer](jcstream-security-reviewer.md) | Read, Bash, Grep, Glob, WebFetch | `jcstream-security-reviewer` |

Six agents (`a11y-auditor`, `sweep-debugger`, `python-reviewer`,
`template-reviewer`, `css-reviewer`, `security-reviewer`) are intentionally
read-only — their output is a written report, not an edit. The rest edit
files in their owned area.

## Invocation patterns

**Direct ask** — name the specialist:

> "Have the **jcstream-template-author** add a 'Court date' column to
> the charges table on the inmate page."

**Domain ask** — describe the task; the right specialist auto-fires
from its description:

> "Update the FCRA disclaimer on every page." → `legal-copy-author`
>
> "The sweep hasn't produced fresh data in two cycles, what happened?"
> → `sweep-debugger`
>
> "Port this new design package." → `design-interpreter` (which then
> hands off to template-author, stylesheet-author, etc.)

## Handoff topology

See the diagram in `../skills/README.md` — the same topology applies.

## Authoring a new agent

See `../skills/README.md#adding-a-new-specialist` for the full checklist.
At minimum:

1. Frontmatter with `name`, `description`, `tools:` (least-privilege).
2. Body instructing the agent to invoke its paired skill at the start of
   every task.
3. Documented hand-offs to other specialists.
