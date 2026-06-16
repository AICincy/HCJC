# HCJC Code Review Remediation: Execution Log

Date: 2026-06-16
Operator: jaredcincy@gmail.com
Agent: Claude Code (claude-opus-4-7)
Source plan: `audit/code-review-2026-06-16/00-summary.md` (originally
authored at `audit/code-review-2026-06-16/00-summary.md` on branch
`docs/code-review-2026-06-16`; relocated under `audit/` because the
next sweep wiped the `docs/` copy as a build artifact)

## 1. Overview

Six branches were produced. Branch 0 archived the canonical review synthesis
because the directory was empty when work began. Branches 1 through 5
implemented the five remediations in the order dictated by the plan, each
branched from `main`, each committed and pushed under the operator's
account, each opened as a draft pull request against `main`. The operator
merged each PR after review.

| Item | Value |
| :-- | :-- |
| Repository | `AICincy/HCJC` |
| Working tree | `/home/user/HCJC` |
| Default branch | `main` |
| Site URL | `https://www.aretheyinjail.com` |
| Live cadence | sweep cron `*/15 * * * *` with 20-minute skip gate |
| Required test baseline | >= 193 tests green per CLAUDE.md |

## 2. Branch and PR map

| Order | Branch | PR | Commit messages | Outcome |
| :-- | :-- | :-- | :-- | :-- |
| 0 | `docs/code-review-2026-06-16` | #337 | `docs: archive 2026-06-16 five-lane code review synthesis` | merged |
| 1 | `docs/session-id-chain-of-custody` | #336 | `docs: document chain-of-custody for court-evidence session IDs`; `docs: split chain-of-custody prose into single-idea sentences` | merged |
| 2 | `legal/remove-dispatch-correlations-public` | #338 | `legal: remove dispatch_correlations.json from publicly served path`; `test: use scraper.correlate.OUT_PATH instead of hardcoded path` | merged |
| 3 | `evidence/durable-waf-and-photo-logging` | #339 | `evidence: durable logging for detail-page WAF blocks and empty photos`; `evidence: fall back to client.get() when get_response is absent` | merged |
| 4 | `a11y/cross-lane-contrast-and-alt-text` | #340 | `a11y: fix WCAG AA contrast failures and add booking photo alt text`; `a11y: revert booking-photo alt to empty per WCAG H2/F89 (redundant link text)` | merged |
| 5 | `security/workflow-permission-tightening` | #341 | `security: tighten GitHub Actions workflow permissions` | merged |

## 3. Non-negotiable constraints honored

| Constraint | Verification |
| :-- | :-- |
| No WAF circumvention | PR 3 only records denials. `JCSTREAM_HTTP_PROXY` remained deliberately unset. `client.get_response` was substituted for `client.get` solely to capture the response status code for evidence logging. |
| No "fix" of the 107 empty base64 booking photos | PR 3 added an INFO log line and a hash-chained `empty_photo_observed` event at the parser's skip site. The skip itself was untouched. |
| No fabricated citations or paths | Every `[VERIFY]` placeholder in PR 1 was preserved. PR 2 verified that `scraper/correlate.py::OUT_PATH` existed before the test refactor. PR 5 walked every step in each workflow against its corresponding permission claim. |
| One-source principle | PR 2 relocated the cross-source inference output (`dispatch_correlations.json`) out of `data/` (the git-tracked, GitHub-published path) into `private/` (a gitignored, build-excluded path). The data-page template references to that file were removed. |
| CLAUDE.md style accommodations | No em or en dashes were added to authored prose. Tables were used for three or more comparable items throughout. Sentences carry one idea each. Active voice was preserved in all PR descriptions and replies. |

## 4. Branch 0: code review synthesis archive

### 4.1 Discrepancy

The remediation plan instructed reading
`audit/code-review-2026-06-16/00-summary.md` and five lane reports before any
code change. Neither the directory nor the files existed in the working tree
or in any git ref. The operator supplied the canonical synthesis text inline
and authorized creating the file on a new branch.

### 4.2 Action

| Step | Detail |
| :-- | :-- |
| Branch | `docs/code-review-2026-06-16` from `origin/main` |
| Write | `audit/code-review-2026-06-16/00-summary.md`, 84 lines |
| Commit | `10b5e0d224` |
| Push | `git push -u origin docs/code-review-2026-06-16` |
| PR | not opened initially per instruction; operator opened #337 and merged it |

