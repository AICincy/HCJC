# Prompt Architecture - Template Library

**Last updated:** May 6, 2026

Five canonical prompt structures. Each template is a starting point. Customize per task.

## Template 1 - Single-Task Instruction Prompt

For prompts that perform one well-defined task without multi-step orchestration.

```
You are [role].

Your task is to [single specific action] given [input description].

Constraints:
- [Constraint 1]
- [Constraint 2]
- [Constraint 3]

Output format:
[Exact output specification]

Failure modes:
- If [condition], return [fallback].
- If [condition], return [fallback].

Example input:
[Concrete example]

Example output:
[Concrete output corresponding to the example input]
```

## Template 2 - Multi-Step Workflow Prompt

For prompts orchestrating a sequence of dependent steps.

```
You are [role].

Your overall task is [high-level outcome]. Execute it as a fixed sequence of steps.

Step 1: [Action]
- Inputs: [Input source]
- Outputs: [What this step produces for the next step]
- Stop condition: [When this step is complete]

Step 2: [Action]
- Inputs: [Output of Step 1 plus any additional]
- Outputs: [What this step produces]
- Stop condition: [When this step is complete]

Step 3: [Action]
- ...

Hard rules across all steps:
- [Rule 1]
- [Rule 2]

If a step fails, return the partial result with a clear note about the failure point. Do not continue past a failed step.
```

## Template 3 - Decision-Making Prompt

For prompts that select an option from alternatives based on stated criteria.

```
You are [role]. You are deciding [decision question].

Available options:
1. [Option A]
2. [Option B]
3. [Option C]

Decision criteria, in priority order:
1. [Criterion 1] (must-have)
2. [Criterion 2] (must-have)
3. [Criterion 3] (preference)

Process:
1. Evaluate each option against each criterion.
2. Eliminate options that fail any must-have.
3. Among remaining options, rank by preference criteria.
4. Recommend the top option.

Output:
- Comparison table
- Recommendation
- One-paragraph rationale
- What would change the recommendation
```

## Template 4 - Verification Prompt

For prompts that audit, validate, or check output against a specification.

```
You are [role]. You are verifying that [target artifact] meets [specification].

Specification:
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

Verification process:
1. Read the target artifact.
2. For each requirement, check whether the artifact satisfies it.
3. Record pass / fail / partial / unverifiable per requirement.
4. For each failure, cite the specific element of the artifact that fails.

Do not modify the artifact. Do not propose alternatives. Verify only.

Output:
| Requirement | Status | Evidence |
|-------------|--------|----------|
| [...] | [...] | [...] |

Summary:
- Total requirements: [N]
- Passed: [N]
- Failed: [N]
- Unverifiable: [N]
```

## Template 5 - Agent / Subagent Prompt

For prompts intended to run as a named agent within a larger orchestration.

```
You are the [Agent Name]. You operate as one of multiple agents reviewing [domain].

Your specific mandate: [What this agent specifically reviews; what it specifically does not review.]

Inputs you will receive:
- [Input 1 with format]
- [Input 2 with format]

Your specific deliverable:
- [Exact deliverable]

Coordination rules:
- You operate independently of [other agents]. Do not assume their findings.
- Disagree with [other agents] when warranted. Disagreement is your job.
- Do not synthesize across agents. Synthesis is a separate step.

Voice: [Specific voice characteristics for this agent's output]

End your output with: "**Verdict: [VERDICT]**"
```

## Cross-Template Rules

- Specify the role explicitly. "You are X" outperforms implicit role.
- State the output format before the workflow. The model anchors on the output shape.
- Provide one or two concrete examples. Do not provide more than three; additional examples reduce variance more than they improve quality.
- State failure handling explicitly. "If you cannot do X, return Y" prevents the model from inventing.
- Keep prompts short. Every clause is a constraint the model tries to honor; redundant clauses cause drift.

## Anti-Patterns

- Do not pad with motivational language. "You are an expert" before "You are a [role]" adds no information.
- Do not put critical rules in prose. Use bullet points.
- Do not conflate goal, workflow, and output. Each gets its own section.
- Do not over-specify. The model interprets ambiguity better than rigid pseudo-code.
- Do not use ALL CAPS for emphasis. Use **bold** sparingly or restructure the prompt.
