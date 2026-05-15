"""Public Records Act email loop for HCSO booking photos.

Sibling of ``scraper.pra_capias`` (which handles daily new-capias requests).
This module is the fallback if HCSO ever stops embedding inline booking
photos on the inmate-detail page; right now JCStream extracts the photo
from the existing page, so this is a contingency only.

In **dry-run mode** (no SMTP secrets configured) we print the email and exit
cleanly so the workflow remains green.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from .pra_base import dry_run_required, env, send_smtp

log = logging.getLogger(__name__)

# Verified contact: Hamilton County's central public-records officer
# (https://www.hamiltoncountyohio.gov/government/transparency/public_records_requests.php).
# HCSO does NOT publish a direct PRA email; their channels are a web form
# (hcso.org/public-records-requests/) and phone (513-946-6400). HCAdmin will
# route the request to HCSO Media Relations.
DEFAULT_TO = "HCAdmin@hamilton-co.org"
SUBJECT = "Public Records Act Request — HCSO Booking Photos"

BODY_TEMPLATE = """\
Hello,

Pursuant to Ohio Revised Code § 149.43, I respectfully request electronic
copies of the booking photographs for all individuals booked into the
Hamilton County Justice Center between {since} and {until} (UTC).

Please send the responsive records as email attachments or via a download
link to this address. No physical inspection or pickup is requested.

This request is hand-typed and electronically transmitted; per § 149.43(C)(2)
I respectfully ask for a response within a reasonable period of time.

Thank you,
JCStream — https://github.com/AICincy/JCStream
"""


_env = env  # back-compat alias for any external caller; prefer pra_base.env


def _build_message(since: str, until: str, to_addr: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = SUBJECT
    msg.set_content(BODY_TEMPLATE.format(since=since, until=until))
    return msg


_send_smtp = send_smtp  # back-compat alias; prefer pra_base.send_smtp


def send_daily_request(since: str, until: str) -> int:
    to_addr = env("JCSTREAM_PRA_TO_PHOTOS_EMAIL") or DEFAULT_TO
    from_addr = env("JCSTREAM_PRA_FROM_EMAIL")
    if dry_run_required(from_addr):
        log.warning(
            "PRA-photos dry-run (set JCSTREAM_PRA_FROM_EMAIL + JCSTREAM_PRA_SMTP_HOST to enable send)"
        )
        msg = _build_message(since, until, to_addr, from_addr or "<unset>")
        log.info("[PRA-photos DRY-RUN] To=%s\nSubject=%s\n\n%s",
                 to_addr, SUBJECT, msg.get_content())
        return 0

    msg = _build_message(since, until, to_addr, from_addr)
    try:
        send_smtp(msg)
        log.info("PRA-photos request sent to %s for window %s -> %s", to_addr, since, until)
    except Exception as e:
        log.error("PRA-photos SMTP send failed: %s", e)
        return 1
    return 0


def main() -> int:
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