## 5. Branch 1: Chain of custody for court-evidence session IDs

### 5.1 Source finding

Critical (legal-evidentiary lane): the four court-evidence Claude Code
session IDs did not appear anywhere in the repository.

### 5.2 Action

Added a `## Chain of Custody: Session IDs` section to `CLAUDE.md`
containing:

| Field | Value |
| :-- | :-- |
| Session ID 1 | `session_01Hbc6p9EspF6RH9ajNNb8tB` (date range `[VERIFY]`) |
| Session ID 2 | `session_01MNnYgZMY5uFz9cHie3w6TY` (date range `[VERIFY]`) |
| Session ID 3 | `session_019fDevbfpgmnjJP7A343T95` (date range `[VERIFY]`) |
| Session ID 4 | `session_01NGMSLESEepbgV8aSn4reVG` (date range `[VERIFY]`) |
| Authoritative storage location | `[VERIFY]` |
| Retrieval procedure | numbered five-step process pointing at `https://claude.ai/code/<session_id>` |
| Cross-reference | named the Critical finding in `audit/code-review-2026-06-16/00-summary.md` |

### 5.3 Review iteration

Gemini-code-assist flagged the section's prose as failing the CLAUDE.md
"one idea per sentence" rule, specifically the multi-clause "are cited or
may be cited in litigation" passive and a multi-instruction commaed
sentence in the retrieval procedure. The prose was split into:

| Before | After |
| :-- | :-- |
| Single sentence with passive "are cited or may be cited" plus joined "abbreviate, redact, or reformat" | Two sentences. One imperative per instruction. |
| Single paragraph mixing retrieval procedure into commas | Ordered list, one verb per item |

Commits: `5260e69de2`, `cdab23df40`. Final SHA on branch after rebase and
push: `b2bbfb50c3`.

### 5.4 Tests

The change is documentation-only. Pytest in the session environment was
blocked by missing project dependencies (`pydantic`, `defusedxml`,
`selectolax`). No Python paths were touched. CI on the branch ran the
test matrix and passed.

## 6. Branch 2: relocate `dispatch_correlations.json` off the public path

### 6.1 Source finding

Elevated from Medium to High (scraper-integrity lane via lead synthesis):
`scraper/correlate.py` produces an inferential cross-source join that
HCSO does not publish. The one-source principle forbids publishing
anything HCSO does not publish.

### 6.2 Discrepancy noted

The summary asserted the file was "publicly served." A verification pass
showed `web/pages.py::_render_data_page` uses an explicit allowlist and
that `dispatch_correlations.json` was not in it. The build never copied
the file into `docs/data/`. The file was, however, tracked in `data/` and
therefore publicly readable via the GitHub raw URL. The remediation
removed both: the file was untracked, the directory was gitignored, the
data-page template references were deleted.

### 6.3 Action

| Step | Detail |
| :-- | :-- |
| `git mv data/dispatch_correlations.json private/dispatch_correlations.json` | move into the new top-level path |
| `git rm --cached private/dispatch_correlations.json` | untrack the moved file |
| `.gitignore` | added `private/` with a comment naming the one-source principle |
| `scraper/correlate.py` | added a 22-line `# =====` comment block at the top of the module explaining why the output must not return to `data/`, `docs/`, or any other served tree; changed `OUT_PATH` to `Path("private") / "dispatch_correlations.json"`; added `OUT_PATH.parent.mkdir(parents=True, exist_ok=True)` before write |
| `tests/test_correlate.py` | updated the round-trip assertion to read from the new path |
| `web/templates/data.html` | removed the `<tr>` row that linked the file; removed the dedicated "Dispatch correlation (researcher mode)" section |

Commits: `e3b7c5e909`, plus follow-up `7672e2d062` substituting the
hardcoded test path for the imported `OUT_PATH` constant. Final SHA on
branch after rebase: `43f2f4be66`.

### 6.4 Review iteration

Gemini suggested the test should reuse the module's `OUT_PATH` constant
rather than hardcode `Path("private") / "dispatch_correlations.json"`,
making the test resilient to future path changes. The suggestion was
applied directly.

### 6.5 Tests

`/root/.local/bin/pytest tests/test_correlate.py -q` ran locally and
returned `21 passed in 0.04s` against both the initial relocate commit
and the OUT_PATH refactor. Full suite ran in CI and passed.

