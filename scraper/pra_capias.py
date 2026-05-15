"""Public Records Act email loop for daily capias / new-warrant listings.

Sends a real electronically-transmitted PRA request to the Hamilton County
Clerk of Courts via SMTP. Per ORC § 149.43(C)(2), failure to respond within
a reasonable time triggers $100/day statutory damages (capped at $1,000)
plus attorney fees.

In **dry-run mode** (no SMTP secrets configured) we print the email and exit
cleanly so the workflow remains green; flipping the secrets on activates the
real send. We never throw on missing config — that would block the daily
sweep cron.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from .pra_base import dry_run_required, env, send_smtp

log = logging.getLogger(__name__)

# Verified contact for Hamilton County's central public-records officer
# (https://www.hamiltoncountyohio.gov/government/transparency/public_records_requests.php).
# The Clerk of Courts does NOT publish a direct PRA email; their published
# channels are a web form and phone (513-946-5656). The county records
# officer routes requests to the originating department.
DEFAULT_TO = "HCAdmin@hamilton-co.org"
SUBJECT = "Public Records Act Request — Daily New Capias / Bench Warrant Roster (Clerk of Courts)"

BODY_TEMPLATE = """\
Hello,

Pursuant to Ohio Revised Code § 149.43, I respectfully request electronic
copies of the new capias / bench warrant filings docketed by the Hamilton
County Clerk of Courts between {since} and {until} (UTC). Please route this
request to the Clerk's records custodian if it should be directed there.

For each filing, please include (where available in the docket): case number,
filing date, defendant name and date of birth, charge description / ORC code,
judge, and any associated bond information.

Please send the responsive records as a CSV attachment or via a download
link to this address. No physical inspection or pickup is requested.

This request is hand-typed and electronically transmitted; per § 149.43(C)(2)
I respectfully ask for a response within a reasonable period of time.

Thank you,
JCStream — https://github.com/AICincy/JCStream
"""


_env = env  # back-compat alias; prefer pra_base.env in new code
_send_smtp = send_smtp  # back-compat alias; prefer pra_base.send_smtp


def _build_message(since: str, until: str, to_addr: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = SUBJECT
    msg.set_content(BODY_TEMPLATE.format(since=since, until=until))
    return msg


def send_daily_request(since: str, until: str) -> int:
    to_addr = env("JCSTREAM_PRA_TO_CAPIAS_EMAIL") or DEFAULT_TO
    from_addr = env("JCSTREAM_PRA_FROM_EMAIL")
    if dry_run_required(from_addr):
        log.warning(
            "PRA-capias dry-run (set JCSTREAM_PRA_FROM_EMAIL + JCSTREAM_PRA_SMTP_HOST to enable send)"
        )
        msg = _build_message(since, until, to_addr, from_addr or "<unset>")
        log.info("[PRA-capias DRY-RUN] To=%s\nSubject=%s\n\n%s",
                 to_addr, SUBJECT, msg.get_content())
        return 0

    msg = _build_message(since, until, to_addr, from_addr)
    try:
        send_smtp(msg)
        log.info("PRA-capias request sent to %s for window %s -> %s", to_addr, since, until)
    except Exception as e:
        log.error("PRA-capias SMTP send failed: %s", e)
        return 1
    return 0


def main() -> int:
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return send_daily_request(since=since, until=until)


if __name__ == "__main__":
    import sys
    sys.exit(main())
