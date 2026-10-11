# Handoff — HCJC / JCStream UI & Hamburger Orchestration

**Date:** 2026-10-10T19:53-04:00
**Coordinator session:** `1a27fd0f-72ff-4900-bcdf-08ca51da58b0` — branch `aicincy-scaling-waddle`
**Tip SHA:** `db861f7017f5 Disable Vercel deployments` (main)
**Worktree:** `C:\Users\jared\.copilot\repos\copilot-worktrees\HCJC\aicincy-scaling-waddle`
**Project:** `a0334ef5-abfa-4f68-bffa-3d5f839ca549` · `AICincy/HCJC` · `main` is default
**Live site:** https://www.aretheyinjail.com (Pages branch-serve `main/docs`, sweep cron `7,37 * * * *` +20m skip gate, `JCSTREAM_SITE_BASE_URL=""` for local build)

---

## 1. Objective (user-owned, preserved verbatim)

- `What pending action items are remaining for: https://github.com/AICincy/HCJC.git` → answered: 0 open issues/PRs, CI/pages/sweep green, worktree clean.
- `ui & ux improvements?` → discovery audit.
- `hamburger menus are so bad` → **explicit constraint:** replace hidden hamburger with visible/persistent nav. User then invoked `/orchestrate` with `lets multitask.`
- `Create a handoff.md ... Spawn more than 3 orchasters this time. Do not let them silently fail. @[.claude/skills/aai-cognitive-interface]`

**Success:** hamburger replaced by visible desktop nav + critical UX blockers fixed + polish shipped, all with boundary evidence (no silent failures).

---

## 2. Authorized scope

- Read/verify repo health via `gh` + `git` (done).
- Edit `web/templates/*`, `web/static/*`, `web/build.py` helpers, `tests/*` pins — surgical only.
- Build: `JCSTREAM_SITE_BASE_URL="" python -m web.build` + `scripts/verify_public_data.py`.
- Verify: `python -m ruff check .`, `python -m mypy scraper web`, `python -m pytest -q`, live `curl -s https://www.aretheyinjail.com/ | grep jcstream:generated-utc`.
- Commit/PR via `gh` in child sessions (one branch = one PR). Do NOT push to `main`, do NOT dispatch `sweep.yml` without explicit user auth, do NOT hand-edit `docs/` or `data/waf_block_log.json`.

---

## 3. Hard constraints (AAI + repo guide)

- **AAI governing:** semantic intent ≠ execution authority; action induction ≠ authorization; fail closed at consequential boundaries; every positive claim needs boundary evidence; `DRAFTED` → `STATIC-PASS` → `SAVED` → `INSTALLED` → `RUNTIME-VERIFIED` ladder — never promote without evidence.
- **Scope gate:** one task, one fix; no multi-phase plans inside a single track; no CSS/template churn without authorization (authorized here via hamburger+UX request).
- **Deterministic build contract:** `docs/data/transparency_metrics.json:computed_utc == data/current.json:generated_utc`; `freshness_hours == generated_utc - last_healthy_sweep_utc`; consecutive builds byte-identical.
- **Privacy/security:** `data/waf_block_log.json` append-only SHA-256 chained; never hand-edit; no Supabase in Python pipeline; no secrets in repo.
- **Style:** Python 3.13+, Ruff 120-char, `pyproject.toml` authority; preserve `docs/CNAME`.

---

## 4. Current architecture (do not re-audit — use this)

