# A2 CI reproducibility report

**Work card:** A2-CI-REPRO-001  
**Audit question:** Can the frozen HCJC source dependencies, CI pins, and declared checks be reproduced in an isolated environment, with every discrepancy classified?  
**Technical verdict:** **Partial**  
**Completion condition:** Met for the locally available Python 3.14 environment. Python 3.13 and the declared Ubuntu runner remain unexecuted and are explicitly retained as an environment gap.

## Custody, scope, and boundaries

| Field | Evidence |
|---|---|
| Frozen repository identity | Detached worktree `C:\Users\jared\.codex\HCJC-audit-worktrees\2026-09-19-public-a2` at `fbe33ca9af7db6e08ab4a6f16515ece26085b241`. `git rev-parse HEAD` returned that SHA before and after execution. |
| Baseline source | A0 baseline manifest, frozen at `2026-09-19T19:28:48Z`. |
| A2 observation close | `2026-09-19T19:57:57.7209377Z`. |
| Environment exercised | Windows 11 `10.0.22631`, CPython `3.14.6`, AMD64, isolated virtual environment created for this audit and removed after execution. |
| CI environment declared by source | `.github/workflows/ci.yml:17,21` declares `ubuntu-latest` with Python `3.13` and `3.14`. |
| Access and action boundary | Local isolated execution only. No source, workflow, lockfile, dependency declaration, production deployment, account, secret, variable, mail, or public record was modified. |
| Privacy boundary | This report contains only aggregate verifier counts and no person-level roster or ledger data. |

The A2 worktree was clean before execution. A disposable sandbox briefly appeared as an untracked directory while checks ran. It and the virtual environment were removed. The A2 worktree was clean again after cleanup, and `git diff --check` returned exit `0`.

A final read-only query of the active checkout showed one tracked diff at `audit-output/HCJC-live-status-report-audit-2026-09-19.md`. A2 did not edit that checkout or attribute that audit-output diff. No source path was returned by that query.

## Requirement-to-evidence matrix

| Requirement or risk | Observable behavior | Fresh evidence | Result | Evidence grade and gap |
|---|---|---|---|---|
| Frozen target identity | A2 executes the exact SHA issued by A0 and leaves it unchanged. | `git rev-parse HEAD` returned `fbe33ca9af7db6e08ab4a6f16515ece26085b241` before and after; starting and final porcelain status were empty. | Pass | E. Git identity and cleanliness are static custody evidence, not production evidence. |
| Python support matrix | Every declared interpreter is either executed or specifically unavailable. | `.github/workflows/ci.yml:21` declares 3.13 and 3.14. `py -0p` listed only 3.14. `py -3.13 -c "import sys; print(sys.version)"` exited `1` with no matching runtime installed. CPython 3.14.6 ran. | Partial | C for 3.14 execution; X for 3.13 and Ubuntu. No conclusion about their result is permitted. |
| Declared runtime dependencies | The requirements file installs under the available declared interpreter. | `python -m pip install -r requirements.txt` exited `0` in the isolated 3.14 environment. | Pass | C. This does not prove a clean resolve on Python 3.13 or Ubuntu. |
| CI lint check | The pinned CI Ruff command succeeds against the frozen source. | `.github/workflows/ci.yml:29,31-32`; `python -m ruff check .` with Ruff 0.15.22 exited `0`: `All checks passed!` | Pass | C. Windows isolated check only. |
| CI type check | The pinned CI mypy command succeeds against the frozen source. | `.github/workflows/ci.yml:29,33`; `python -m mypy scraper web` with mypy 2.3.0 exited `0`: no issues in 45 source files. | Pass | C. Windows isolated check only. |
| Dependency advisory check | Current advisory-db scan of the declared requirements completes. | `.github/workflows/ci.yml:34-41`; a JSON-format reproduction of `pip-audit -r requirements.txt` exited `0` and reported no known vulnerabilities. | Pass | C. Tool and advisory database were current at observation time, not frozen CI inputs. |
| CI behavioral suite | The declared test command runs to completion. | `.github/workflows/ci.yml:42`; `python -m pytest -v` exited `0`: 469 passed in 25.32 seconds. | Pass | C. The suite is evidence about this isolated environment, not a live-site result. |
| WAF evidence chain | The declared verifier accepts the committed local chain. | `.github/workflows/ci.yml:44-47`; `python -m scraper.verify_block_log` exited `0`: hash chain intact across 137,023 records. | Pass | C. Integrity of this local artifact only. It does not establish WAF effectiveness or current live behavior. |
| PRA evidence chain | The declared verifier accepts the committed local chain. | `.github/workflows/ci.yml:49-51`; `python -m scraper.verify_pra_log` exited `0`: hash chain intact across 352 records. | Pass | C. Historic local ledger integrity only. It does not establish current SMTP configuration or delivery. |
| Empty-base build smoke test | The site builder succeeds with the declared empty site-base URL. | `.github/workflows/ci.yml:53-57`; `JCSTREAM_SITE_BASE_URL='' python -m web.build` equivalent exited `0` in a disposable copy. | Pass | C. The local frozen snapshot built 1,116 entries. This is not a current public-roster count or deployment assertion. |
| Custom-domain build check | The builder writes `docs/CNAME` with the declared hostname. | `.github/workflows/ci.yml:59-70`; build with `JCSTREAM_CNAME=www.aretheyinjail.com` exited `0`; a Windows semantic equivalent of the workflow's shell assertions exited `0` and read `www.aretheyinjail.com`. | Pass | C. The workflow's Bash `test` and `grep` syntax itself was not run because the observed host is Windows. |

