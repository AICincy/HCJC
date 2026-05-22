"""Tests for the offline logic in tools/verify_ingest.py.

The Datadog search is network-only and not covered here; the event-name
extraction, the required/canonical-set reporting, and the env/arg handling are.
"""
from __future__ import annotations

import httpx

import tools.verify_ingest as vi


def _event(name: str) -> dict:
    return {"attributes": {"attributes": {"event": name}, "timestamp": "2026-05-22T00:00:00Z"}}


def test_event_name_reads_nested_then_flat_then_none():
    assert vi._event_name(_event("sweep_start")) == "sweep_start"
    assert vi._event_name({"attributes": {"event": "waf_block"}}) == "waf_block"
    assert vi._event_name({"attributes": {}}) is None
    assert vi._event_name({}) is None


def test_report_flags_missing_required_event(capsys):
    vi._report([_event("sweep_start")])  # sweep_complete absent
    out = capsys.readouterr().out
    assert "missing required events" in out
    assert "sweep_complete" in out


def test_report_silent_when_required_present(capsys):
    vi._report([_event("sweep_start"), _event("sweep_complete"), _event("waf_block")])
    out = capsys.readouterr().out
    assert "missing required events" not in out
    assert "waf_block" in out  # canonical conditional event is surfaced


def test_main_returns_2_without_keys(monkeypatch, capsys):
    monkeypatch.delenv("DD_API_KEY", raising=False)
    monkeypatch.delenv("DD_APP_KEY", raising=False)
    assert vi.main([]) == 2
    assert "Need DD_API_KEY and DD_APP_KEY" in capsys.readouterr().err


def test_main_returns_1_when_no_events(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")
    monkeypatch.setenv("DD_APP_KEY", "a")
    monkeypatch.setattr(vi, "_search", lambda *a, **k: [])
    assert vi.main([]) == 1


def test_main_returns_0_when_events_found(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "k")
    monkeypatch.setenv("DD_APP_KEY", "a")
    monkeypatch.setattr(vi, "_search", lambda *a, **k: [_event("sweep_start")])
    assert vi.main([]) == 0


def test_search_returns_none_on_transport_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(vi.httpx, "post", boom)
    assert vi._search("k", "a", "datadoghq.com", "service:jcstream", "now-1h") is None


def test_search_passes_query_and_window(monkeypatch):
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [_event("sweep_complete")]}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(vi.httpx, "post", fake_post)
    out = vi._search("k", "a", "us5.datadoghq.com", "service:jcstream event:waf_block", "now-6h")
    assert out and vi._event_name(out[0]) == "sweep_complete"
    assert captured["json"]["filter"]["query"] == "service:jcstream event:waf_block"
    assert captured["json"]["filter"]["from"] == "now-6h"
