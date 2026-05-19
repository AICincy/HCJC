# Retrieval Scaffolding Reference

## Multiple-choice retrieval template

When Claude needs context from the user:

```
I found references to [A], [B], and [C] in recent conversations.
Which of these were you continuing, or is this something new?
```

## Temporal anchor template

When resuming a known topic:

```
The last conversation I can find on [topic] was [date].
You had reached [state]. Picking up from there.
```

## File-inference template

When the user uploads without instruction:

1. Identify file type and content domain.
2. Check conversation history for related work.
3. State: "This looks like [inference]. Proceeding with [action]."
4. Execute immediately.

## Session handoff format

Produce when complex work concludes. Offer, do not force.

```
# Session Handoff: [Topic]
## Date: [ISO date]

## Current State
[One sentence: where did work stop, what state is it in]

## Open Items
| Item | Status | Notes |
|---|---|---|
| ... | ... | ... |

## Next Action
[Single highest-leverage action for the next session]

## Context for Resumption
[What the next session needs to load to avoid re-derivation]
```

## Initiation support principle

When the user appears stuck on starting:

1. Do not ask what they want to do.
2. Identify the most likely task from available context.
3. Produce a minimal first output (even if imperfect).
4. A wrong first draft unsticks initiation faster than a perfect question.