## Manifest and CI dependency matrix

All rows below are at frozen SHA `fbe33ca`. The runtime package pins agree across `pyproject.toml:15-20` and `requirements.txt:1-6`.

| Component | `pyproject.toml` | `requirements.txt` | CI workflow | Version exercised locally | Claim status |
|---|---|---|---|---|---|
| Python | `>=3.13` at line 9 | Not declared | 3.13 and 3.14 at line 21 | 3.14.6 only | verified |
| httpx | 0.28.1 | 0.28.1 | Installed from requirements | 0.28.1 | verified |
| selectolax | 0.4.11 | 0.4.11 | Installed from requirements | 0.4.11 | verified |
| pydantic | 2.13.5 | 2.13.5 | Installed from requirements | 2.13.5 | verified |
| jinja2 | 3.1.6 | 3.1.6 | Installed from requirements | 3.1.6 | verified |
| defusedxml | 0.7.1 | 0.7.1 | Installed from requirements | 0.7.1 | verified |
| Pillow | 12.3.0 | 12.3.0 | Installed from requirements | 12.3.0 | verified |
| pytest | dev 9.1.1 | 9.1.1 | Installed from requirements | 9.1.1 | verified |
| Ruff | dev 0.16.7 | Not listed | 0.15.22 at CI line 29 | 0.15.22 | conflicting |
| mypy | dev 2.3.1 | Not listed | 2.3.0 at CI line 29 | 2.3.0 | conflicting |
| pip-audit | Not pinned | Not listed | Installed without a version at CI line 40 | 2.10.1 | verified |

`python -m pip check` in the isolated environment exited `0` with no broken requirements. That confirms the observed installation had no resolver conflict. It does not make its unpinned transitive packages, pip-audit version, or advisory database reproducible across time.

## Material findings

| ID | Finding | Severity and confidence | Claim-source status | Technical verdict | Evidence and consequence | Smallest safe next step |
|---|---|---|---|---|---|---|
| A2-F1 | The frozen source's declared development tool versions differ from the versions CI actually installs. Ruff is 0.16.7 versus 0.15.22. mypy is 2.3.1 versus 2.3.0. Neither tool is in `requirements.txt`. | Medium, High | conflicting | Partial | The different local developer and CI tools both pass at this SHA, so no current source failure was reproduced. The divergence reduces confidence that local development and CI apply the same static checks. | Run the same frozen source under the `pyproject.toml` dev-tool pins in a distinct disposable environment, then compare only tool results and diagnostics. |
| A2-F2 | The CI dependency scan is time-dependent because CI installs `pip-audit` without a version and queries a mutable advisory database. | Low, High | verified | Partial | The current observation with pip-audit 2.10.1 returned no findings. That cannot reproduce an earlier or future CI security verdict exactly. | Record the scanner version and advisory-db observation time in CI artifacts before treating a scan result as historically reproducible. |
| A2-F3 | Full declared CI matrix reproduction remains incomplete. | Medium, High | manual review needed | Partial | The local host has Python 3.14.6 only. The 3.13 launcher command exited 1 because no matching runtime exists. The declared `ubuntu-latest` shell path was not available. This is an environment limitation, not a source or test failure. | Execute the unchanged workflow in an isolated Ubuntu Python 3.13 environment, or inspect a public run bound to the frozen SHA as a separate evidence route. |

