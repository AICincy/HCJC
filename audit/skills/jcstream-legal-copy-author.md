# Audit — jcstream-legal-copy-author

- **Date**: 2026-05-14
- **SKILL.md**: .claude/skills/jcstream-legal-copy-author/SKILL.md
- **Paired agent**: .claude/agents/jcstream-legal-copy-author.md
- **Verdict**: Yellow
- **One-line summary**: Every named claim verifies, but the SKILL omits the CC BY-NC 4.0 licensing copy and the inmate page's "no-fee" tail is inconsistent with the contract the SKILL itself asserts.

## A. Drift
- Path/line claims hold: `web/templates/index.html:5-9` is the legal banner (`<aside class="banner" aria-label="Legal notice">` opens at line 5, closes at line 9). Verified phrases at `index.html:6,7,8`, `base.html:71`, `stats.html:12,202`, `statute.html:13`, `data.html:60,68,75,84-88`, `inmate.html:62,83,295`.
- **Required-phrase contract violation in actual code, not in SKILL**: SKILL.md:29 says the no-fee guarantee is "**repeated on every page that mentions removal**" with the verbatim tail "and there never will be". `web/templates/inmate.html:83` says "**there is never a fee**" (no tail) and `web/templates/inmate.html:290` repeats the short form. This is an internal inconsistency the SKILL should flag as something to *fix*, not as canonical state.
- SKILL.md:13 says the index banner contains "ORC 2953.32" — confirmed at `web/templates/index.html:8`.
- SKILL.md:30 removal endpoint `https://github.com/AICincy/JCStream/issues` matches every site occurrence (`index.html:8`, `inmate.html:83,290,307`, `stats.html:202`, `data.html:78,101`).

## B. Coverage gaps
- **CC BY-NC 4.0 license assertion is unowned**: appears at `web/templates/base.html:71`, `web/templates/inmate.html:28,288`, `web/templates/data.html:110`. This is a legal-copy claim (licensing the JCStream-arranged data) and the SKILL never mentions it.
- **`noarchive` robots meta with sealing/expungement rationale** at `web/templates/base.html:7-10` — explicit ORC § 2953.32 reasoning the SKILL does not cover.
- **JSON-LD legal claims** at `web/templates/inmate.html:18-33` ("isAccessibleForFree", license URL → ORC § 149.43) — structured-data legal claims not mentioned.
- **Figcaption attribution** `Booking photo · ORC § 149.43` at `web/templates/inmate.html:45` — third statute citation per inmate page, not listed.
- **HB 234 / HB 96 amendment references** at `web/templates/data.html:76`, plus the broader **ORC §§ 2953.31–2953.61** citation at `web/templates/data.html:81` — both extend the "Reference statutes" list at SKILL.md:52-55.
- **Meta `description` and `og:description`** at `web/templates/base.html:12,19` — SKILL.md:19 lists these in the table but the body never names them as required-phrase carriers (both contain "presumed innocent" claims).
- **Comment-policy block content** at `web/templates/inmate.html:295-308` is much richer than the SKILL hints (covers removal of identifying info, threats, defamation, thread closure on roster removal) — the SKILL says "comment-policy block" but doesn't enumerate the categories the policy commits to.
- **`statute.html:13` alert** uses "Charges are accusations only" — SKILL's required-phrase list (SKILL.md:25) is "charges are accusations only" (lowercase c) — verify casing intent.

## C. Trigger-phrase quality
- Current description (paraphrased): "user-facing legal language… presumed-innocent banners, FCRA disclaimer, ORC § 149.43, ORC § 2953.32, no-fee guarantee, comment-policy block. Triggers: 'update the disclaimer', 'rephrase the banner', 'fix the FCRA notice', 'removal policy'."
- Issues: triggers miss common phrasings — "expungement", "sealing", "takedown", "presumption of innocence", "no-fee", "comment policy", "DMCA-style removal", "license notice", "CC BY-NC". A user saying "fix the expungement language" or "update the takedown policy" would not obviously route here from triggers alone.
- Proposed rewording: append "expungement language", "sealing notice", "takedown protocol", "no-fee guarantee", "license footer", "presumption of innocence" to the trigger list.

## D. Applicability
- Domain is alive — six owned templates plus the base footer all carry active legal copy that ships on every page; the skill is load-bearing, not stale.

## Recommended fixes (priority order)
1. Add CC BY-NC 4.0 licensing as a fourth legal-copy domain (footer, inmate attribution, data.html) — currently invisible to this specialist.
2. Resolve the no-fee tail inconsistency: either update the SKILL contract to say "tail required only on the homepage, stats, and data" or flag `inmate.html:83,290` as broken and require the tail there too.
3. Mention the `base.html:7-10` `noarchive` rationale and the `inmate.html:18-33` JSON-LD license claim under "Files and where the copy lives".
4. Expand "Reference statutes" with HB 234 / HB 96 amendments and ORC §§ 2953.31–2953.61 (already in `data.html:76,81`).
5. Broaden trigger phrases to include "expungement", "sealing", "takedown", "license", "no-fee".
6. Enumerate the comment-policy commitments (identifying info, threats, defamation, thread-closure-on-removal) so edits can't silently drop categories.
