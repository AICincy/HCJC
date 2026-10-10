# AAI Trusted Controller Contract

## Purpose

The trusted controller is the execution boundary between agent reasoning and consequential external effects.

The agent MAY propose an action. The controller MUST independently determine whether the action is authorized and MUST be the only reachable mutation path for protected effects.

## Trust boundary

```text
agent instructions / skills / retrieved content
        |
        | untrusted proposal
        v
trusted controller
  - canonicalization
  - grant signature verification
  - exact scope/action binding
  - provenance validation
  - skill/schema binding
  - expiry/revocation/replay
  - policy epoch
  - live-state validation
        |
        | only verified request
        v
provider adapter / mutation interface
        |
        v
external effect
```

## Effect exclusivity

A controller is not an enforcement boundary if the agent can reach the protected mutation interface without passing through the controller. Deployment MUST therefore remove standing mutation credentials from the agent process or otherwise make the controller the mandatory policy enforcement point.

## Grant

A consequential grant MUST bind:

```text
grant_id
subject_id
operation
resource_scope
scope_hash
environment
issued_at
expires_at
nonce
replay_state
issuer
status
policy_epoch
tool_id
schema_hash
skill_id
skill_hash
parameter_provenance
```

The controller MUST reject malformed, unsigned, expired, revoked, replayed, or mismatched grants.

## Commit boundary

Immediately before the external effect, the controller MUST revalidate the exact canonical action, target identity, scope hash, operation, skill/schema identity and digest, policy epoch, provider capability, approval or grant freshness, revocation, nonce, parameter provenance, and current target state. Any material change removes commit entitlement.

## Failure behavior

The controller MUST fail closed on verifier or policy failure.

```text
BLOCKED: VERIFIED_EXTERNAL_GRANT_REQUIRED
BLOCKED: AUTHORIZATION_VERIFIER_UNAVAILABLE
BLOCKED: AUTHORIZATION_SCOPE_MISMATCH
BLOCKED: AUTHORIZATION_STATE_DRIFT
```

## Receipt

Every consequential attempt MUST produce a signed receipt containing the grant identifier, subject, operation, scope, verification result and reason, policy state, nonce state, execution result, timestamp, receipt-chain linkage, and controller signature.

## Status evidence

`PACKAGE-PRESENT` means the package exists. `STATIC-PASS` requires the deterministic package gate. `INSTALLED` requires independent runtime-path verification. `RUNTIME-SMOKE-PASS` requires a live task through the controlled path. `RUNTIME-VERIFIED` requires repeated fresh checks. `ADVERSARIAL-PASS` requires the defined adversarial suite plus a real trusted authorization path.

Never promote one label without the required evidence.
