# Evidence Log: HCSO Inmate Detail Page Outage
## Chain of Custody

**Investigation opened:** 2026-09-20T02:45:17Z (UTC)
**Investigator:** Automated collection via curl
**Subject:** https://www.hcso.org/justice-center-services/inmate-search/

### Collection Method
1. Fetched 5 surname list pages (SMITH, JOHNSON, WILLIAMS, BROWN, JONES) at 2026-09-20T02:45:18Z
2. Extracted 94 unique inmate IDs from list pages
3. Tested 30 inmate IDs x 2 URL variants (single-slash and double-slash) = 60 detail fetches
4. Each fetch saved with timestamp in filename, full HTTP response body preserved
5. SHA-256 hashes computed for all collected files

### Findings
- **List pages:** 5/5 returned HTTP 200 (operational)
- **Detail pages:** 60/60 returned HTTP 404 (all failed)
- **Response:** Identical 121,499-byte WordPress "Page not found" page
- **Title:** "Page not found - Hamilton County Sheriff's Office"

### File Inventory
- `list-*.html` (5 files): Surname search result pages, HTTP 200
- `detail-*-single-*.html` (30 files): Detail pages, single-slash URL, HTTP 404
- `detail-*-double-*.html` (30 files): Detail pages, double-slash URL, HTTP 404
- `fetch-log.tsv`: Timestamped log of all 60 fetches with HTTP codes
- `inmate-ids.txt`: 94 unique IDs extracted from list pages
- `SHA256SUMS`: SHA-256 hashes of all evidence files

### Verification
Run `sha256sum -c SHA256SUMS` to verify file integrity.

### Timeline: Sustained Outage (Two Independent Verifications)

**Verification 1: GitHub Actions sweep (automated infrastructure)**
- Timestamp: 2026-09-19T23:32:41Z to 23:34:02Z
- Source: GitHub Actions run 35476388990, logs_96066537026.zip
- Result: 198 detail fetches returned HTTP 404
- Watchdog: 0/132 yielded names, 0/132 yielded photos
- Action: Roster write BLOCKED to preserve last-good data
- Sweep result: roster_ok=False, rc=0

**Verification 2: Direct manual collection (independent)**
- Timestamp: 2026-09-20T02:45:18Z to 02:47:xxZ
- Source: Direct curl fetches from investigator workstation
- Result: 60/60 detail fetches returned HTTP 404
- Sample: 30 unique inmate IDs x 2 URL variants
- Response: Identical 121,499-byte WordPress 404 page

**Duration:** Minimum 3 hours 13 minutes of sustained outage
**Conclusion:** Not transient. Detail pages systematically non-functional across multiple verification points.

### Timeline continued: sustained outage (verifications 3-4) and notice record

**Verification 3: GitHub Actions sweep (automated infrastructure)**
- Timestamp: 2026-09-20T12:19:34Z (run start) to ~12:23Z (detail-fetch window)
- Source: GitHub Actions run 35510288488 (scheduled sweep)
- Result: 195 detail fetches: 143 HTTP 404, 52 HTTP 503; zero photos yielded
- Sweep result: roster_ok=False, clean=True, seen=1212, current=1212
- Failure mode varies by request/network (404 vs 503 mix); channel still unusable

**Verification 4: Direct manual check (independent)**
- Timestamp: 2026-09-20T13:18:13Z
- Source: single curl fetch from investigator workstation
- URL: https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/?id=1261360
- Result: HTTP 403, 162-byte body, title "403 Forbidden" (sha256 9c8c654fe26ffff6...)
- Failure mode has shifted over the outage window (404 -> 503 mix -> 403); detail channel remains non-functional throughout

**Notice record (metadata only; no action taken on its contents)**
- Sent: 2026-09-20T03:23:45Z (2026-09-19 23:23:45 EDT)
- From: JCStream <OhioGovRequestor@proton.me>; To: publicrecords@hcso.org (Bcc: jaredcincy@gmail.com)
- Subject: "Notice of Denial of Access to Public Records"
- Attachment: "HCSO Evidence Package 2026-09-19.zip" (zip sha256 e8858f042a3ad102ba4f47e77ed84e54c075343718f6657250ed7482bdf0fba20, as stated in the message)
- Stored at: workspace/user/files/Notice_of_Denial_of_Access_to_Public_Records_2026-09-19T23_23_45-04_00.eml
- Purpose recorded at the user's direction: duration tracking for the outage timeline. No legal conclusion is drawn in this log.

**Duration:** First documented detail failure 2026-09-19T23:32:41Z to latest verification 2026-09-20T13:18:13Z = ~13h 46m of documented outage, still ongoing at log time.
**Conclusion (unchanged):** Not transient. Detail pages systematically non-functional across four verification points spanning ~14 hours, via two independent collection paths.

**Comparator check: Data Cincinnati (data.cincinnati-oh.gov)**
- Checked 2026-09-20T13:20:30Z at the user's direction ("if Data Cincinnati is also down, that needs recorded the same way").
- Result: OPERATIONAL. Portal root HTTP 200 (641,549 bytes); Socrata catalog API (api.us.socrata.com, domains=data.cincinnati-oh.gov) HTTP 200 (9,142 bytes, real catalog data).
- No Cincinnati outage to record. The 6-hourly watch now probes both Cincinnati endpoints alongside the HCSO probes, so any future Cincinnati downtime is logged in the same TSV the same way.
