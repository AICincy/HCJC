"""Round-trip + error-path coverage for the Cincinnati Open Data loaders.

All four feeds (cfs, cfs_pdi, incidents, shootings) share the same persistence
shape: ``{generated_utc, dataset_id, row_count, rows}`` (cfs omits dataset_id).
The ``query()`` shim in cincy_open is the only thing that touches the network;
these tests stub it out so the suite never makes a real request.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import httpx

from scraper import cfs, cfs_pdi, incidents, shootings


def _socrata_400() -> httpx.HTTPStatusError:
    """Simulate Socrata rejecting a $where with a 'column not found' error.
    This is what surfaces on a renamed-or-missing column in a real query."""
    req = httpx.Request("GET", "https://data.cincinnati-oh.gov/resource/x.json")
    resp = httpx.Response(400, request=req, text="column not found")
    return httpx.HTTPStatusError("Socrata 400", request=req, response=resp)


# ----- load() returns [] when file is missing -----------------------------

@pytest.mark.parametrize("mod,attr", [
    (cfs, "load_recent"),
    (cfs_pdi, "load"),
    (incidents, "load"),
    (shootings, "load"),
])
def test_loader_returns_empty_when_file_missing(mod, attr, tmp_path: Path):
    assert getattr(mod, attr)(tmp_path / "nope.json") == []


# ----- save -> load round trip -------------------------------------------

@pytest.mark.parametrize("mod,save_name,load_name", [
    (cfs, "save_recent", "load_recent"),
    (cfs_pdi, "save", "load"),
    (incidents, "save", "load"),
    (shootings, "save", "load"),
])
def test_save_load_round_trip(mod, save_name, load_name, tmp_path: Path):
    path = tmp_path / "feed.json"
    rows = [{"id": "1", "x": "a"}, {"id": "2", "x": "b"}]
    getattr(mod, save_name)(rows, path)
    assert getattr(mod, load_name)(path) == rows
    # Persisted shape must keep generated_utc + row_count alongside rows.
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["row_count"] == 2
    assert "generated_utc" in payload


# ----- pull_recent uses the configured Socrata dataset --------------------

def test_cfs_pull_recent_filters_dispositions(monkeypatch):
    # cfs now routes through cincy_open.query like the other three feeds,
    # so the network seam lives in cincy_open. Patch it and assert that the
    # disposition $where clause is still present.
    captured = {}

    def fake_query(dataset_id, **kw):
        captured["dataset_id"] = dataset_id
        captured["where"] = kw.get("where", "")
        captured["limit"] = kw.get("limit")
        return [{"ok": True}]

    monkeypatch.setattr(cfs, "query", fake_query)
    rows = cfs.pull_recent(hours=24, limit=10)
    assert rows == [{"ok": True}]
    assert captured["dataset_id"] == "qiik-bpks"
    assert "disposition_text" in captured["where"]
    assert captured["limit"] == 10


def test_cfs_pdi_pull_uses_dataset_id(monkeypatch):
    seen = {}

    def fake_query(dataset_id, **kw):
        seen["dataset_id"] = dataset_id
        return [{"row": 1}]

    monkeypatch.setattr(cfs_pdi, "query", fake_query)
    assert cfs_pdi.pull_recent(hours=24, limit=5) == [{"row": 1}]
    assert seen["dataset_id"] == "gexm-h6bt"


def test_incidents_pull_falls_back_when_first_filter_fails(monkeypatch):
    calls = []

    def fake_query(dataset_id, **kw):
        where = kw.get("where")
        calls.append(where)
        if where and where.startswith("date_reported"):
            # Simulate Socrata's "column not found" 400 - the only failure
            # shape the filter-candidate loop should be tolerant of.
            raise _socrata_400()
        return [{"row": 1}]

    monkeypatch.setattr(incidents, "query", fake_query)
    rows = incidents.pull_recent(days=1, limit=5)
    assert rows == [{"row": 1}]
    # First (canonical) filter tried, then the second succeeded.
    assert len(calls) >= 2
    assert calls[0].startswith("date_reported")
    assert calls[1].startswith("date_from")


def test_shootings_pull_returns_unfiltered_when_all_filters_fail(monkeypatch):
    calls = []

    def fake_query(dataset_id, **kw):
        calls.append(kw.get("where"))
        if kw.get("where") is not None:
            raise _socrata_400()
        return [{"fallback": True}]

    monkeypatch.setattr(shootings, "query", fake_query)
    rows = shootings.pull_recent(days=1, limit=5)
    assert rows == [{"fallback": True}]
    # Tried both candidate filters, then the unfiltered fallback.
    assert calls[-1] is None


def test_incidents_pull_propagates_transport_errors(monkeypatch):
    # sec-net-F4: a real transport error (e.g. ConnectError) must NOT be
    # silently swallowed and rolled into the unfiltered fallback. The
    # operator wants to see an outage, not stale data.
    def fake_query(dataset_id, **kw):
        raise httpx.ConnectError("dns failed")

    monkeypatch.setattr(incidents, "query", fake_query)
    with pytest.raises(httpx.ConnectError):
        incidents.pull_recent(days=1, limit=5)


def test_shootings_pull_propagates_transport_errors(monkeypatch):
    def fake_query(dataset_id, **kw):
        raise httpx.ConnectError("dns failed")

    monkeypatch.setattr(shootings, "query", fake_query)
    with pytest.raises(httpx.ConnectError):
        shootings.pull_recent(days=1, limit=5)
