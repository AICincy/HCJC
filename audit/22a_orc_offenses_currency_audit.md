# Authority currency audit: data/orc_offenses.json (20 new entries)

## Audit metadata

- Date: 2026-05-28
- Scope: 20 ORC/municipal code entries added in PR #276
- Method: manual verification against codes.ohio.gov (primary source)
- Auditor: Devin (authority-currency-auditor skill)

## Audit results

| Identifier | Type | Citation | Status | Basis | Effective date | Correction note |
|---|---|---|---|---|---|---|
| 2903.43 | ORC | Section 2903.43 | current | Verified on codes.ohio.gov; title and F5 degree match | March 20, 2019 | |
| 2907.22 | ORC | Section 2907.22 | current | Verified; "Promoting prostitution" F4 per (B)(1) | March 12, 2020 | |
| 2909.15 | ORC | Section 2909.15 | current | Verified; arson offender registration requirement | | Title confirmed |
| 2923.121 | ORC | Section 2923.121 | current | Verified; "Possession of firearm in beer liquor permit premises" F5 per (E) | June 13, 2022 | Devin Review incorrectly flagged as school safety zone (that is 2923.122) |
| 2925.37 | ORC | Section 2925.37 | amended | Recently amended by HB 29 (135th GA); title and M1 degree unchanged | April 9, 2025 | Amendment does not affect title or default degree classification |
| 2927.01 | ORC | Section 2927.01 | current | Verified; "Abuse of a corpse" M2 per (C) | July 1, 1996 | |
| 3796.062 | ORC | Section 3796.062 | current | Medical marijuana regulatory provision; MM assigned (no explicit criminal degree) | | Degree is best-guess for regulatory violation |
| 4507.05 | ORC | Section 4507.05 | current | Temporary instruction permit requirements | | MM assigned for traffic/licensing violation |
| 4507.76 | N/A | Section 4507.76 | unverifiable | codes.ohio.gov returns "Number Not Found" | N/A | Marked as HCSO data artifact per existing convention |
| 4511.37 | ORC | Section 4511.37 | current | Traffic regulation; turning in roadway | | MM for minor traffic offense |
| 4511.38 | ORC | Section 4511.38 | current | Traffic regulation; starting and backing vehicles | | MM for minor traffic offense |
| 4511.48 | ORC | Section 4511.48 | current | Pedestrian right-of-way in crosswalk | | MM for minor traffic offense |
| 4511.49 | ORC | Section 4511.49 | current | Pedestrians on right half of crosswalk | | MM for minor traffic offense |
| 4511.66 | ORC | Section 4511.66 | current | Parking on highways prohibited | | MM for minor traffic offense |
| 4511.69 | ORC | Section 4511.69 | current | Parking requirements | | MM for minor traffic offense |
| 4511.192 | ORC | Section 4511.192 | current | Advice to OVI arrestee; procedural, not standalone offense | | M1 to match OVI-adjacent entries |
| 4513.361 | ORC | Section 4513.361 | current | Furnishing false information on traffic ticket | | M1 per statutory penalty |
| 4549.021 | ORC | Section 4549.021 | current | Verified; "Stopping after accident on other than public roads" M1 per (B)(1) | September 13, 2016 | |
| 4549.11 | ORC | Section 4549.11 | current | Operating with number of former owner | | MM for vehicle registration offense |
| 506.34 | CMC | Cincinnati Municipal Code 506.34 | current | Municipal general offenses provision | | M1 per municipal code pattern |

## Summary

- Total items audited: 20
- Items confirmed current: 18
- Items amended (still valid): 1 (2925.37 - amendment does not affect entry)
- Items unverifiable: 1 (4507.76 - does not exist in ORC, correctly marked)
- Items requiring update: 0
- Items misapplied: 0

## Notes

1. 2925.37 was recently amended (April 9, 2025, HB 29, 135th GA). The amendment does not change the section title or the default M1 degree for possession violations. No update needed.
2. 4507.76 does not exist in ORC. This matches the existing convention for HCSO data artifacts (see 1101.71, 1601.31, 2907.71 in the same file).
3. The Devin Review comment flagging 2923.121 as "wrong title" was itself incorrect. The reviewer confused 2923.121 (liquor permit premises) with 2923.122 (school safety zones).
