# Audit — `claude-api` (personal/harness skill)

- **Date**: 2026-05-14
- **Applicability**: None
- **Recommendation**: Keep enabled (harmless; will not auto-fire)

## What it does
Builds, debugs, optimizes, and version-migrates apps that call the Claude API via the Anthropic SDK, with prompt caching as a default.

## Fit for JCStream
`grep -rn "anthropic\|Anthropic" --include="*.py"` and the same for `openai` return zero hits. `requirements.txt` pins only `httpx`, `selectolax`, `pydantic`, `jinja2`, `Pillow`, `pytest` — a static-site/scraping stack with no LLM runtime. JCStream uses Claude Code as a development tool, not as a runtime dependency; the skill's trigger conditions therefore never match this codebase.

## Realistic triggers in this project
- None under the current architecture.
- Hypothetical only: if someone adds an LLM-backed feature (e.g. auto-generated ORC explainers, charge summarization, photo-captioning) it would then apply — but that would be a deliberate new direction, not in scope today. The existing `jcstream-orc-curator` skill maintains explainers by hand.

## Risk
None — the skill's trigger conditions (anthropic imports, Claude API questions, model-feature edits) cannot match anything currently in this repo, so it stays dormant.

## Recommendation rationale
Leave enabled. It is gated on imports and explicit Claude API/SDK language, neither of which exist in JCStream, so it imposes no cost on day-to-day work. Disabling it would only matter if it were misfiring, and there is nothing here for it to misfire on. If an LLM feature is ever added, the skill becomes immediately useful with no reconfiguration; until then it is inert.