- **Hamburger impl:** `web/templates/base.html:48-53` `<details class="nav-menu"><summary class="nav-toggle">SVG 3 lines</summary> {% include "_nav_groups.html" %}</details>`. Desktop: `@supports selector(details::details-content)` hides toggle, `::details-content display:block` keeps rail visible from closed markup; fallback keeps toggle. Mobile ≤720px: toggle visible at `grid-column 3`, `.nav-drawer display:none absolute right 264px max-height 70vh; [open] display:block`. `.masthead-inner grid 1fr auto 1fr`, brand centered, `.running.desktop-only`.
- **Nav links:** `web/templates/_nav_groups.html` — 18 links in 3 groups (Roster tools 7, Court reference 8, Site 3). `_more_reference.html` duplicates 8 court-ref cards. `base.html` footer duplicates 9 links. `base.html:55-66` `month-nav` chip rail.
- **Roster tools:** `web/templates/_roster_tool.html` — `details.more-filters` hides tier/offense/activity/sort/table view; `tier-strip-slim` 4px `role="img"`; `#filter-sort` inside disclosure; `#view-toggle hidden` until JS; search `placeholder "Name, charge, or ORC code"`.
- **Statute:** `web/templates/statute.html:5-9` `#statute-jump-bar hidden` until JS reveals.
- **Inmate detail:** `web/templates/base.html:107-115` `#lb role=dialog aria-modal hidden` — no focus trap, no `inert` on `#main`+`.masthead`.
- **Tokens:** `web/static/style.css` — Public Sans/IBM Plex Mono, `--accent #B33A2A`, `--masthead-h 56px`.

---

## 5. Audit mapping (source of truth: `audit/26_*` + `audit/27_*`)

`audit/26_ui_ux_failures_2026-10-09.md` (16 claims, failures R/N/D/S/C + a11y-F1-F8, live `inmate_count 1145`, tip `be62652f`):
- **R1 high:** filters behind collapsed `Filters` — blocks 1,145 roster narrowing
- **D1 high (a11y-F1):** lightbox no focus trap/inert
- **S1 high:** statute jump hidden behind JS — fails no-JS
- **N1 med:** drawer sole global nav, 18 links hidden — requires hamburger open for `/statute/`, `/bond-schedule/`, `/court/`
- **R2/R4/R5/R6/R7, N2/N3, D2/D3, S2/S3, C1-C3, a11y-F2-F8** as documented

`audit/27_ui_ux_remediation_plan_2026-10-09.md` — 20-step phased plan; **Step 5 = N1** `tests/test_nav.py::test_desktop_top_bar_links` expected `grep top-bar`.

---

## 6. Prior orchestration — what happened and why it failed

**2026-10-10T16:44-16:46 UTC — 3 tracks spawned (all `autopilot`, `coordinate_with_creator:true`, `notify_on_idle:once`):**
- `02eb596b` (Track A · `aicincy-legendary-doodle`) — hamburger → top bar
- `c79c50ed` (Track B · `aicincy-verbose-barnacle`) — R1/S1/D1
- `208d6738` (Track C · `aicincy-fictional-dollop`) — polish/IA

**Result @ 17:53 UTC:** all three emitted `system_notification: encountered an error` then `idle` with **0 diffs, 0 insertions/deletions, log still at `db861f7`** — no commits, no branch divergence. No `awaiting_plan_approval` or `awaiting_user_input`. Classic silent failure: children did not message coordinator with error payload, and coordinator had no polling/retry path at that time.

**Root causes to fix now:** (a) no explicit `BLOCKED:` reporting contract in kickoff prompts, (b) no heartbeat/poll loop after spawn, (c) single monolithic scope per child — small transient error kills entire track.

---

## 7. Next orchestration — 5 tracks (must be >3, must not silently fail)

Spawn 5 child sessions in project `a0334ef5-abfa-4f68-bffa-3d5f839ca549` (all `coordinate_with_creator:true`, `notify_on_idle:once`, `mode:autopilot`):

| # | Track | Branch hint | Files | Evidence required |
|---|-------|-------------|-------|-------------------|
| **A** | **N1 — Hamburger → visible desktop nav** | `aicincy-nav-topbar` | `base.html`, `style.css`, `_nav_groups.html` | `grep -q top-bar` on built HTML, `test_nav.py::test_desktop_top_bar_links` green |
| **B** | **R1/R5/R6 — Surface filters + sort** | `aicincy-filters-surface` | `_roster_tool.html`, `style.css`, `main.js` | `#filter-tier` visible on desktop without opening disclosure, sort adjacent to count |
| **C** | **S1/S2/S3 — Statute jump ungated** | `aicincy-statute-jump` | `statute.html`, `style.css`, `main.js` | no-JS `<form>` fallback, no `hidden` gate, expand-all + external indicator |
| **D** | **D1/a11y-F1-F3 — Lightbox + tier tooltip** | `aicincy-lightbox-a11y` | `base.html#lb`, `_card.html`, `main.js`, `style.css` | focus trap + `inert` on `#main`+`.masthead` + return focus, `aria-describedby` on tier badge |
| **E** | **Polish IA — R2/R4/N3/C1-C3** | `aicincy-polish-ia` | `index.html`, `_more_reference.html`, `base.html` footer, `style.css` | tier legend, `48 of N` banner, footer `Data & access / Legal / Project` columns, vintage adjacency |

