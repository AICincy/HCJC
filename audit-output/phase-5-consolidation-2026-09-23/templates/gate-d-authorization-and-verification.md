# Gate D authorization and post-deployment verification (fillable form)

The missing half of the release cycle: `pages.yml` verifies the new build against what is **currently live**, before deploying, so nothing in CI checks that the freshly deployed UI works. This form is that check, plus the authorization record that makes it attributable to a human.

## Part 1, authorization (before deployment)

```
GATE D AUTHORIZATION

Candidate commit: [SHA, must match what the gate evidence names]
CI run on that exact commit: [run ID + conclusion]
Gate A determination: [CLOSED | RISK-ACCEPTED] per C1, evidence file:
Gate B determination: [CLOSED | RISK-ACCEPTED] per C1, evidence file:
Gate C determination: [CLOSED | RISK-ACCEPTED] per C2, evidence file:
Gate E rebuild condition satisfied: [Y/N - rebuilt from final reviewed commit]
Isolation merge state: [state + run ID]
Standing notes acknowledged as open: [e.g. d3_sweep PENDING-NEXT-SWEEP; run
  35800597032 pre-fix failure is the item D3 will confirm on the next cron]
Evidence freshness at authorization: [D4 outcome, must not be RENEWAL-REQUIRED]
Deploy path note (F-01): Pages serves committed docs/ on main. Confirm which
  mechanism you believe is deploying, and that the docs/ tree at the candidate
  commit is the tested one.

Named authorizing authority:
UTC timestamp of authorization:
```

## Part 2, post-deployment verification (after, not optional)

```
POST-DEPLOYMENT VERIFICATION

Deployed build identifier: [Pages run ID + SHA]
UTC timestamp of deploy:

Contract and data freshness
  [ ] https://www.aretheyinjail.com/data/current.json is served and parses
  [ ] its generated_utc is within one sweep cycle of main's committed current.json
  [ ] every manifest JSON path from config/public-data-manifest.json returns 200
        with matching shape; run: python scripts/verify_public_data.py locally,
        and gh workflow run live-parity.yml for the CI-side check

Home and search behavior, on a real device
  [ ] Home renders roster cards, not an empty state, in both themes
  [ ] searching an inmate number present in the archive returns that record in
        suggestions and via Enter into the full archive
  [ ] archive filters (charge level) change the result set and reload correctly
  [ ] record page shows charges with case links intact
  [ ] tier badge disclosure opens, shows the focused record, and Escape dismisses it

Accessibility smoke, not a substitute for Gate A
  [ ] tab order from skip link reaches main content with no focus trap
  [ ] table and bond-schedule reading order verified with one AT
  [ ] no new console errors on Home, archive, or a record page

Deployment health
  [ ] pages run conclusion success for the deployed SHA
  [ ] no open issue titled "Site deploy is stale: live roster lags main"
  [ ] if one appears, that is failure class 1 in gate-d-failure-path.md

Verifier name:
UTC timestamp:
Result: [PASS | FAIL(class)]
```

## Part 3, disposition

| Result | Next step |
| :-- | :-- |
| PASS, all boxes | C4 records Gate D closed. Release readiness report gains the deployed build identifier, which `closure/README.md:119` still lists as unavailable |
| FAIL class 1 | `gate-d-failure-path.md` Step 0, then class 1 routing. Do not revert to fix queueing |
| FAIL class 2a | Rollback Authorization Record, including the data-staleness cost field |
| FAIL class 2b | D1-structured defect plus `GATE-D-CONDITIONAL: [defect ID] open; release is live but not fully verified` in the sign-off row |
| Any box left unchecked | State why it is unchecked. `Not run` is a valid entry; a silent gap is not |

This form creates no gate determination. C4 reads it. An unchecked box here is exactly the "missing coverage must remain explicit" requirement already written in `manual-qa-checklist.md`.
