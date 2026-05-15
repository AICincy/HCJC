"""PRA send-path tests with smtplib mocked.

The dry-run path (no env) is already covered in test_pra.py. These exercise
what happens when ``JCSTREAM_PRA_SMTP_HOST`` + ``JCSTREAM_PRA_FROM_EMAIL``
are set, without actually opening a socket.
"""
from __future__ import annotations

import smtplib

import pytest

from scraper import pra, pra_capias


@pytest.fixture
def smtp_recorder(monkeypatch):
    """Yield a list that collects every fake-SMTP instance the test produces.

    Avoids class-level state on the fake — each test gets its own registry,
    so test order and parallel execution can never bleed instances across.
    """
    captured: list = []

    class _FakeSMTP:
        """Behaves like ``smtplib.SMTP`` / ``SMTP_SSL`` for our send paths."""

        def __init__(self, host, port, timeout=None, context=None):
            self.host = host
            self.port = port
            self.logged_in = False
            self.starttls_called = False
            self.sent: list = []
            captured.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context=None):
            self.starttls_called = True

        def login(self, user, password):
            self.logged_in = True
            self.user = user

        def send_message(self, msg):
            self.sent.append(msg)

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTP)
    return captured


def _set_smtp_env(monkeypatch, *, port="587", with_auth=True):
    monkeypatch.setenv("JCSTREAM_PRA_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("JCSTREAM_PRA_SMTP_PORT", port)
    monkeypatch.setenv("JCSTREAM_PRA_FROM_EMAIL", "me@example.com")
    if with_auth:
        monkeypatch.setenv("JCSTREAM_PRA_SMTP_USER", "user@example.com")
        monkeypatch.setenv("JCSTREAM_PRA_SMTP_PASS", "shh")
    else:
        monkeypatch.delenv("JCSTREAM_PRA_SMTP_USER", raising=False)
        monkeypatch.delenv("JCSTREAM_PRA_SMTP_PASS", raising=False)


def test_capias_send_starttls_path(monkeypatch, smtp_recorder):
    _set_smtp_env(monkeypatch, port="587")
    rc = pra_capias.send_daily_request("2026-05-10T00:00:00Z", "2026-05-11T00:00:00Z")
    assert rc == 0
    assert len(smtp_recorder) == 1
    inst = smtp_recorder[0]
    assert inst.starttls_called
    assert inst.logged_in
    assert len(inst.sent) == 1
    assert "capias" in inst.sent[0].get_content().lower()


def test_capias_send_skips_login_when_credentials_missing(monkeypatch, smtp_recorder):
    _set_smtp_env(monkeypatch, port="587", with_auth=False)
    rc = pra_capias.send_daily_request("a", "b")
    assert rc == 0
    inst = smtp_recorder[0]
    assert inst.starttls_called
    assert not inst.logged_in
    assert len(inst.sent) == 1


def test_capias_send_returns_one_on_smtp_failure(monkeypatch):
    _set_smtp_env(monkeypatch)

    class _Boom:
        def __init__(self, *a, **kw): raise OSError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP", _Boom)
    assert pra_capias.send_daily_request("a", "b") == 1


def test_photos_send_starttls_path(monkeypatch, smtp_recorder):
    _set_smtp_env(monkeypatch, port="587")
    rc = pra.send_daily_request("2026-05-10T00:00:00Z", "2026-05-11T00:00:00Z")
    assert rc == 0
    msg = smtp_recorder[0].sent[0]
    assert "booking photograph" in msg.get_content().lower()


def test_photos_send_implicit_tls_path(monkeypatch, smtp_recorder):
    _set_smtp_env(monkeypatch, port="465")
    rc = pra.send_daily_request("a", "b")
    assert rc == 0
    inst = smtp_recorder[0]
    assert inst.port == 465
    # SMTP_SSL path: no STARTTLS handshake.
    assert not inst.starttls_called
    assert inst.logged_in
