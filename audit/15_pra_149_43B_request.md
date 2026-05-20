# Draft: written R.C. 149.43(B) public-records request to HCSO

**Status: DRAFT. Gated on owner review and counsel sign-off before it is sent.**
Date drafted: 2026-05-20. Companion to `audit/14_hcso_waf.md` (the
document-don't-evade posture) and the contemporaneous denial record in
`data/waf_block_log.json`.

## Purpose

The HCSO inmate-search system is blocking JCStream's automated retrieval of the
public roster (see `audit/14_hcso_waf.md`). This draft is the written
R.C. 149.43(B) request that (1) asks for the roster itself in a machine-readable
medium, and (2) asks for the records of the access restriction (the WAF rule,
policy, and related communications). A clean written request, and any denial or
non-response to it, is the predicate for the R.C. 149.43(C) mandamus record the
owner is building. Counsel finalizes and sends; this file is the starting text.

> **Counsel note on citations.** The subsection letters below reflect
> R.C. 149.43 as commonly cited. The section has been amended repeatedly and the
> lettering has shifted across versions. Verify every citation against the
> current statute before sending. Items marked `[VERIFY]` are the ones most
> likely to have moved.

## Recipient and channel

| Field | Value |
|---|---|
| Office | Hamilton County Sheriff's Office (records custodian for the Justice Center inmate roster) |
| County records officer | `HCAdmin@hamilton-co.org` (routes to HCSO; the verified central public-records contact) |
| HCSO web form | `https://www.hcso.org/public-records-requests/` |
| HCSO phone | 513-946-6400 |
| Suggested method | Send by email to the county records officer AND submit through the HCSO web form, so two dated channels exist. Counsel may prefer certified mail for the formal record. |

## Request letter (copy-paste, then fill the bracketed fields)

> Subject: Public Records Request under R.C. 149.43 (inmate roster export and
> access-restriction records)
>
> To the Records Custodian, Hamilton County Sheriff's Office:
>
> Under the Ohio Public Records Act, R.C. 149.43, I request copies of the
> following public records. I am willing to receive all responsive records
> electronically, at no charge if delivered by email or download link.
>
> **Item 1: The current inmate roster, in a machine-readable medium.**
> An electronic, machine-readable export (for example JSON, CSV, or a database
> query result) of the current Hamilton County Justice Center inmate roster,
> containing the same fields the office already publishes on its public
> inmate-search and inmate-detail pages, including for each individual: inmate
> number, booking number, name, booking date, projected release date, holder
> status, and each charge row (charge description, ORC code, court and case
> number, bond type, bond amount, and disposition). If the office maintains this
> data in an electronic system, I ask to receive it in the medium in which it is
> kept, as I am entitled to choose under R.C. 149.43(B)(6) `[VERIFY]`. I am not
> requesting physical inspection or pickup.
>
> **Item 2: Records concerning the restriction of automated access to the
> public inmate-search system at hcso.org.** Specifically:
>
> a. The web application firewall (WAF), bot-management, or rate-limit rule(s)
>    and any IP blocklist or allowlist applied to the inmate-search and
>    inmate-detail endpoints.
>
> b. Records identifying the vendor or service that provides that filtering
>    (for example Cloudflare, Akamai, Imperva, or F5), and the contract,
>    purchase order, or service order for it.
>
> c. Any policy, directive, configuration standard, or written justification
>    for blocking, throttling, or denying automated (programmatic) retrieval of
>    the public inmate records.
>
> d. The records-retention schedule that governs the WAF logs and the
>    inmate-search access logs.
>
> e. Communications among HCSO staff, and between HCSO and the vendor in (b),
>    concerning blocking, throttling, or denying access to the inmate-search
>    system from automated or datacenter clients, for the period [START DATE]
>    through the date of this request.
>
> I do not need to state my identity or the purpose of this request as a
> condition of receiving these records (R.C. 149.43(B)(4)-(B)(5) `[VERIFY]`).
> Please provide the records within a reasonable period of time
> (R.C. 149.43(B)(1) `[VERIFY]`). If you deny any part of this request, please
> provide the denial in writing with an explanation that includes the legal
> authority for the denial, as R.C. 149.43(B)(3) `[VERIFY]` requires, and
> provide the remaining responsive records.
>
> If any portion is voluminous or needs clarification, please contact me so I
> can narrow or prioritize rather than have the request denied.
>
> Thank you,
> [NAME]
> [EMAIL / PHONE / MAILING ADDRESS]
> [DATE]

## Statutory basis (counsel to confirm lettering)

| Provision (as commonly cited) | Use in this request |
|---|---|
| R.C. 149.43(B)(1) `[VERIFY]` | Records made available within a reasonable period of time. |
| R.C. 149.43(B)(3) `[VERIFY]` | A denial must be in writing with the legal authority for it. |
| R.C. 149.43(B)(4)-(B)(5) `[VERIFY]` | No requirement to disclose identity or purpose as a condition. |
| R.C. 149.43(B)(6) `[VERIFY]` | Requester may choose the medium the office keeps the record in (the machine-readable hook for Item 1). |
| R.C. 149.43(C) `[VERIFY]` | Mandamus remedy, with potential statutory damages, court costs, and attorney fees, if the request is ignored or improperly denied. |

## Evidentiary linkage

This request is part of the documented record, not a workaround:

- `data/waf_block_log.json` is the contemporaneous, hash-chained record of each
  blocked cycle and recovery (status, headers, body sample, SHA-256). It
  documents that automated access was in fact denied at the times stated.
- `audit/14_hcso_waf.md` records the diagnosis (WAF blocking the runner IP) and
  the deliberate decision not to evade the block while this record is built.
- A denial of, or non-response to, Item 1 while the public web pages remain up
  is itself evidence for the access theory; Item 2 seeks the office's own
  records of the restriction.

## Counsel checklist before sending

1. Verify every `[VERIFY]` citation against the current R.C. 149.43.
2. Decide whether to send Item 1 and Item 2 as one request or two (a roster
   export may be answered faster than the access-restriction records).
3. Choose the channel(s): email to the county records officer, the HCSO web
   form, and/or certified mail. Preserve the dated send confirmation.
4. Set the `[START DATE]` in Item 2(e) (suggest the first logged block in
   `data/waf_block_log.json`).
5. Decide whether to attach or link the evidence log, or hold it for the
   mandamus filing.
6. Plan the R.C. 149.43(C) step (mandamus posture and any pre-suit
   requirements) if the request is ignored or denied.
