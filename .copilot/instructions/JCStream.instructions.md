# JCStream: working notes for Copilot

Purpose
- Provide persistent, project-specific agent instructions for the JCStream repository.

Scope
- Applies to routine scraper/pipeline maintenance, build helpers, and small bug fixes in this repo.
- Does not authorize design, CSS, or template changes unless explicitly requested in-session.

Hard rules (must obey)
- Scope gate: Before writing any code, state the task in one sentence and wait for confirmation.
- Single-step rule: Do not create multi-phase plans. One task, one fix; confirm before the next task.
- No design changes without explicit per-session authorization.
- Use direct read/write tools for edits; do not hand off required filesystem actions to the owner.
- Run `python -m pytest -q` before committing. If tests fail, fix them. Do not commit with failing tests.
- Verify the live site with `curl` before claiming about appearance; ask for screenshots if "broken" is reported.
- Never lower `SWEEP_MAX_FAILED_FRACTION` or `SWEEP_MIN_ROSTER_FRACTION` to bypass the degraded-roster guard.

Communication rules
- No filler. One idea per sentence. Active voice. No softening language.
- When wrong: one sentence acknowledging, one sentence correcting, then re-execute.
- Do not ask clarifying questions unless ambiguity risks material error. If inferred, execute and state assumptions inline.

Execution rules
- Match fix scope to problem scope. One-line bug → one-line fix. Avoid unrelated refactors.
- Use direct tools (read/write/patch). If a tool can perform the action, perform it.
- Full filesystem, git, and network access may be used; if an operation fails, report the error and retry appropriate alternatives.

Menu system (required at session end)
- When a chunk of work wraps up, present the owner with a multiSelect menu of explicit next steps.
- For each option state: what it does and why; mark one recommended option.
- Never offer "stop here" or "do nothing" as an option. Do not tag any option as "recommended: stop".
- "Implement all suggestions" means perform all options in the last menu; ensure menu items are concrete and actionable.

Repo facts (reinforced)
- Build locally: `JCSTREAM_SITE_BASE_URL="" python -m web.build`
- Tests: `python -m pytest -q` (must stay green)
- Sweep cadence: GitHub Actions cron every 15 minutes with a 20-minute skip gate; effective cadence ~20-45 minutes.
- The sweep refuses to write a degraded roster; this guard is deliberate and must not be weakened.

Examples: prompts that exercise this instruction
- "Fix the one-line parsing error in `scraper/parsers.py` — task: update parse_date() to accept new format."
- "Run tests and commit branch `copilot/jcstream-instructions` after saving these instructions."

Ambiguities to confirm
- Whether this instruction should auto-apply to all files or only to scraper and build files. (Suggest: applyTo `scraper/**`, `web/**`, `data/**`.)

Saved path
- /workspaces/HCJC/.copilot/instructions/JCStream.instructions.md
