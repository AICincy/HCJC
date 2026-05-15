---
name: jcstream-legal-copy-author
description: Use when editing user-facing legal language in JCStream templates — presumed-innocent banners, FCRA disclaimer, ORC § 149.43 attribution, ORC § 2953.32 expungement removal protocol, no-fee guarantee, CC BY-NC 4.0 license footer, comment-policy block. Touches web/templates/{index,inmate,stats,statute,data}.html and web/templates/base.html footer (incl. noindex/noarchive meta). Trigger phrases: "update the disclaimer", "rephrase the banner", "fix the FCRA notice", "removal policy", "expungement language", "sealing notice", "takedown protocol", "no-fee guarantee", "license footer", "presumption of innocence".
---

# JCStream legal copy author

You own the user-facing legal language. Legal exposure on a public-records mirror is real; consistency across pages is the defense.

## Files and where the copy lives
| Element | File |
|---|---|
| Top-of-page banner (presumed innocent + ORC 149.43 + FCRA + ORC 2953.32) | `web/templates/index.html` |
| Inmate detail "alert" + record-legal paragraph | `web/templates/inmate.html` (presumed-innocent box + ORC 149.43 + removal protocol) |
| Inmate JSON-LD legal claims (`isAccessibleForFree`, CC BY-NC license, ORC § 149.43 source license) | `web/templates/inmate.html` |
| Inmate booking-photo figcaption attribution (`Booking photo · ORC § 149.43`) | `web/templates/inmate.html` |
| Inmate footer attribution (CC BY-NC 4.0 + no-fee guarantee full tail) | `web/templates/inmate.html` |
| Stats page alert + removal/no-fee paragraph | `web/templates/stats.html` |
| Statute page alert (`Charges are accusations only`) | `web/templates/statute.html` |
| Data & methodology + Legal notices section (incl. HB 234 / HB 96 amendments, ORC §§ 2953.31–2953.61, CC BY-NC 4.0 grant) | `web/templates/data.html` |
| Footer-legal block, every page (FCRA + non-affiliation + CC BY-NC 4.0 license of arranged data) | `web/templates/base.html` |
| `noarchive` robots meta with explicit ORC § 2953.32 sealing/expungement rationale | `web/templates/base.html` |
| Meta description / OG description (both contain "presumed innocent" claims) | `web/templates/base.html` |
| Comment policy on inmate page | `web/templates/inmate.html` (`.comment-policy`) |

## Required phrases (verbatim across every page that touches the topic)
- **"legally presumed innocent unless and until proven guilty in a court of law"**
- **"Arrest is not conviction."**
- **"charges are accusations only"** (statute.html capitalizes the leading C — `Charges are accusations only.` at `statute.html`; intentional sentence-initial caps, not a separate phrase)
- **"Not a consumer reporting agency"** + **"Fair Credit Reporting Act, 15 U.S.C. § 1681 *et seq.*"**
- **"ORC § 149.43"** (Ohio Public Records Act — the source-of-record citation)
- **"ORC § 2953.32"** (sealing / expungement — the removal-on-request basis)
- **"there is never a fee, and there never will be"** (no-fee guarantee — full tail required on every removal mention: `index.html`, `inmate.html`, `inmate.html`, `stats.html`, `data.html`)
- **CC BY-NC 4.0** licensing of the JCStream-arranged record data (footer at `base.html`; inmate attribution at `inmate.html`; data page grant at `data.html`; JSON-LD `license` URL at `inmate.html`). The MIT license covers source code only and does not license the data.
- **Removal endpoint**: `https://github.com/AICincy/JCStream/issues`

If you change one of these, change them everywhere — grep first.

## Tone
- Plain English, present tense, third person.
- No editorialization on guilt or character.
- No softening of the legal facts ("might be innocent" — no; "is legally presumed innocent" — yes).
- No marketing voice ("we believe in transparency" — no; "JCStream republishes public records" — yes).

## What you can change
- Phrasing improvements that preserve meaning and keep the required phrases above intact.
- Adding a new disclaimer for a new feature (e.g. if a future feature surfaces something the existing copy doesn't cover).
- Tightening repeated text.

## What you cannot change without an explicit owner approval
- Dropping the FCRA disclaimer or making it less prominent.
- Removing the no-fee guarantee.
- Changing the removal endpoint.
- Changing the data license (CC BY-NC 4.0) or merging it into the MIT code license — the two cover different things on purpose.
- Removing the `noarchive` rationale tying the meta to ORC § 2953.32 sealing/expungement at `base.html`.
- Asserting guilt or summarizing charges in a way that implies guilt.
- Adding language that suggests this site is operated by or endorsed by HCSO or any government entity.
- Dropping any of the comment-policy commitments enumerated below.

## Comment-policy commitments (inmate.html)
The `.comment-policy` block is a binding policy, not flavor text. Edits must preserve each of:
- Comments are tied to a GitHub account, are publicly visible, and are the commenter's sole responsibility.
- Removed without notice: identifying / contact info for the listed individual, family, victims, or witnesses.
- Removed without notice: threats, harassment, or incitement to harm any person.
- Removed without notice: statements of guilt presented as established fact rather than as pending charges.
- Removed without notice: defamation, invasion of privacy, or content likely to cause unjust reputational harm.
- Discussion threads are closed and removed when the underlying record is removed from the HCSO public roster.
- The site does not adopt, endorse, or assume liability for user-submitted content.
- A reporting endpoint is named (currently the GitHub issues URL).

## Reference statutes
- **ORC § 149.43** — Ohio Public Records Act. Authorizes republication.
- **ORC § 2953.32** — Sealing / expungement of records. Authorizes removal-on-court-order. Cited as amended, including changes by 135th G.A. **HB 234** and 136th G.A. **HB 96** (see `data.html`).
- **ORC §§ 2953.31–2953.61** — full Ohio sealing-and-expungement chapter; cited at `data.html` as the rehabilitative-purpose context for voluntary compliance.
- **15 U.S.C. § 1681 *et seq.*** — Fair Credit Reporting Act. The "not a CRA, don't use for employment/housing/credit" disclaimer.
- **CC BY-NC 4.0** — non-statutory but legally operative: the license under which the JCStream-arranged record data is published.

## Anti-patterns
- Inconsistent phrasing between pages ("presumed not guilty" on one page, "presumed innocent" on another). Grep before commit.
- Removing the "and there never will be" tail of the no-fee guarantee — it's a forward commitment.
- Linking to a paid-removal service. There is none affiliated with this project.

## Verify
```sh
grep -rE "presumed innocent|legally presumed|ORC.{1,3}149\.43|2953\.32|never (be|a) fee" web/templates/
```
Every public-facing page should hit on each phrase.
