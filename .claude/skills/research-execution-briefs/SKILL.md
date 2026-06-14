---
name: research-execution-briefs
description: >
  Executes scoped research and returns decision-ready briefs with source-backed
  findings, comparisons, open questions, and next actions. Use when the user
  asks to research a topic, investigate something, compare options, verify
  current guidance, gather official sources, or turn a broad question into a
  concise brief. Also use when the user says "look this up," "research this,"
  "what are my options," "find out if," "investigate," "what does the law say
  about," or asks any question that requires consulting multiple sources before
  answering. If the answer requires more than one source, this skill applies.
---

# Research Execution Briefs

## Rules

IF the user asks an open-ended research question:
THEN narrow the scope before gathering sources. State the narrowed scope
in one sentence. Proceed with research within that scope.

IF the question is time-sensitive:
THEN search for content within the relevant recency window before
consulting older sources. Note the source date in the brief.

IF sources conflict:
THEN present both positions with their respective sources. State which
source carries more authority using the source hierarchy. Do not
resolve the conflict by choosing one without stating the basis.

IF the research cannot answer the question from available sources:
THEN return a narrowed research frame and source plan instead of
fabricating completeness. State what was searched and what came back
empty.

## Source hierarchy

| Tier | Sources |
|---|---|
| 1 (Primary authority) | uscode.house.gov, ecfr.gov, codes.ohio.gov, issuing court opinions, agency official documents, peer-reviewed journals |
| 2 (Secondary authority) | CourtListener, Justia, National Law Review, AP/Reuters, Google Scholar |
| 3 (Reference) | Wikipedia (with date caveat), textbooks, practice guides |
| 4 (Last resort) | Stack Exchange, practitioner blogs, forums |

Cite Tier 1 directly when available. Cite lower tiers only when higher
tiers are silent. Label the tier in the brief.

## Output structure

1. Question (one sentence).
2. Scope (what was searched, what was excluded).
3. Findings (ranked by usefulness to the user's decision).
4. Source map or comparison table.
5. Uncertainty (what remains unresolved).
6. Next actions (concrete steps if the user needs to act).

## References

- [references/source-hierarchy.md](references/source-hierarchy.md): Full
  four-tier source taxonomy, inadmissible categories, recency rules, and
  source diversity requirements.
