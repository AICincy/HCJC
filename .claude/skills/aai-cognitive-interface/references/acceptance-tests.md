# AAI Runtime Acceptance Tests v0.4.0

The reference controller MUST pass these negative controls before any runtime status is promoted:

```text
fake grant signature -> deny
scope mutation -> deny
parameter provenance mutation -> deny
schema identity mutation -> deny
skill identity mutation -> deny
expired grant -> deny
revoked grant -> deny
policy epoch drift -> deny
target state drift -> deny
nonce replay -> deny
provider capability missing -> deny
receipt forgery -> deny
```

Positive control:

```text
exact externally issued grant + exact canonical action + fresh target state
-> allow exactly once
```

The positive control is not valid when the trusted issuer/verifier is simulated by user text or model output.

Runtime status requires the controller process, not the test harness, to produce the evidence.
