"""Shared SMTP transport for the three PRA (Public Records Act) request modules.

``scraper.pra`` (booking photos) and ``scraper.pra_capias`` (daily new-capias)
each compose a different subject + body template but rely on the same SMTP
envelope. This module is the single home for that transport plus the env-var
helpers each module uses.

The SMTP path is the security-load-bearing line in the codebase: anything
that touches credentials or the From/To header should land here so there is
one place to review when the credential handling changes.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger(__name__)


def env(name: str) -> str:
    """Read an env var, stripped. Empty string when unset (never None)."""
    return os.environ.get(name, "").strip()


def send_smtp(msg: EmailMessage) -> None:
    """Send ``msg`` over SMTP using JCSTREAM_PRA_SMTP_* env vars.

    Port 465 uses implicit TLS (``SMTP_SSL``); any other port uses STARTTLS.
    Credentials are optional: a missing user/pass pair sends without login,
    suitable for an internal relay that authorizes by source IP. Both
    transports use ``ssl.create_default_context`` and a 30-second timeout.

    Raises ``RuntimeError`` when JCSTREAM_PRA_SMTP_HOST is not set; raises
    any underlying smtplib exception on transport failure.
    """
    host = env("JCSTREAM_PRA_SMTP_HOST")
    port = int(env("JCSTREAM_PRA_SMTP_PORT") or "587")
    user = env("JCSTREAM_PRA_SMTP_USER")
    password = env("JCSTREAM_PRA_SMTP_PASS")
    if not host:
        raise RuntimeError("JCSTREAM_PRA_SMTP_HOST is not set")
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            if user and password:
                s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            if user and password:
                s.login(user, password)
            s.send_message(msg)


def dry_run_required(from_addr: str) -> bool:
    """Return True when the SMTP path is not fully configured.

    Callers should fall through to dry-run logging (print the email instead of
    sending) so the GitHub Actions workflow remains green pre-config.
    """
    return not from_addr or not env("JCSTREAM_PRA_SMTP_HOST")
