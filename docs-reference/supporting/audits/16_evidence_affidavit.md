# Draft: operator affidavit authenticating the WAF-block evidence log

**Status: DRAFT. Gated on owner review and counsel sign-off before use.**
Date drafted: 2026-05-20. Companion to `audit/14_hcso_waf.md` (posture and
diagnosis), `audit/15_pra_149_43B_request.md` (the written request), and
`data/waf_block_log.json` (the record this affidavit authenticates).

## Purpose

This is a draft affidavit by the JCStream operator that authenticates
`data/waf_block_log.json` and its hash chain as a contemporaneous business
record, so counsel can put it before a court in the R.C. 149.43(C) mandamus
action. The operative paragraphs track the Ohio Evid.R. 803(6) elements (made
at or near the time, by a person with knowledge, kept in the regular course,
where making the record is the regular practice). Counsel finalizes the form
and citations.

> **Counsel note.** Choose the form: a notarized affidavit (drafted below) or an
> unsworn declaration. Confirm which Ohio practice prefers for the filing.
> Verify any statutory citations. Attach the log file and a
> `python -m scraper.verify_block_log` transcript as exhibits.

## Affidavit (template, then fill the bracketed fields)

> STATE OF OHIO )
> ) ss:
> COUNTY OF HAMILTON )
>
> **AFFIDAVIT OF [NAME]**
>
> I, [NAME], being first duly sworn, state the following of my own personal
> knowledge:
>
> 1. I am over eighteen years of age and competent to testify to the matters
>    stated here. I make this affidavit in support of [CASE OR MATTER].
>
> 2. I operate JCStream, a public-records mirror of the Hamilton County Justice
>    Center inmate roster, published at https://www.aretheyinjail.com. The
>    system retrieves the inmate records that the Hamilton County Sheriff's
>    Office (HCSO) publishes on its public inmate-search pages.
>
> 3. JCStream retrieves the roster automatically on a recurring schedule
>    (approximately every fifteen to forty-five minutes) using a scheduled
>    GitHub Actions workflow. The retrieval software identifies itself honestly
>    in its User-Agent and does not attempt to evade access controls.
>
> 4. When a retrieval cycle is blocked or returns a degraded result, the
>    software automatically records the event to a file named
>    `data/waf_block_log.json`. It records each blocked cycle, and each
>    recovery, at or near the time the event occurs, as a regular and automatic
>    part of operating the system.
>
> 5. For each blocked cycle the record includes the time in UTC; the prior and
>    current roster counts; the number and fraction of failed searches; a
>    histogram of the HTTP status codes returned; and a forensic sample of the
>    blocking response. The forensic sample includes the HTTP status, the
>    response body length, a SHA-256 hash of the response body, the first one
>    thousand characters of the body, the response headers, and the request that
>    was denied. The values of any session or credential headers (for example,
>    cookies) are replaced with a placeholder before the record is written; no
>    such values are stored.
>
> 6. Each record also carries a field named `prev_sha256`, which is the SHA-256
>    hash of the record immediately before it. These hashes form a chain:
>    altering or removing any earlier record changes the hash of every record
>    after it, which is detectable.
>
> 7. The file is append-only and is committed to a public version-control (git)
>    repository on every cycle. The repository history independently records the
>    date and time of each version of the file.
>
> 8. The integrity of the file can be checked by running the command
>    `python -m scraper.verify_block_log`, which walks the hash chain and reports
>    any break. [On (DATE) I ran this command, and it reported the chain intact
>    across (N) records. A true copy of that output is attached as Exhibit __.]
>
> 9. I have not altered, edited, or removed any record in
>    `data/waf_block_log.json`. The file is a true and accurate record of the
>    blocking events it describes, made automatically by the system in the
>    regular course of its operation.
>
> 10. Attached as Exhibit __ is a true and accurate copy of
>     `data/waf_block_log.json` as of (DATE).
>
> Further affiant sayeth naught.
>
> _______________________________
> [NAME], Affiant
>
> Sworn to and subscribed before me this ____ day of ____________, 20__.
>
> _______________________________
> Notary Public

## Counsel checklist before use

1. Choose the form (notarized affidavit above, or an unsworn declaration) per
   the practice for this filing.
2. Fill the bracketed fields. Run `python -m scraper.verify_block_log`, capture
   the output, and attach it as the Exhibit referenced in paragraph 8.
3. Attach the log file (paragraph 10), and, if useful, the `audit/14` diagnosis
   and the `audit/15` request as further exhibits.
4. Consider whether a separate custodian-of-records affidavit from HCSO is
   needed for any records HCSO itself produces in response to the request.
