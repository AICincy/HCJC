# Trusted Runtime Controller Deployment

## Required topology

```text
agent process
      |
      | untrusted request
      v
AAI trusted controller service
      |
      | exact verified execution request
      v
provider-specific executor
      |
      v
external mutation
```

The agent process MUST NOT retain a reusable mutation credential that can bypass the controller.

## Deployment requirements

1. Run the controller as a separate service account.
2. Store controller signing keys outside model- or agent-writable skill directories.
3. Store issuer verification keys separately from the agent process.
4. Make provider mutation interfaces reachable only through broker-owned identities, credentials, proxies, or admission controls.
5. Record signed, hash-chained receipts outside agent-writable state.
6. Fail closed when the verifier, policy store, or receipt writer is unavailable.
7. Verify the canonical governing skill directory from the controller itself.

## What this enables

Each of these statuses requires its own current evidence:

```text
INSTALLED
RUNTIME-SMOKE-PASS
RUNTIME-VERIFIED
```

`ADVERSARIAL-PASS` additionally requires the adversarial suite and a real external authorization path.

## Bypass condition

If the agent can reach the provider mutation path without the controller, the controller is advisory, not authoritative. Report runtime enforcement as `INCONCLUSIVE`.
