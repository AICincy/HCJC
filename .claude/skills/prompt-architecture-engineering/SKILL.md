---
name: prompt-architecture-engineering
description: >
  Designs and refines high-performance prompts, system instructions, agent
  workflows, and multi-step operating guidance for LLMs. Use when the user
  asks for a system prompt, agent specification, orchestration plan,
  instruction hierarchy, subagent workflow, prompt debugging, skill file
  creation, CLAUDE.md writing, or a cleaner prompt architecture. Also use
  when the user says "write a system prompt," "design an agent," "fix this
  prompt," "make this more reliable," "build a skill," "orchestrate these
  agents," or describes any multi-agent or multi-step LLM workflow. If the
  output is instructions that an LLM will execute, this skill applies.
---

# Prompt Architecture Engineering

## Rules

IF the user asks for a prompt or agent specification:
THEN identify role, task boundary, inputs, outputs, and failure modes
before writing a single instruction line.

IF the brief is underspecified:
THEN return a minimal prompt skeleton plus the missing variables. Do not
pad with guesses.

IF writing a system prompt:
THEN separate permanent rules from task-specific context. Encode workflow
order explicitly: what to do first, what to avoid, when to stop.

IF writing a multi-agent workflow:
THEN define each agent's specific mandate, what it does NOT review, its
exact deliverable, and the coordination rules between agents. Use the
agent/subagent template from the reference doc.

IF the user says "fix this prompt" or "make this more reliable":
THEN diagnose the failure mode first. Common failures: scope creep (no
boundary), drift (critical rules buried in prose), fabrication (no
failure handling), repetition (redundant clauses causing conflicting
interpretation). State the diagnosis, then rewrite.

IF adding examples to a prompt:
THEN use one or two concrete examples. Do not use more than three.
Additional examples reduce variance more than they improve quality.

## Prompt structure (default)

1. Role statement ("You are X").
2. Output format (state before workflow; the model anchors on output shape).
3. Workflow steps with explicit ordering.
4. Hard rules (bullet points, not buried in prose).
5. Failure handling ("If you cannot do X, return Y").
6. Examples (1-2 max).

## Anti-patterns

- Motivational padding ("You are an expert" before "You are a [role]").
- Critical rules in prose paragraphs instead of bullets.
- Conflating goal, workflow, and output format in one section.
- ALL CAPS for emphasis (use bold sparingly or restructure).
- Over-specification that causes drift.

## References

- [references/prompt-templates.md](references/prompt-templates.md): Five
  canonical prompt templates: single-task, multi-step workflow,
  decision-making, verification, and agent/subagent.
