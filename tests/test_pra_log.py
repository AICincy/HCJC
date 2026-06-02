"""Tests for scraper.pra_log: hash chain, response tracking, verification."""

from __future__ import annotations

import json
from pathlib import Path

from scraper.pra_log import (
    append_pra_record,
    load_pra_log,
    make_pra_record,
    record_response,
    verify_pra_chain,
)


def test_append_creates_chain(tmp_path: Path):
    log_path = tmp_path / "pra.json"
    r1 = make_pra_record(
        module="photos",
        to="a@b.com",
        subject="S",
        window_since="a",
        window_until="b",
        status="sent",
    )
    append_pra_record(r1, path=log_path)

    r2 = make_pra_record(
        module="capias",
        to="c@d.com",
        subject="S2",
        window_since="c",
        window_until="d",
        status="dry_run",
    )
    append_pra_record(r2, path=log_path)

    entries = load_pra_log(log_path)
    assert len(entries) == 2
    assert entries[0]["prev_sha256"] is None
    assert entries[1]["prev_sha256"] is not None


def test_verify_intact_chain(tmp_path: Path):
    log_path = tmp_path / "pra.json"
    for _ in range(3):
        r = make_pra_record(
            module="photos",
            to="a@b.com",
            subject="S",
            window_since="a",
            window_until="b",
            status="sent",
        )
        append_pra_record(r, path=log_path)
    entries = load_pra_log(log_path)
    assert verify_pra_chain(entries) == []


def test_verify_broken_chain(tmp_path: Path):
    log_path = tmp_path / "pra.json"
    for _ in range(3):
        r = make_pra_record(
            module="photos",
            to="a@b.com",
            subject="S",
            window_since="a",
            window_until="b",
            status="sent",
        )
        append_pra_record(r, path=log_path)

    entries = load_pra_log(log_path)
    entries[1]["prev_sha256"] = "tampered"
    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    reloaded = load_pra_log(log_path)
    problems = verify_pra_chain(reloaded)
    assert len(problems) >= 1
    assert "tampered" in problems[0]


def test_record_response(tmp_path: Path):
    log_path = tmp_path / "pra.json"
    r = make_pra_record(
        module="photos",
        to="a@b.com",
        subject="S",
        window_since="a",
        window_until="b",
        status="sent",
    )
    append_pra_record(r, path=log_path)
    rid = load_pra_log(log_path)[0]["request_id"]

    ok = record_response(rid, "Email reply received with 5 photos", path=log_path)
    assert ok is True

    entries = load_pra_log(log_path)
    assert entries[0]["response_received_utc"] is not None
    assert "5 photos" in entries[0]["response_notes"]


def test_record_response_not_found(tmp_path: Path):
    log_path = tmp_path / "pra.json"
    ok = record_response("nonexistent", "notes", path=log_path)
    assert ok is False


def test_empty_log_verifies(tmp_path: Path):
    assert verify_pra_chain([]) == []


def test_load_missing_file(tmp_path: Path):
    assert load_pra_log(tmp_path / "does_not_exist.json") == []