## 7. Branch 3: durable logging for detail-page WAF blocks and empty photos

### 7.1 Source findings

Two Medium findings (legal-evidentiary lane):

| Finding | Existing state |
| :-- | :-- |
| Per-inmate detail-page WAF blocks | logged at WARNING level only; ephemeral in Actions log retention |
| Empty-payload base64 photo skips | parser increments a counter; no INFO log, no durable record |

### 7.2 Hash-chained log mechanism

`data/waf_block_log.json` is the durable evidence log. Records chain via
`prev_sha256`. Append happens through
`scraper/store.py::append_block_evidence`, which uses both a threading
lock and an advisory file lock and writes atomically via temp-file
rename. Verification of the chain runs through
`scraper.verify_block_log`. The existing list-page block event format
(`event="blocked"`) was not modified.

### 7.3 New event types

| Event | Emitter | Fields |
| :-- | :-- | :-- |
| `detail_page_waf_block` | `scraper/sweep.py::_record_detail_page_block`, called from `_fetch_detail_with_retry` after a second WAF-block-shaped response | `timestamp_utc`, `event`, `inmate_id`, `url` (`<DETAIL_PATH>?id=<inmate_id>`), `http_status`, `response_signature` (first 16 hex of SHA-256 of the body), `response_length` |
| `empty_photo_observed` | `scraper/parsers.py::_record_empty_photo_event`, called from `_extract_photo` at the `if "base64" not in header or not payload: continue` skip | `timestamp_utc`, `event`, `inmate_id`, `photo_field_path` (`f"img[{i}]@src {data_uri_header}"`), `payload_length` |

### 7.4 Implementation notes

| Concern | Resolution |
| :-- | :-- |
| Parser test pollution of `data/waf_block_log.json` | `parse_detail_page` and `_extract_photo` gained a keyword-only `record_evidence: bool = False`. The sweep passes `True`. Parser tests run with `False` and emit no events. |
| HTTP status capture | `client.get_response` returns the `httpx.Response`. `_fetch_detail_with_retry` switched from `.get` to `.get_response` to read `response.status_code`. |
| Test fakes do not implement `get_response` | added a `get_response = getattr(client, "get_response", None)` shim that falls back to `.get(...)` with `http_status = None` on the synthetic events. |
| Parser-to-store import cycle | the empty-photo emitter imports `append_block_evidence` lazily inside the function. |

### 7.5 CI failure and fix

The initial push caused five regressions in `tests/test_sweep.py`,
specifically `test_fetch_one_*` cases that pass a `_FakeClient` and a
`_FlipClient` that implement `.get` only. The new code called
`.get_response` directly and the fakes raised `AttributeError`, which
the existing exception handler turned into `return None, None, None`.

| Failing test | Root cause |
| :-- | :-- |
| `test_fetch_one_uses_list_row_name_when_detail_heading_missing` | `_FakeClient` lacks `.get_response` |
| `test_fetch_one_carries_existing_photo_when_no_inline_image` | same |
| `test_fetch_one_falls_back_to_disk_when_pillow_rejects_bytes` | same |
| `test_fetch_one_returns_none_on_waf_blocked_response_for_known_inmate` | same |
| `test_fetch_one_retries_within_same_cycle_and_recovers_on_second_attempt` | `_FlipClient` lacks `.get_response`; the retry loop never ran |

The fix introduced the `getattr` shim. Local syntax check
`python -c "import ast; ast.parse(...)"` passed for both modified
modules. Final SHA on branch after rebase: `155c5ece80`.

### 7.6 Review iteration

Gemini opened three threads.

| Severity | Path | Status | Resolution |
| :-- | :-- | :-- | :-- |
| Medium | `scraper/parsers.py` L539 (redundant `img_index` variable) | outdated after refactor commit | already addressed in `155c5ec`: variable removed, `img_count - 1` used in field_path |
| Medium | `scraper/parsers.py` L575 (use `img_count - 1` directly) | resolved | same commit applied the change; thread marked resolved via API |
| High | `scraper/sweep.py` L885 (exception in attempt 0 returns immediately) | declined | the early return is pre-existing behavior; the retry loop is for WAF-block-shaped responses, not transport errors; `client.get_response` already retries 5xx and 429 internally; reshaping the exception flow is out of PR 3 scope. Reply posted explaining this; thread left unresolved per the operator's "skip; reply to gemini" decision. |