No source, test, or implementation defect was directly reproduced in the executed Python 3.14 check sequence.

## Command and failure record

| Command or event | Exit result | Classification | Preserved result |
|---|---:|---|---|
| `git rev-parse HEAD` and `git status --porcelain=v1` before work | 0 | Baseline custody | Exact frozen SHA; clean starting worktree. |
| `py -0p` and `py -3.14 --version` | 0 | Environment identity | Only CPython 3.14.6 was available. |
| `py -3.13 -c "import sys; print(sys.version)"` | 1 | Environment limitation | No 3.13 runtime installed. It was not installed during this audit. |
| First anti-churn reservation | 1 | Environment/control-plane configuration failure | The event's policy digest did not match the active policy. The event was repaired to the active policy and the next reservation was allowed. This did not run or alter HCJC. |
| `python -m pip install -r requirements.txt` | 0 | Executed setup | Exact runtime requirements installed in the isolated 3.14 environment. |
| `python -m pip install ruff==0.15.22 mypy==2.3.0` | 0 | Executed setup | Exact CI static-tool pins installed. |
| `python -m pip install pip-audit` | 0 | Executed setup | CI leaves this version unpinned; observed version was 2.10.1. |
| `python -m ruff check .` | 0 | Executed check | All checks passed. |
| `python -m mypy scraper web` | 0 | Executed check | No issues in 45 source files. |
| Initial exact `pip-audit -r requirements.txt` invocation | No observable completion payload | Environment/tool-output limitation | The host relay returned no status or output after waiting. It was not counted as a pass. One JSON-output evidence route then completed with exit 0 and no known vulnerabilities. |
| `python -m pytest -v` | 0 | Executed check | 469 passed in 25.32 seconds. |
| `python -m scraper.verify_block_log` | 0 | Executed check | 137,023-record hash chain intact. |
| `python -m scraper.verify_pra_log` | 0 | Executed check | 352-record hash chain intact. |
| Two `python -m web.build` runs and CNAME assertion | 0 | Executed check | Empty-base and custom-domain build paths passed in the disposable copy. |
| First sandbox-copy cleanup with native PowerShell `Remove-Item` | Rejected before execution | Environment/tool policy limitation | The host blocked the exact file deletion. The known temporary `.git` pointer was then removed with the permitted patch workflow before tests ran. |
| Final `git status --porcelain=v1` and `git diff --check` | 0 | Cleanup verification | Empty status and no diff-whitespace output in the A2 worktree. |

The transient setup and host-output limitations above do not alter any CI verdict. They are included so no local failure is erased or converted into a product conclusion.

## Deliberately excluded work

- No Python 3.13 interpreter, Linux runner, Docker image, remote Actions run, or additional package lockfile was installed or changed.
- No code, test, fixture, manifest, workflow, generated site, ledger, or configuration was edited.
- No live scrape, deployment check, private Actions, Pages, Giscus, SMTP, secret, variable, mail, person-linked comparison, or public correction was attempted.
- A passing local lint, type, test, verifier, or build result is not a claim about current production health, live roster accuracy, owner state, or successful mail delivery.

## A2 conclusion for A0 intake

The frozen source reproduces its declared CI command sequence successfully in one isolated Windows Python 3.14.6 environment. The result is **Partial**, not Pass, because the workflow also declares Ubuntu Python 3.13 and that environment was not available. The dependency/tool matrix contains two directly verified reproducibility gaps: developer-tool pins differ from CI pins, and pip-audit is unpinned. These are configuration-drift findings, not evidence that the frozen source presently fails CI or that the public deployment is unhealthy.

**Recommended A0 disposition:** accept this report as Grade C isolated-execution evidence and Grade E configuration evidence; retain A2-F1 through A2-F3 for independent adversarial review if they materially influence remediation prioritization.
