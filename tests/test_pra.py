import pytest

from scraper import pra, pra_capias


def test_capias_default_recipient_is_verified_county_records_officer():
    assert pra_capias.DEFAULT_TO == "HCAdmin@hamilton-co.org"


def test_photos_default_recipient_is_verified_county_records_officer():
    assert pra.DEFAULT_TO == "HCAdmin@hamilton-co.org"


def test_capias_build_message_renders_template():
    msg = pra_capias._build_message(
        since="2026-05-10T00:00:00Z",
        until="2026-05-11T00:00:00Z",
        to_addr="HCAdmin@hamilton-co.org",
        from_addr="me@example.com",
    )
    assert msg["To"] == "HCAdmin@hamilton-co.org"
    assert msg["From"] == "me@example.com"
    body = msg.get_content()
    assert "2026-05-10T00:00:00Z" in body
    assert "2026-05-11T00:00:00Z" in body
    assert "149.43" in body
    assert "capias" in body.lower()


def test_photos_build_message_renders_template():
    msg = pra._build_message(
        since="2026-05-10T00:00:00Z",
        until="2026-05-11T00:00:00Z",
        to_addr="MediaRelations@hcso.org",
        from_addr="me@example.com",
    )
    body = msg.get_content()
    assert "booking photograph" in body.lower()
    assert "Hamilton County" in body


def test_dry_run_returns_zero_without_smtp_env(monkeypatch):
    for var in (
        "JCSTREAM_PRA_SMTP_HOST",
        "JCSTREAM_PRA_FROM_EMAIL",
        "JCSTREAM_PRA_SMTP_USER",
        "JCSTREAM_PRA_SMTP_PASS",
    ):
        monkeypatch.delenv(var, raising=False)
    assert pra_capias.send_daily_request("a", "b") == 0
    assert pra.send_daily_request("a", "b") == 0


def test_build_message_rejects_crlf_in_recipient_header():
    # tests-F6: CR/LF in a header value (To/From) must be rejected by
    # EmailMessage at set-time. This pins that defense so a future refactor
    # away from EmailMessage (e.g. raw sendmail with f-strings) can't
    # silently re-introduce header-splitting risk. Body fields are not at
    # risk - they're interpolated into the body via .format(), not a header.
    with pytest.raises(ValueError):
        pra._build_message(
            since="2026-05-10T00:00:00Z",
            until="2026-05-11T00:00:00Z",
            to_addr="HCAdmin@hamilton-co.org\r\nBcc: leak@example.test",
            from_addr="me@example.com",
        )
    with pytest.raises(ValueError):
        pra_capias._build_message(
            since="2026-05-10T00:00:00Z",
            until="2026-05-11T00:00:00Z",
            to_addr="HCAdmin@hamilton-co.org",
            from_addr="me@example.com\r\nBcc: leak@example.test",
        )


def test_safe_port_parsing_invalid_or_missing(monkeypatch):
    from scraper import pra_base

    monkeypatch.setenv("JCSTREAM_PRA_SMTP_HOST", "localhost")
    monkeypatch.setenv("JCSTREAM_PRA_SMTP_PORT", "not-a-number")
    captured_port = None

    class MockSMTP:
        def __init__(self, host, port, timeout=None):
            nonlocal captured_port
            captured_port = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, context=None):
            pass

        def send_message(self, msg):
            pass

    monkeypatch.setattr(pra_base.smtplib, "SMTP", MockSMTP)
    from email.message import EmailMessage

    msg = EmailMessage()
    pra_base.send_smtp(msg)
    assert captured_port == 587