### 7.7 Tests

Local: `python -c "import ast; ast.parse(...)"` OK on both modified
files. Local pytest blocked by missing `selectolax`/`pydantic` in the
session environment. CI on the fix commit ran the full suite and the
operator merged after CI green.

## 8. Branch 4: cross-lane contrast and alt text

### 8.1 Source findings

| Lane | Finding |
| :-- | :-- |
| templates-build (High) | `--fg-muted` `#6c6c6c` on `--bg` `#F5F0EB` measured approximately 4.0:1; WCAG AA small-text threshold is 4.5:1. |
| templates-build (High) | `.court-stat-primary` label `rgba(255,255,255,0.78)` against the cobalt-blue end of its gradient measured approximately 2.7-2.9:1; WCAG AA large-text threshold is 3:1. |
| templates-build (WCAG 1.1.1) | `alt=""` on the booking-photo `<img>` inside the card-link anchors in `statute.html` and `court.html`. |
| federal-docket-css (High) | `.court-stat-primary` and `.visit-card-primary` used `linear-gradient(... var(--accent), #2c41a8 100%)`; `#2c41a8` is an off-spec cobalt blue not in the Federal Docket palette. |

### 8.2 Action (initial)

| Token / selector | Before | After |
| :-- | :-- | :-- |
| `--bg` | `#F5F0EB` | `#fafafa` |
| `--fg-muted` | `#6c6c6c` | `#5c5c5c` |
| `.court-stat-primary` background | `linear-gradient(140deg, var(--accent) 0%, #2c41a8 100%)` | `var(--accent)` |
| `.visit-card-primary` background | `linear-gradient(155deg, var(--accent) 0%, #2c41a8 100%)` | `var(--accent)` |
| `statute.html` booking-photo `alt` | `alt=""` | `alt="HCSO booking photo of {{ inm.full_name }}"` |
| `court.html` booking-photo `alt` | `alt=""` | `alt="HCSO booking photo of {{ e.inmate.full_name }}"` |

`--fg` and `--accent` were deliberately left unchanged per the
remediation plan. Commit: `ca7d5e6d28`.

### 8.3 Review iteration

Gemini flagged the new `alt` text as a WCAG H2 / F89 violation: an
`<img>` inside an anchor whose visible body text already names the
inmate causes a screen reader to read the name twice. The remediation
plan's literal instruction conflicted with the WCAG rule. The conflict
was surfaced to the operator with three options:

| Option | Outcome on screen reader |
| :-- | :-- |
| Revert to `alt=""` (chosen) | name read once via card-link text; image marked decorative |
| `alt="Booking photo"` | name read once; image flagged with generic description |
| Keep name in `alt` | name read twice |

The operator selected `alt=""`. Both templates were reverted to
`alt=""`. Commit: `c023434629`. Replies posted on both gemini threads;
both threads marked resolved via the GraphQL `resolve_review_thread`
mutation.

### 8.4 Tests

CSS tokens and `alt` attributes only. No Python paths exercised. CI on
the final commit ran the full suite and the operator merged.

## 9. Branch 5: workflow permission tightening

### 9.1 Source findings

Two High findings (repo-hygiene lane):

| Workflow | Excess permissions | Reason |
| :-- | :-- | :-- |
| `.github/workflows/sweep.yml` | `pages: write`, `id-token: write` | the `actions/upload-pages-artifact` and `actions/deploy-pages` steps that required them are fully commented out; Pages now serves from `docs/` on the working branch via Settings > Pages > Source = branch |
| `.github/workflows/pra_daily.yml` | `contents: write` on every run | the commit step is dead code on deployments without SMTP configured |

### 9.2 Action: `sweep.yml`

| Field | Before | After |
| :-- | :-- | :-- |
| `permissions.contents` | write | write (retained for the "Commit data + built site" step) |
| `permissions.pages` | write | removed |
| `permissions.id-token` | write | removed |
| `permissions.issues` | write | write (retained for `scraper.freeze_alert`) |

A comment block at the top of the file documents the active permissions
and explicitly notes that `pages: write` and `id-token: write` must be
restored together if the deploy-pages path is ever re-enabled.

### 9.3 Action: `pra_daily.yml`

`contents: write` remained at the workflow level because GitHub Actions
does not allow conditional permission grants. The commit step itself
was gated:

