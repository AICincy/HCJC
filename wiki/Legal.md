# Legal posture

This page is a plain-English summary for contributors and the curious. The authoritative,
user-facing notices live on the site: **[aretheyinjail.com/data/#legal](https://www.aretheyinjail.com/data/#legal)**.
Nothing here is legal advice.

## Presumption of innocence

Everyone listed on the site is **legally presumed innocent unless and until proven guilty in
a court of law**. An arrest or booking record is not evidence of guilt. Charges may be reduced,
dismissed, or result in acquittal. JCStream does not editorialise about guilt or innocence.
The presumption-of-innocence notice appears on the homepage banner, on every inmate page, and
in the public-commentary policy.

## Authority to publish

The right of public access to these records is established by the **Ohio Public Records Act,
[ORC § 149.43](https://codes.ohio.gov/ohio-revised-code/section-149.43)**. JCStream is
generated *exclusively* from records the Hamilton County Sheriff's Office already publishes at
[hcso.org](https://www.hcso.org/justice-center-services/inmate-search/). The site does not
collect, retain, or distribute anything HCSO doesn't already make public.

## No archive — record removal & sealing

When HCSO removes a record from its public inmate roster, JCStream removes the corresponding
record on its **next automated update cycle** (typically within 30 minutes). **There is no
historical archive of removed records.** For records subject to a court order of sealing or
expungement under **[ORC § 2953.32](https://codes.ohio.gov/ohio-revised-code/section-2953.32)
(as amended** — incl. 135th G.A. HB 234 and 136th G.A. HB 96 — and §§ 2953.31–2953.61), the
site removes the record on notice of the order. Submit notice (or report any error) via a
[GitHub issue](https://github.com/AICincy/JCStream/issues). Removal and correction requests
are processed **at no cost — there is never a fee, and there never will be.** If a third party
claims to offer paid removal of records on this site, they are not affiliated with JCStream
and cannot fulfil that promise.

## Not a consumer reporting agency (FCRA)

JCStream **is not a consumer reporting agency** as defined by the Fair Credit Reporting Act,
15 U.S.C. § 1681 *et seq.* The information here has not been collected, in whole or in part,
for furnishing consumer reports. **Do not use this site** to make decisions about consumer
credit, employment, insurance, housing, tenant screening, or any other FCRA-governed purpose.
This notice appears on the homepage banner, the footer, every inmate page, and `/data/#legal`.

## Non-affiliation

JCStream is an independent, non-governmental project. It is **not affiliated with, endorsed
by, or operated by** the Hamilton County Sheriff's Office, Hamilton County, the State of Ohio,
or any government entity. The MIT licence governs the *source code* only; it does not (and
cannot) licence the underlying public-records data, which is governed by Ohio law.

## Public commentary

If commentary is enabled on an inmate page (via Giscus / GitHub Discussions), comments are
tied to the commenter's GitHub account, are public, and are the commenter's sole
responsibility. Removed without notice: identifying/contact info for the listed person, their
family, victims, or witnesses; threats, harassment, or incitement; statements of guilt
presented as established fact rather than as the pending charges on the record; and content a
reasonable person would recognise as defamatory, invasive of privacy, or likely to cause
unjust reputational harm. Threads close and are removed when the record leaves HCSO's roster.
The site does not adopt, endorse, or assume liability for user-submitted content.

## Scraping ethics

The HCSO scraper honours `robots.txt` and a polite User-Agent and runs at the crawl-delay the
site allows (0 s). It does **not** bypass CAPTCHAs. courtclerk.org's `robots.txt` disallows
`/data/`, so JCStream **links** to case records there but never scrapes them; codes.ohio.gov's
`robots.txt` disallows everything, so the ORC title/degree lookup is **hand-curated** in
`data/orc_offenses.json`. RCIC/NCIC and other restricted criminal-history systems (28 CFR
Part 20) are not touched.

## Corrections

See **[[Contributing]]** for the issue forms. The fastest path for a data error, a sealing
order, or an expungement is: open an issue → it's removed on notice. No fee, no exceptions.
