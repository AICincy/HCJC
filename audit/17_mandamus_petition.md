# Draft: R.C. 149.43(C) petition for a writ of mandamus

**Status: DRAFT. Gated on owner review and counsel sign-off. Counsel selects the
court and finalizes all citations and relief before any filing.**
Date drafted: 2026-05-20. Final piece of the legal-record set:
`audit/15_pra_149_43B_request.md` (the written request),
`audit/16_evidence_affidavit.md` (the authenticating affidavit), and
`data/waf_block_log.json` (the contemporaneous denial record).

## Purpose

This is a skeleton verified petition for a writ of mandamus under R.C. 149.43(C)
to compel production of the public records sought in `audit/15` and to recover
the statutory damages, costs, and fees the Public Records Act allows. It is a
starting structure for counsel, not a filing. It assumes the R.C. 149.43(B)
request has been sent and then ignored or denied.

> **Counsel note.** This is the most consequential document in the set. Verify
> every `[VERIFY]` item against current law and rules before relying on it:
> the proper court and the relator's choice of forum (R.C. 149.43(C)(1)(b)
> permits the court of common pleas, the court of appeals, or the Supreme Court
> of Ohio), the pleading and verification requirements, the statutory-damages
> cap and trigger, and the fee standard. Confirm the request was transmitted by
> a method that satisfies the damages trigger before pleading damages.

## Petition (skeleton, then fill the bracketed fields)

> IN THE [COURT] `[VERIFY forum]`
>
> STATE OF OHIO EX REL. [RELATOR NAME], )
> Relator, )
> )
> v. ) Case No. __________
> )
> [RESPONDENT: e.g., HAMILTON COUNTY ) VERIFIED PETITION FOR
> SHERIFF, in official capacity], ) WRIT OF MANDAMUS
> Respondent. ) (R.C. 149.43(C))
>
> **I. Nature of the action**
>
> 1. This is an action in mandamus under R.C. 149.43(C) `[VERIFY]` to compel
>    Respondent, a public office and the custodian of public records, to produce
>    records that Respondent has failed to make available in violation of the
>    Ohio Public Records Act, R.C. 149.43.
>
> **II. Parties, jurisdiction, and venue**
>
> 2. Relator is [identity / capacity].
>
> 3. Respondent is the records custodian for the Hamilton County Justice Center
>    inmate roster and the public inmate-search system at hcso.org.
>
> 4. This Court has jurisdiction over an original action in mandamus under
>    [constitutional / statutory basis] `[VERIFY]`, and venue is proper because
>    [basis] `[VERIFY]`.
>
> **III. Facts**
>
> 5. Respondent maintains and publishes a public inmate roster, which is a
>    public record under R.C. 149.43(A)(1) `[VERIFY]`.
>
> 6. On [DATE], Relator sent Respondent a written public-records request (the
>    request is attached as Exhibit A and reproduced from
>    `audit/15_pra_149_43B_request.md`) for (a) a machine-readable export of the
>    roster and (b) the records of Respondent's restriction of automated access
>    to the public inmate-search system.
>
> 7. Respondent [denied the request / failed to respond within a reasonable
>    period of time / produced only a partial response], as described in
>    [Exhibit __].
>
> 8. Independently, Respondent's web application firewall has blocked Relator's
>    good-faith automated retrieval of the public roster on the dates and at the
>    times recorded contemporaneously in `data/waf_block_log.json` (Exhibit B),
>    which is authenticated by the affidavit attached as Exhibit C (drafted at
>    `audit/16_evidence_affidavit.md`). Each record carries the HTTP status, the
>    response headers, a hash of the response body, and a `prev_sha256` chain
>    that, with the public git commit history, establishes the record's
>    integrity.
>
> 9. The public web pages for individual records remained available to ordinary
>    browser traffic during the same period, while automated retrieval of the
>    same public records was blocked.
>
> **IV. Claim for relief (mandamus)**
>
> 10. Relator has a clear legal right to the requested records, Respondent has a
>     clear legal duty to provide them under R.C. 149.43(B) `[VERIFY]`, and
>     Relator has no adequate remedy in the ordinary course of law.
>
> 11. Relator is entitled to a writ compelling Respondent to produce the
>     requested records.
>
> **V. Statutory damages, costs, and fees**
>
> 12. Relator is entitled to statutory damages under R.C. 149.43(C)(2) `[VERIFY
>     amount and trigger]`, and to court costs and reasonable attorney fees
>     under R.C. 149.43(C)(3) `[VERIFY standard]`.
>
> **VI. Prayer for relief**
>
> Relator respectfully requests that the Court:
>
> a. Issue a writ of mandamus compelling Respondent to produce the records
>    described in the request;
>
> b. Award statutory damages, court costs, and reasonable attorney fees as
>    R.C. 149.43(C) allows `[VERIFY]`; and
>
> c. Grant any further relief the Court deems just.
>
> Respectfully submitted,
> [COUNSEL NAME, BAR NO., FIRM, CONTACT] `[counsel of record]`
>
> **Verification**
>
> I, [RELATOR], declare under penalty of perjury that the factual statements in
> this Petition are true to the best of my knowledge. `[VERIFY verification form
> required by the chosen court]`
>
> _______________________________
> [RELATOR]

## Exhibit list

| Exhibit | Source |
|---|---|
| A | The written R.C. 149.43(B) request (`audit/15_pra_149_43B_request.md`, as sent). |
| B | `data/waf_block_log.json` as of the filing date. |
| C | The operator affidavit (`audit/16_evidence_affidavit.md`, executed). |
| D | The `python -m scraper.verify_block_log` transcript showing the chain intact. |

## Counsel checklist before filing

1. Select the forum and verify the original-jurisdiction basis (common pleas,
   court of appeals, or Supreme Court of Ohio).
2. Confirm the request was sent and that the response window has run; attach the
   send confirmation.
3. Verify the statutory-damages amount, cap, and trigger, and the
   attorney-fees standard, against current R.C. 149.43(C).
4. Execute the affidavit (`audit/16`) and run `python -m scraper.verify_block_log`
   to produce Exhibit D.
5. Confirm the verification form the chosen court requires.
