# Stale-artifact publish and the misdiagnosed "Pages queue" (2026-09-24)

Incident record for the ~208-minute production lag observed after PR #503 merged,
and for a remediation document that diagnosed it incorrectly. Companion to
[24_pages_deploy_stale_incidents.md](./24_pages_deploy_stale_incidents.md) (the
`deploy_alert` incident log), the `CLAUDE.md` sections "Pages deploy:
branch-serving is the live path" and "Live-Parity HTML Freshness SLA", and
[audit-output/full-stack-audit-2026-09-24.md](../audit-output/full-stack-audit-2026-09-24.md).

## Audit metadata

- Date: 2026-09-24
- Trigger: a handoff document ("Production Remediation: Corrected Technical
  Analysis") circulated with a force-push remediation tier, a claim that the
  Pages webhook was still pending, and a claim that the agent's token had been
  revoked. Each was checked against the GitHub API, the Actions/deployment
  history, and local rebuilds. The webhook-pending claim was wrong; the
  force-push prohibition was right; the token claim was half right — scoped, not
  revoked, and the capability matrix below records which operations actually 403.
- Author: Arena agent session `arena/01a0d152-hcjc`, verified against the GitHub
  API, Actions history, and two independent local builds at write time.
- State at write time: `main` = `5d90340`; branch `arena/01a0d152-hcjc` carries
  the regenerated `docs/`, `tests/test_build_determinism.py`, and this record,
  raised as PR #504 (Lint + Deno green).

## Summary

The lag was **not** a stuck Pages webhook. Pages deployed `5d90340` successfully
at `2026-09-24T02:44:59Z`. The lag was the age of the roster itself: the last
scheduled sweep ran at `23:27Z` and no sweep had run since, because the hourly
cron drifts by hours. Separately, the `docs/` tree published at that merge had
been built by *pre-fix* code, so it shipped non-deterministic artifacts even
though the determinism fix was live in the same commit.

Three distinct problems were conflated into one "Pages deployment is pending"
narrative. They have different causes and different fixes.

## What was actually verified

All timestamps UTC. Observed at ~`03:00Z` on 2026-09-24.

| Check | Result | Evidence |
| :-- | :-- | :-- |
| `main` tip | `5d903407b1`, merged `2026-09-24T02:43:57Z` | `GET /repos/AICincy/HCJC/commits/main` |
| Pages source | `build_type=legacy`, `main` + `/docs`, `status: built` | `GET /repos/AICincy/HCJC/pages` |
| `pages-build-deployment` | **success**, 36s, ~8 min before observation | run `35948486860` |
| `pages` (Actions artifact) | **success**, both jobs, 58s | run `35948487541` |
| Latest Pages deployment | `5d903407b1`, status `success` at `02:44:59Z` | deployment `6629019162` |
| `data/current.json` | `generated_utc = 2026-09-23T23:35:42Z` | local + `git show HEAD:` |
| `docs/data/current.json` | `2026-09-23T23:35:42Z` — in sync | local + `git show HEAD:` |
| HTML stamps | 1214/1214 carry `jcstream:generated-utc` = `23:35:42Z` | `grep -rl` over `docs/` |
| Last scheduled sweep | started `23:27:20Z`, ended `23:36:15Z`, success | run `35933680491` |
| Test suite | 803 passed | `pytest tests/ -q` |
| Lint / types | ruff clean, mypy clean (45 files) | `ruff check .`, `mypy scraper web` |

### The lag arithmetic

Roster vintage `23:35:42Z`; observation time `~03:00Z` on the 24th. That is
~205 minutes — the reported "208 min". It is the age of the **data**, measured
from the last successful sweep. Nothing about the deploy was pending: the deploy
of that data had completed at `02:44:59Z`, minutes earlier.

## Root cause: three problems, one narrative

### 1. The `/tmp`-build defect (real, already fixed before this session)

`CLAUDE.md` records it and commit `5790d1a16d` (01:07:50Z) fixed it:

> Pages is still `build_type=legacy` (Deploy from a branch). Sweep and rebuild
> were building into `/tmp` and committing only `data/`, so every successful
> `pages-build-deployment` republished the frozen `docs/` skeleton while main's
> roster stayed current (issue #496, lag alarm 275 min).

This is the cause behind the recurring "Site deploy is stale" alerts (#483,
#487, #496). It is **not** a failed or queued webhook — those jobs report
success while publishing a stale skeleton. `sweep.yml` and `rebuild.yml` now
build into `docs/` and commit `data/` + `docs/`, guarded by
`tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs`.

### 2. Stale artifacts published *by the determinism merge itself* (found here)

PR #503 anchored the build clock to the roster vintage (`web/build.py:412` →
`set_build_now_from_utc(snapshot.generated_utc)`). The fix is correct, but the
`docs/` tree committed at merge `5d90340` had been generated at `01:07:24Z` by
`5790d1a16d` — that is, by pre-fix code. So the branch-serve deploy published
pre-fix artifacts while every gate stayed green:

```
docs/data/transparency_metrics.json (as committed at 5d90340)
    computed_utc      2026-09-24T01:07:24Z   <- wall-clock at build time
    freshness_hours   1.5                    <- age of the docs BUILD
    roster_age_hours  1.5
data/current.json
    generated_utc     2026-09-23T23:35:42Z   <- the anchor the fix requires
```

Rebuilding from the same committed `data/` with the merged code yields the
anchored values (`computed_utc = 2026-09-23T23:35:42Z`, both ages `0.0`) and
changes **654 files** — 655 with `SHA256SUMS`, 1316 insertions against 1316
deletions, i.e. value changes with no structural churn.

Two variance sources, both wall-clock:

- `transparency_metrics.json` — `computed_utc` / `freshness_hours` /
  `roster_age_hours` carried the build's wall-clock time.
- Inmate timeline positions — `web/shape/timeline.py` derives `now_x`, `end` and
  `_days_in_custody` from `_now_naive_est()`. Observed drift is ~0.1% of the
  timeline per rebuild (`width: 7.0%` → `6.9%`), so pages never settle
  byte-identical while the clock is unanchored.

The published effect is not cosmetic: `freshness_hours` feeds the `STALE`
verdict against `stale_alarm_hours = 6.0`. Anchored at `01:07:24Z` instead of
the roster's `23:35:42Z`, the transparency page measures the roster's age from
the wrong origin and under-reports staleness by ~1.5 h.

**Why no gate caught it.** `verify_live_html_freshness.py` reads the
`jcstream:generated-utc` *meta stamp*, which was correct in all 1214 files.
Nothing compared the committed `docs/` artifacts against what the committed code
produces. The internal checksum manifest could not help either: at `5d90340`
`docs/data/SHA256SUMS` hashed the same stale bytes it shipped (both
`89f5e378…`), so the tree was self-consistent while being wrong.

### 3. Cron drift, not webhook lag (the actual reason the roster aged)

`sweep.yml` declares `cron: '0 * * * *'` but its own comment concedes "Actions
cron is best-effort with multi-hour gaps". Observed scheduled-run starts:

```
05:37:24Z  11:01:45Z  16:22:49Z  20:00:18Z  23:27:20Z
     5h24m       5h21m       3h37m       3h27m
```

Not hourly. `scraper/deploy_alert.py` says the same ("cron */15; observed gaps
2-5h" — itself stale, the cron is hourly now). With the last sweep at `23:36Z`
and a ~210 min lag at `03:00Z`, the roster was simply awaiting a sweep that the
cron would not reliably deliver.

## Corrections to the handoff document

| Document claim | Verified status |
| :-- | :-- |
| "Pages Publication ⏳ Pending — waiting for webhook" | **Wrong.** Deployment `6629019162` of `5d903407b1` succeeded at `02:44:59Z`; `pages-build-deployment` run `35948486860` success in 36s. |
| Root cause "Pages Deployment: webhook published async; no fallback when stuck" | **Wrong.** `CLAUDE.md` already records the true cause (`/tmp`-only builds), fixed by `5790d1a16d` before this session. |
| "208 min lag is NOT missing docs/ … is Pages deployment not yet published" | **Half right, wrong conclusion.** `docs/` was present and deployed; it was *stale*, built by pre-fix code. The 208 min is roster age from cron drift. |
| Tier 1: "Next sweep at next hour boundary. If 23:40 UTC now, sweep runs at 00:00 (~20 min)" | **Wrong and unsafe to rely on.** No sweep ran at `00:00Z` or `01:00Z` or `02:00Z`. Observed gaps are 3.5–5.5 h. Manual dispatch is the reliable path, not waiting. |
| Tier 2: "Owner must dispatch manually — bot token revoked, no `actions:write`" | **Half right, and the operative half is correct.** `gh workflow run sweep.yml --ref main` failed with `HTTP 403: Resource not accessible by integration` on `/actions/workflows/277044658/dispatches`, so dispatch genuinely must go through the UI. The *reason* is wrong: the token is not revoked. |
| "Session now CLOSED (token revoked post-merge)" | **Wrong.** `gh auth status` = authenticated as `arena-ai-coding-agent[bot]`. The token is live and useful; it is scoped, not revoked. See the capability matrix below. |

### Bot capability matrix, measured not assumed

`GET /repos/AICincy/HCJC` reports `permissions` all-`false` for this
installation, which is **not** a reliable guide — `git push` succeeded despite
`push: false`. Measured behaviour:

| Operation | Result |
| :-- | :-- |
| REST reads (commits, pages, deployments, runs) | **works** |
| `gh run list` / `gh run watch` | **works** |
| `git push origin arena/01a0d152-hcjc` | **works** |
| `gh pr create` / `gh pr edit` via REST PATCH | **works** (PR #504) |
| `gh workflow run sweep.yml --ref main` | **403** — no `actions:write` |
| `gh issue comment 496` / `502` | **403** — no `issues:write` |
| `gh pr edit` via GraphQL | fails on an unrelated `Projects (classic)` deprecation; the REST PATCH path works |

So the handoff document was right that the owner must dispatch the sweep by hand,
and right that commenting on the issues is not something an agent can do here —
but wrong that the session or token was dead. Planned work should be scoped to
branch push + PR, with dispatch and issue comment handed to the owner.

Because issue comments are blocked, the traceability notes for #496 and #502 live
in this record and in the PR #504 description instead of on the issues. Both
issues are CLOSED and the open-issue count is 0, so no `deploy_alert` alarm is
latched open (the dedupe latch described in
[24_pages_deploy_stale_incidents.md](./24_pages_deploy_stale_incidents.md) is
clear).
| Success criterion "docs/ rebuilds to byte-identical (≤1s rebuild time, 0 diff)" | **Unmet as stated.** Rebuild is ~12–18 s, not ≤1 s. Byte-identity holds between two builds of the *current* code (0 diff, identical tree hash `e9794f7a…`), but committed `docs/` differed from it in 654 files until regenerated. |
| "Document findings in issue #502" | **Blocked twice over.** #502 and #496 are both CLOSED (#502's only workflow run was `skipped`), and `gh issue comment` returns 403 — no `issues:write`. Findings are recorded here and on PR #504 instead. |
| "DO NOT `git push -f origin main`" | **Correct and endorsed.** Consistent with `runbooks/live-parity-failure.md` §4.3 ("Do not hand-edit `docs/` or force-push generated output") and `DECISIONS.md` (owner enabled block-force-push + block-deletion on `main`). |
| "Determinism Fix ✅ Complete" | **Code: yes. Artifacts: no** — see §2 above. |

The document's `curl https://www.aretheyinjail.com/` verification step could not
be run from this sandbox: egress to the custom domain fails at TLS
(`SSL_ERROR_SYSCALL`) while `api.github.com` returns 200. Live-site checks here
must be run from a network that can reach the domain; that is an environment
limit, not evidence about the site.

## Remediation applied in this session

1. **Regenerated `docs/`** from committed `data/` with the merged deterministic
   code (`JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com
   python -m web.build`). 655 files, no structural churn, preserved files
   (`CNAME`, `FRAMEWORK-REVIEW-2026-09-20.md`) intact via `PRESERVED_FILES`.
2. **Proved determinism**: two independent builds into scratch dirs diffed to 0;
   in-place rebuild reproduced tree hash `e9794f7ab342e63dc12f9fe099346e9578b0ba385e3efb045333f91625ad9dfa`
   exactly.
3. **Added `tests/test_build_determinism.py`** (4 tests) so a stale published
   artifact cannot merge silently again:
   - `computed_utc == data/current.json:generated_utc` — the guard that catches
     §2. Verified to fail against the pre-fix artifact and pass against the
     regenerated one.
   - `build()` anchors the clock before `_render_build(...)` and clears it after
     — the wiring existing timeline tests bypass by monkeypatching
     `_now_naive_est` (`tests/test_shape.py:44,319`).
   - the anchor resolves the vintage to naive Eastern and clearing resumes
     wall-clock (the empty-bootstrap path).
   - `docs/data/SHA256SUMS` matches `docs/data/*.json` — guards *partial*
     rebuilds, not §2 (recorded honestly in the test docstring).
4. **Gates**: 803 + 4 tests pass, ruff clean, mypy clean, `verify_public_data.py`
   reports "public data manifest and source mirrors: OK".
5. **Attempted to dispatch a sweep** to close the roster gap rather than wait on
   drifting cron: `gh workflow run sweep.yml --ref main` returned `HTTP 403`,
   `Resource not accessible by integration`, on
   `/actions/workflows/277044658/dispatches`. The bot lacks `actions:write`, so
   dispatch is UI-only and the roster gap remains open at write time. This is the
   one operational claim in the handoff document that was substantively correct.

## Open items not fixed here

- **Cron drift is unmitigated.** `0 * * * *` delivers 3.5–5.5 h gaps. Either add
  a catch-up path (a secondary schedule offset from the hour, or a
  `workflow_dispatch`-friendly manual cadence in the runbook) or stop describing
  the sweep as hourly. The stale `*/15` comment in `scraper/deploy_alert.py:36`
  should be corrected either way.
- **`deploy_alert` only runs inside `sweep.yml`** (`sweep.yml:116`). If the cron
  stalls, the alarm cannot fire — the monitor shares a failure domain with the
  thing it monitors. The 275-min alarm in issue #496 fired because a sweep
  eventually ran. A lag alarm needs a schedule independent of the sweep.
- **Dual Pages mechanisms.** `build_type=legacy` (committed `docs/`) and
  `pages.yml` (Actions artifact + `deploy-pages`) both fire on every push to
  `main` and both deployed `5d903407b1` within ~30s of each other. `CLAUDE.md`
  documents this deliberately and forbids flipping `build_type` from an agent, so
  this record does not change it — but the `pages.yml` header comment still says
  it "replaces the implicit committed-docs deployment", which now contradicts
  `CLAUDE.md`. Reconcile the comment, or an admin should decide the cutover.
- **`freshness_hours` semantics under the anchor.** Anchoring to the vintage
  makes `freshness_hours` and `roster_age_hours` identically `0.0` at build time,
  so the published value can no longer express how old the roster is *now*; it
  only ages once a new build runs. That is the intended determinism trade, but
  the transparency page should not be read as a live staleness signal — the HTML
  meta stamp plus `deploy_alert` are the live signals.

## Next-session prompt (corrected)

```markdown
CONTEXT (verified 2026-09-24, main = 5d90340):
- Pages is NOT pending. Deployment of 5d90340 succeeded 02:44:59Z.
- The /tmp-build defect (issue #496) was already fixed by 5790d1a16d.
- The residual defect was stale docs/ artifacts published by the determinism
  merge itself; regenerated + guarded by tests/test_build_determinism.py on
  branch arena/01a0d152-hcjc, PR #504 (Lint + Deno green).
- The roster ages because the hourly cron drifts 3.5-5.5h, not because of
  webhooks. Issues #496 and #502 are CLOSED; open-issue count is 0.
- Bot scope: can read, push branches, open/edit PRs. CANNOT dispatch workflows
  or comment on issues (403 on both). Owner must dispatch sweep.yml via the UI.

DO:
1. Verify docs/ reproduces byte-identically:
     JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com \
       python -m web.build --out /tmp/outA
     JCSTREAM_SITE_BASE_URL='' JCSTREAM_CNAME=www.aretheyinjail.com \
       python -m web.build --out /tmp/outB
     diff -rq /tmp/outA /tmp/outB        # expect no output
2. Run the gates: pytest -q (807), ruff check ., mypy scraper web,
   python scripts/verify_public_data.py
3. Treat manual dispatch of sweep.yml as the reliable freshness lever; do not
   plan around an hourly cron. Note the bot cannot dispatch: `gh workflow run`
   returns HTTP 403 (no `actions:write`), so it is a UI action for the owner --
   but the bot CAN read, push branches and open PRs, so do not assume the token
   is dead.
4. Pick up the open items in audit/25_*.md, in priority order:
   deploy_alert's shared failure domain with sweep, then cron drift, then the
   pages.yml / CLAUDE.md contradiction.
5. Check the live site only from a network that can reach
   www.aretheyinjail.com; sandbox egress fails at TLS and proves nothing.

DO NOT:
- git push -f origin main (rewrites history; owner blocked force-push on main)
- hand-edit docs/ (regenerate it)
- diagnose "webhook stuck" without first reading the deployment status API and
  comparing docs/data/transparency_metrics.json:computed_utc to
  data/current.json:generated_utc
- flip Pages build_type from an agent (CLAUDE.md: admin-only, 2026-07-04
  incident)
```