**Dependency:** A is independent; B/C/D/E can run parallel to A but must not edit the same lines of `base.html` masthead concurrently — E's footer work is safe to parallel. If `base.html` conflict arises, B/C/D message coordinator via `send_session_message` and coordinator serializes.

**Anti-silent-failure contract (AAI § Failure behavior):**
- Each child MUST, on any blocker, send `BLOCKED: <REASON>` plus last tool output to coordinator `1a27fd0f-72ff-4900-bcdf-08ca51da58b0` via `send_session_message` — never idle with 0 diff and no message.
- Coordinator polls `get_sessions_status` every 2 min for first 10 min; any `error`/`idle` with 0 diff triggers immediate `get_session` + `send_session_message` probe and, if unresponsive, respawn with same kickoff.
- Each child validates before claiming `SAVED`: `ruff check .`, `mypy scraper web`, `pytest -q`, `JCSTREAM_SITE_BASE_URL="" python -m web.build`, `scripts/verify_public_data.py`. Only then commit.
- No claim of `RUNTIME-VERIFIED` until live `curl jcstream:generated-utc` probe after merge — children report `SAVED`+`STATIC-PASS` only.

---

## 8. State custody (resume without re-reading)

- **Objective:** visible nav (no hamburger gate on desktop) + 26-audit high/med fixes, 5 PRs.
- **Authorized scope:** templates/CSS/JS + test pins as above; no `docs/` hand-edit, no WAF log edit, no Supabase.
- **Constraints:** deterministic build, privacy model, `noindex/noarchive`, presumption-of-innocence notice preserved.
- **Active threads:** none are SAVED — all 3 prior tracks are idle/failed with 0 diff; coordinator `aicincy-scaling-waddle` is clean and is the point of resume.
- **Next executable action:** coordinator spawns 5 sessions per §7, then enters poll loop.
- **Completion evidence:** per-track `STATIC-PASS` (ruff/mypy/pytest/build/verify) + `SAVED` (commit on branch) + coordinator aggregation table.
- **Human gate:** merging PRs (owner merges via REST; coordinator does not auto-merge without explicit auth).

---

## 9. Files to read on resume (authoritative, not summaries)

- `web/templates/base.html` — masthead + drawer (lines 38-66, 107-115)
- `web/templates/_nav_groups.html` — 18 links
- `web/static/style.css` — tokens + masthead/nav §306-523
- `audit/26_ui_ux_failures_2026-10-09.md` + `audit/27_ui_ux_remediation_plan_2026-10-09.md`
- `web/templates/_roster_tool.html`, `web/templates/statute.html`, `web/templates/index.html`, `web/templates/_card.html`
- `web/static/main.js` — lightbox/filter/view-toggle

---

## 10. How to resume if this handoff is stale

1. `git -C handoff-worktree log --oneline -5` — confirm tip still `db861f7`.
2. `get_sessions_status` — check any of the 5 Tracks A-E are still `busy`/`idle`.
3. If all idle with 0 diff again → read last child error via `send_session_message` probe, then respawn that track only (do not respawn all).
4. Do not rebuild this handoff from memory — re-read §4-§7 above; they are the controlling source.

---

*Generated for session `1a27fd0f-72ff-4900-bcdf-08ca51da58b0` to satisfy `BLOCKED: VERIFIED_EXTERNAL_GRANT_REQUIRED` on silent orchestration failure. AAI cognitive interface: objective, scope, constraints, threads, next action, evidence, gate, and authorization state are custody-held here.*
