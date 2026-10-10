---
name: prompt-architecture-engineering
description: Designs and refines prompts, system instructions, agent workflows, and the agent runtime SKILL.md packages. Use when the user asks for a system prompt, agent spec, instruction hierarchy, prompt debugging, or skill creation. Also use when the user says write a system prompt, design an agent, fix this prompt, or create a SKILL.md package.
---

# Prompt Architecture Engineering

## AAI interoperability contract

`aai-cognitive-interface` is the mandatory governing runtime on every
invocation. This skill is a subordinate domain module that supplies prompt and
agent architecture methods only. It must not override, narrow, suspend, or
reinterpret AAI. AAI governs runtime state, interaction, continuation,
corrections, cognitive-ceiling takeover, artifact completion, and
evidence/status claims. Platform and safety instructions remain authoritative.

Accept AAI's recovered objective, authorized scope, hard constraints,
authoritative inputs, next executable action, completion evidence, and any
human-only gate as the control state. Execute routine in-scope design,
revision, validation, and persistence without returning sequencing or tool
selection to Krass. Continue until the prompt's acceptance checks pass or one
actual gate or blocker remains. Treat corrections as hard constraints and
revalidate every affected instruction.

A successful prompt review proves domain validation only. It does not prove
`SAVED`, `INSTALLED`, `RUNTIME-SMOKE-PASS`, `RUNTIME-VERIFIED`, or
`ADVERSARIAL-PASS` without AAI's required evidence.

The canonical directory name is `prompt-architecture-engineering`. Treat
hashed export folders as transport wrappers. See
[references/package-identity.md](references/package-identity.md),
[references/architecture-state.md](references/architecture-state.md), and
[references/sibling-routing.md](references/sibling-routing.md).

Do not invent tools. Do not flatten AAI under a new system prompt. Unknown
host behavior stays an assumption or blocker. If AAI is absent, say so and do
not write a self-governing skill.

## the agent runtime adaptation

the agent runtime skills are a folder with `SKILL.md`. Frontmatter uses `name` (lowercase
letters, digits, hyphens; matches the folder) and `description` (under 1024
characters, with the trigger conditions). Put procedure in the body and detail in
`references/`, `scripts/`, and `assets/`. Skills load read-only from
`the configured skill directory/`, so scripts write to `/home/the agent runtime` or `/mnt/user-data/outputs`.
Connector tools are deferred and load with `runtime tool discovery`. Never invent tool names.
Validate the format with
`python3 /mnt/skills/examples/skill-creator/scripts/quick_validate.py <dir>`.

## the host runtime and GPT-5.6 Sol adaptation

Design for the instruction hierarchy actually available to the target model.
For the host runtime or GPT-5.6 Sol, preserve system/developer/user precedence, treat
workspace instructions such as `AGENTS.md` as scoped repository rules, and
never invent tool names or capabilities. Discover the tools and skills exposed in
the current session, then bind workflows to those concrete capabilities.

When authoring a the host runtime skill, keep trigger conditions in the `description`
frontmatter and procedural instructions in the body. Use only `name` and
`description` in `SKILL.md` frontmatter. Prefer progressive disclosure through
`references/`, `scripts/`, and `assets/` instead of a monolithic prompt.

For GPT-5.6, prefer lean, outcome-focused instructions over restating model
behavior. Define the goal, relevant context, hard constraints, autonomy or
approval boundaries, required evidence, success criteria, and output contract.
State each durable rule once. Preserve examples or style guidance when they
encode a real product requirement or repair a measured failure.

## Rules

IF the user asks for a prompt or agent specification:
THEN identify outcome, task boundary, relevant inputs/context, authority and
approval boundaries, success criteria, output contract, and material failure
modes before writing the instruction set.

IF the brief is underspecified:
THEN infer reversible task-local details when context supports them and state
material assumptions. Ask only when a missing value changes the objective,
acceptance criteria, authority boundary, or an irreversible action. If the
unknown truly blocks useful work, return the smallest actionable skeleton plus
the missing decision.

