# Audit — jcstream-stylesheet-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-stylesheet-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-stylesheet-author.md
- **Verdict**: Yellow
- **One-line summary**: Token system, anti-patterns, and tier palette are accurate, but the mobile-breakpoint count and ladder-cell line range are wrong, and several owned components (lightbox, recent-bookings photo-stack, CFS/dispatch map, stacked-bar/timeline, stats page) go unmentioned.

## A. Drift
- SKILL.md:34 says "(six occurrences: `:183, :513, :880, :1081, :1177`)" — only 5 line numbers listed and the real count of `@media (max-width: 720px)` is **12** (`web/static/style.css:183, 513, 880, 1081, 1177, 1292, 1359, 1525, 1580, 1684`, plus inline ones at `:1498, :1616`). The trailing print-mode mobile block at `style.css:1684` is the canonical bottom anchor, not `:1177`.
- SKILL.md:25 places ladder cells at "`style.css:1008-area`". Line 1008 is `.tier-row` — actual `.ladder-grid` / `.ladder-cell` / `.ladder-F1`…`.ladder-MM` definitions are at `web/static/style.css:1217-1244`, inside the "Severity ladder" section (`web/static/style.css:1195`).
- SKILL.md:11 says ":root block at `style.css:5-54`". `:root` actually opens at `web/static/style.css:7` and closes at `:54` — minor off-by-two on the start.
- SKILL.md:17 lists tier tokens but omits `--tier-felony-bd` / `--tier-misd-bd` callout that they're border-color twins of the bg pair (`web/static/style.css:38-39`); existing copy is technically correct, just incomplete.
- SKILL.md:16 lists `--ok` and `--misd` but both literally evaluate to `#4f7c3a` (`web/static/style.css:29-30`) — readers may assume they are independently tunable; they currently are not.

## B. Coverage gaps
- `--border` / `--border-hi` (`web/static/style.css:13-14`) and `--accent-bg-2` (`:25`) are not in the token table at SKILL.md:13-21 even though they're load-bearing for hover/border treatments (`web/static/style.css:220, 673`).
- City-accent tokens `--cincy-navy` / `--cincy-red` (`web/static/style.css:42-43`) are unmentioned — they're used by CFS captions and easy to clobber.
- `.lightbox` system at `web/static/style.css:1363-1409` (used by inmate mugshot zoom, suppressed in print at `:1664`) — owned, undocumented.
- Recent-bookings photo-stack (`.rb-grid`, `.rb-card` with its own `content-visibility` at `web/static/style.css:768`, plus `@media (max-width:1080px)` and `:540` breakpoints at `:756-757`) — these are the **only non-720 breakpoints** in the file and contradict the "extend the existing 720 px block" rule (SKILL.md:34).
- Dispatch / CFS map block (`web/static/style.css:1593-1616`) and Comments / Giscus block (`:1640-1652`) — both interactive-only, both already correctly suppressed in `@media print` (`:1665`); SKILL.md doesn't tell future authors to add new interactive elements to that print-suppression list.
- Stacked severity bar (`.stacked-leg` at `web/static/style.css:1483-1498`), top-list (`:1500`), court calendar (`:1530-1583`), bond box-and-whisker (`:1297-1362`), time-in-custody timeline (`:1252-1295`), stats KPIs (`:1458-1481`) — entire stats/inmate visualization layer is unmentioned.
- `.view-toggle[aria-pressed="true"]` (`web/static/style.css:478`) — the table-mode toggle handle that drives `body.is-table`; mentioned consequentially but not by name.
- `@view-transition` (`web/static/style.css:60`) and `prefers-reduced-motion` guard (`:59`) — affect cross-page animation; should be flagged so authors don't break them.

## C. Trigger-phrase quality
- Current description (paraphrased): "Use when editing web/static/style.css. Covers light-theme tokens, 10-tier ladder, body.is-table, content-visibility, 720 px breakpoint, print rule. Trigger phrases: restyle the cards / fix the tier colors / make the hero bigger / add a CSS rule."
- Issues: triggers skew toward homepage cards/hero. Common phrasings like "tweak the mugshot lightbox", "table view is broken on mobile", "the print stylesheet drops too much", "recolor the F3 chip", "fix the dispatch map height", "the comments section overlaps" wouldn't obviously match. Also "stylesheet" / "CSS" as bare verbs ("the CSS is broken", "edit style.css") are missing.
- Proposed rewording (additive only): add `, "edit the stylesheet", "tweak the lightbox", "fix the table view", "recolor the F3 chip", "tune the print layout"` to the trigger list.

## D. Applicability
- Domain is alive and central — `web/static/style.css` is 2765 lines, edited every design pass, owns the entire visual surface; skill should not be retired.

## Recommended fixes (priority order)
1. Fix the ladder-cell line range (point at `web/static/style.css:1217-1244`, not `:1008-area`) and the mobile-breakpoint enumeration (12 occurrences, not 6; list the real anchor lines or stop enumerating).
2. Acknowledge the two non-720 breakpoints on `.rb-grid` (`:756-757`) so the "no new breakpoints" rule isn't taken as absolute.
3. Add tokens `--border`, `--border-hi`, `--accent-bg-2`, `--cincy-navy`, `--cincy-red` to the table; note that `--ok` and `--misd` (and `--danger` / `--warn`) currently share hex values.
4. Add a "Components you also own" mini-list: lightbox, recent-bookings stack, dispatch map, comments, stacked-bar, timeline, bond box-and-whisker, stats KPIs — each with its `style.css:` anchor.
5. Broaden the trigger phrases as proposed in section C.
