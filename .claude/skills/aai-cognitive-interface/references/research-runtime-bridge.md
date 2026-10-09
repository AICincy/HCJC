# Research Runtime Bridge

The 2025-2026 literature converges on a model-independent execution boundary.

Relevant prior work includes:

- CaMeL: control/data-flow separation and provenance-aware capabilities.
- Fides: deterministic information-flow policy enforcement.
- Progent: deterministic least-privilege policy checking and monotonic confinement.
- PAuth: task-scoped authorization and signed provenance envelopes.
- Commit-Time Authorization: freshness, causal priority, target binding, and commit eligibility.
- IntentCap: task-conditioned capabilities with field-level source ownership and monotonic narrowing.
- SARA: separation of action induction from execution authorization.
- CapSeal: local trusted broker, session-bound capabilities, anti-replay, typed executors, and tamper-evident auditing.
- Sovereign Execution Broker: mandatory broker enforcement, scoped execution credentials, live-state drift checks, and signed outcomes.
- SkillScope: task-conditioned least privilege for reusable Agent Skills.
- Containment Verification: boundary-level safety guarantees independent of model alignment, conditional on effect exclusivity.

## AAI implication

The remaining runtime gap should be solved by a controller/sidecar outside the model process. The controller must become the mandatory mutation path, not an advisory checker beside an otherwise reachable provider.

The literature supports the individual controls. It does not establish that AAI's overall integration is novel. AAI therefore uses a non-novelty posture for individual mechanisms and treats system-level integration as an empirical research question.