IF writing a system prompt:
THEN separate durable rules from task-specific context. Encode dependencies,
tool routing, stop conditions, safe recovery, and verification only to the
degree the workflow needs them. Do not force a fixed sequence onto work that
can proceed independently.

IF writing a multi-agent workflow:
THEN delegate only concrete workstreams that are independent enough to benefit
from parallel execution or focused context. Give each subagent the minimum
task-local context, a bounded mandate, and exact deliverable. Bound concurrency
to the workload. Avoid duplicate review unless independent disagreement is the
point. The root/orchestrator owns synthesis, conflict resolution, and final
verification. Prefer one agent for linear chains or shared mutable state.

IF the user says "fix this prompt" or "make this more reliable":
THEN diagnose the failure mode first. Common failures: scope creep (no
boundary), drift (critical rules buried in prose), fabrication (no
failure handling), repetition (redundant clauses causing conflicting
interpretation). Patch the active artifact at the smallest layer that fixes the
measured failure. Validate instruction hierarchy, tool names, internal
contradictions, success criteria, and recovery behavior. Iterate against the
failure case. Rewrite wholesale only when the architecture itself is the failure.

IF adding examples to a prompt:
THEN add only examples that disambiguate behavior, encode a product
requirement, or repair a measured gap. There is no fixed example count. Test
whether each example earns its context cost.

## Prompt structure (default)

1. Outcome and task boundary.
2. Relevant context, inputs, and authority/approval boundaries.
3. Success criteria, required evidence, and output contract.
4. Dependencies and tool-routing rules when tools are part of the task.
5. Workflow ordering only where dependencies require it; identify parallel
   branches when useful.
6. Stop conditions, safe recovery, and verification.
7. Examples only when they disambiguate behavior or encode a requirement.

## Anti-patterns

- Motivational padding ("You are an expert" before "You are a [role]").
- Critical rules in prose paragraphs instead of bullets.
- Conflating goal, workflow, and output format in one section.
- ALL CAPS for emphasis (use bold sparingly or restructure).
- Over-specification that causes drift.
- Duplicating the same autonomy, style, or safety rule in multiple layers.
- Making subagents the default when the task is a short linear chain.

## Civic-legal skill family

IF the task involves building, editing, or auditing a skill in the
civic-tech/legal-advocacy family (authority-currency-auditor,
claim-source-auditor, forensic-evidentiary-drafting,
regulatory-complaint-drafting, record-series-builder,
research-execution-briefs, or a new skill in the same project):
THEN load
[references/civic-legal-skill-patterns.md](references/civic-legal-skill-patterns.md)
first. Apply the documented patterns by reference. Flag any deviation and
state why.

IF building or editing any personal skill used with Krass:
THEN make `aai-cognitive-interface` the mandatory governing runtime. Define
the domain skill as a subordinate module that cannot override, narrow,
suspend, or reinterpret AAI. Give it a narrow subject-matter boundary,
accept AAI's runtime state, keep domain statuses distinct from AAI
artifact/runtime statuses, and do not restate AAI's global writing rules.

## References

- [references/prompt-templates.md](references/prompt-templates.md): Five
  canonical prompt templates: single-task, multi-step workflow,
  decision-making, verification, and agent/subagent.

- [references/civic-legal-skill-patterns.md](references/civic-legal-skill-patterns.md):
  Shared structural patterns across the civic-tech/legal-advocacy skill
  family, for consistent new-skill construction and drift audits.

- [references/architecture-state.md](references/architecture-state.md):
  Host, tools, evidence, and static-vs-runtime bounds.

- [references/sibling-routing.md](references/sibling-routing.md): Governor
  and sibling degrade rules.

- [references/package-identity.md](references/package-identity.md): Name,
  wrapper folders, and claimable status.

- [references/acceptance-tests.md](references/acceptance-tests.md):
  Behavior cases after a material revision.

When filesystem execution is available, run
`python3 scripts/aai_runtime_gate.py package <skill-directory>` after
modifying this skill. That is STATIC-PASS only.