```yaml
- name: Commit PRA requests log
  if: ${{ secrets.JCSTREAM_PRA_SMTP_HOST != '' }}
  run: |
    ...
```

The send-side steps already run in dry-run mode without SMTP, so the
log file does not change on unconfigured deployments. The gated commit
step short-circuits and the token stays unexercised. A comment block at
the top of the file documents the active permissions and the gating
condition.

### 9.4 Step-by-step verification

`sweep.yml` active steps and the permission each needs:

| Step | Permission consumed |
| :-- | :-- |
| `actions/checkout` | none beyond default |
| `actions/setup-python` | none |
| `pip install -r requirements.txt` | none |
| HCSO inmate sweep | none beyond default |
| Roster freeze alarm (`scraper.freeze_alert`) | `issues: write` |
| Four Cincinnati Open Data pulls | none |
| Build dispatch correlation candidates | none |
| Build static site | none |
| Commit data + built site (`git push`) | `contents: write` |

The deploy-pages and health-check steps remain commented out and were
not re-enabled.

`pra_daily.yml` active steps:

| Step | Permission consumed |
| :-- | :-- |
| `actions/checkout` | none beyond default |
| `actions/setup-python` | none |
| `pip install -r requirements.txt` | none |
| PRA capias send | none (SMTP outbound only) |
| PRA photos send (gated on `vars.JCSTREAM_PRA_PHOTOS_ENABLED == '1'`) | none |
| Commit PRA requests log (gated on `secrets.JCSTREAM_PRA_SMTP_HOST != ''`) | `contents: write` |

### 9.5 Tests

| Check | Result |
| :-- | :-- |
| `python -c "import yaml; yaml.safe_load(open(...))"` on both files | OK |
| Python code paths touched | none |
| Pytest delta | none |

Commit: `a51cfe277b`. CI started on push.

## 10. Pull request review interactions

Gemini-code-assist posted automated reviews on five of the six PRs.
Each comment was investigated and either applied, declined with a
reply, or implicitly resolved by the existing changeset.

| PR | Gemini findings | Disposition |
| :-- | :-- | :-- |
| #336 | one Medium (sentence complexity) | applied via follow-up commit `cdab23df40` |
| #337 | none | n/a |
| #338 | one Medium (use `OUT_PATH` constant) | applied via follow-up commit `7672e2d062` |
| #339 | one High (exception flow), two Medium (`img_index` redundancy) | High declined with a posted reply; Medium findings were already addressed by the fix commit `155c5ece80`; threads resolved via API |
| #340 | two Medium (alt-text redundant with link text) | applied via follow-up commit `c023434629`; threads resolved via API |
| #341 | none (gemini does not review YAML) | n/a |

## 11. Open items

| Item | Owner | Source |
| :-- | :-- | :-- |
| Replace the four `[VERIFY]` placeholders in `CLAUDE.md` chain-of-custody section with confirmed storage location and date ranges | operator | PR #336 |
| Run `jcstream-a11y-auditor` after PR #340 merge to confirm contrast deltas at rendered scale | operator | PR #340 |

## 12. Session environment notes

| Item | Detail |
| :-- | :-- |
| Container | ephemeral; cloned `AICincy/HCJC` at session start |
| Python | 3.11 on the host; project requires 3.13+ |
| Missing dependencies | `selectolax`, `pydantic`, `defusedxml`, `Pillow`, `jinja2`, `httpx` were not installed |
| Pytest reach | `tests/test_correlate.py` ran (pure stdlib); other modules failed at collection due to the missing dependencies |
| Test authority | CI on each PR was the canonical test signal; the operator merged only after CI green |

## 13. Commit reference

| Branch | Final SHA pushed | Notes |
| :-- | :-- | :-- |
| `docs/code-review-2026-06-16` | `10b5e0d224` | initial commit only |
| `docs/session-id-chain-of-custody` | `b2bbfb50c3` | two commits, rebased on `main` |
| `legal/remove-dispatch-correlations-public` | `43f2f4be66` | two commits, rebased on `main` |
| `evidence/durable-waf-and-photo-logging` | `155c5ece80` | two commits, rebased on `main` |
| `a11y/cross-lane-contrast-and-alt-text` | `c023434629` | two commits |
| `security/workflow-permission-tightening` | `a51cfe277b` | one commit |
