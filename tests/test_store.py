import json
from pathlib import Path

import pytest

from scraper.models import Charge, Inmate
from scraper.store import (
    SnapshotCorruptError,
    _record_sha256,
    append_block_evidence,
    diff,
    load_block_log,
    load_changelog,
    load_current,
    load_current_or_raise,
    save_current,
)


def _inm(num: str, charges=None, last="DOE", first="JOHN") -> Inmate:
    return Inmate(
        inmate_number=num,
        last_name=last,
        first_name=first,
        booking_date="5/10/26",
        charges=charges or [],
    )


def test_diff_detects_booked_released_and_updated():
    previous = {
        "1": _inm("1"),
        "2": _inm("2", last="SMITH"),
    }
    current = {
        "1": _inm("1", charges=[Charge(orc_code="2903.02", description="MURDER")]),
        "3": _inm("3", last="ROE"),
    }
    events = {(e.event, e.inmate_number) for e in diff(previous, current)}
    assert ("updated", "1") in events
    assert ("released", "2") in events
    assert ("booked", "3") in events


def test_diff_emits_no_event_for_unchanged_record():
    same = _inm("1")
    events = diff({"1": same}, {"1": _inm("1")})
    assert events == []


def test_diff_ignores_charge_reorder_with_same_content():
    # data-F3: HCSO occasionally reshuffles the same charges in a different
    # display order. _materially_changed must compare by canonical content,
    # not by document order, so the reshuffle does not flood the changelog
    # with spurious `updated` events.
    c1 = Charge(orc_code="2903.02", description="MURDER")
    c2 = Charge(orc_code="2911.01", description="AGGRAVATED ROBBERY")
    prev = {"1": _inm("1", charges=[c1, c2])}
    curr = {"1": _inm("1", charges=[c2, c1])}
    assert diff(prev, curr) == []


def test_save_changelog_sorts_by_timestamp_with_stable_tiebreak(tmp_path: Path):
    # data-F6: changelog must be persisted sorted by timestamp_utc so an NTP
    # slew or container restart doesn't leave the rolling feed out of order.
    # Insertion order is the tiebreaker for events sharing a timestamp.
    import json

    from scraper.models import ChangeEvent
    from scraper.store import save_changelog

    path = tmp_path / "changelog.json"
    save_changelog(
        path,
        [
            ChangeEvent(event="booked", inmate_number="3", name="C", timestamp_utc="2026-05-14T03:00:00Z"),
            ChangeEvent(event="booked", inmate_number="1", name="A", timestamp_utc="2026-05-14T01:00:00Z"),
            ChangeEvent(event="updated", inmate_number="2a", name="Ba", timestamp_utc="2026-05-14T02:00:00Z"),
            ChangeEvent(event="updated", inmate_number="2b", name="Bb", timestamp_utc="2026-05-14T02:00:00Z"),
        ],
    )
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert [(e["timestamp_utc"], e["inmate_number"]) for e in on_disk] == [
        ("2026-05-14T01:00:00Z", "1"),
        ("2026-05-14T02:00:00Z", "2a"),  # insertion-order tiebreak
        ("2026-05-14T02:00:00Z", "2b"),
        ("2026-05-14T03:00:00Z", "3"),
    ]


def test_load_current_returns_empty_on_corrupt_json(tmp_path: Path, caplog):
    bad = tmp_path / "current.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_current(bad) == {}
    assert any("could not deserialize" in r.message for r in caplog.records)


def test_load_current_returns_empty_when_json_is_not_a_dict(tmp_path: Path):
    # `null`, a bare list, or a primitive would all make `raw.get("inmates", ...)`
    # raise AttributeError. Each path must fall back to empty.
    for payload in ("null", "[]", '"oops"', "42"):
        bad = tmp_path / "current.json"
        bad.write_text(payload, encoding="utf-8")
        assert load_current(bad) == {}, payload


def test_load_current_returns_empty_on_schema_mismatch(tmp_path: Path):
    bad = tmp_path / "current.json"
    # Missing required inmate_number; pydantic should reject and we swallow.
    bad.write_text('{"inmates": [{"last_name": "DOE"}]}', encoding="utf-8")
    assert load_current(bad) == {}


def test_load_changelog_returns_empty_on_corrupt_json(tmp_path: Path):
    bad = tmp_path / "changelog.json"
    bad.write_text("[corrupt", encoding="utf-8")
    assert load_changelog(bad) == []


def test_save_current_writes_atomically_and_round_trips(tmp_path: Path):
    path = tmp_path / "current.json"
    save_current(path, [_inm("1"), _inm("2", last="ROE")])
    # No leftover tmp file.
    assert not (tmp_path / "current.json.tmp").exists()
    loaded = load_current(path)
    assert set(loaded.keys()) == {"1", "2"}
    assert loaded["2"].last_name == "ROE"


def test_save_current_writes_schema_version(tmp_path: Path):
    # data-F1: every snapshot we write should carry schema_version so a
    # future reader can detect a too-new file.
    import json
    path = tmp_path / "current.json"
    save_current(path, [_inm("1")])
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1


def test_load_current_or_raise_returns_empty_when_missing(tmp_path: Path):
    # File genuinely absent is the only path that bootstraps a roster.
    assert load_current_or_raise(tmp_path / "nope.json") == {}


def test_load_current_or_raise_raises_on_corrupt_json(tmp_path: Path):
    # File exists but is unreadable; the sweep must NOT canonicalize.
    bad = tmp_path / "current.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SnapshotCorruptError):
        load_current_or_raise(bad)


def test_load_current_or_raise_raises_on_schema_mismatch(tmp_path: Path):
    bad = tmp_path / "current.json"
    bad.write_text('{"inmates": [{"last_name": "DOE"}]}', encoding="utf-8")
    with pytest.raises(SnapshotCorruptError):
        load_current_or_raise(bad)


def test_load_current_or_raise_rejects_future_schema_version(tmp_path: Path):
    # A future migration could ship a version-2 file. Today's reader must
    # refuse rather than silently drop fields and write back as v1.
    bad = tmp_path / "current.json"
    bad.write_text(
        '{"schema_version": 99, "generated_utc": "", "inmate_count": 0, "inmates": []}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotCorruptError, match="schema_version"):
        load_current_or_raise(bad)


def test_load_current_forgiving_still_returns_empty_on_corrupt(tmp_path: Path, caplog):
    # web/build.py and other lossy callers still get {} back when the file
    # is unreadable; only the strict variant raises.
    bad = tmp_path / "current.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_current(bad) == {}
    assert any("could not deserialize" in r.message for r in caplog.records)


def test_anon_changelog_dedupes_recent_rows_across_sweeps(tmp_path: Path):
    # Regression: recent (non-anonymized) rows were keyed with a 3-tuple that
    # never matched the 5-tuple seen_keys built from existing rows, so every
    # sweep re-appended the same recent event. A second identical sweep must
    # not grow the file.
    from datetime import datetime, timezone

    from scraper.models import ChangeEvent
    from scraper.store import save_anon_changelog

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ev = ChangeEvent(event="booked", inmate_number="42", name="DOE, JOHN",
                     timestamp_utc=now)
    path = tmp_path / "anon_changelog.json"
    enr = {"42": {"tier": "F1", "category": "violent"}}

    save_anon_changelog(path, [ev], enrichment=enr)
    first = json.loads(path.read_text(encoding="utf-8"))
    save_anon_changelog(path, [ev], enrichment=enr)
    second = json.loads(path.read_text(encoding="utf-8"))

    assert len(first) == 1
    assert len(second) == 1  # not duplicated on the second sweep


def test_block_log_round_trips(tmp_path: Path):
    p = tmp_path / "waf_block_log.json"
    assert load_block_log(p) == []  # missing file -> empty
    append_block_evidence({"event": "blocked", "surnames_failed": 24}, p)
    append_block_evidence({"event": "recovered"}, p)
    log = load_block_log(p)
    assert [r["event"] for r in log] == ["blocked", "recovered"]


def test_load_block_log_tolerates_corrupt(tmp_path: Path):
    p = tmp_path / "waf_block_log.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_block_log(p) == []
    # A valid-JSON-but-not-a-list payload also degrades to [].
    p.write_text('{"event": "blocked"}', encoding="utf-8")
    assert load_block_log(p) == []
    # append_block_evidence recovers by starting a fresh list.
    append_block_evidence({"event": "blocked"}, p)
    assert load_block_log(p) == [{"event": "blocked", "prev_sha256": None}]


def test_block_log_hash_chains(tmp_path: Path):
    p = tmp_path / "waf_block_log.json"
    append_block_evidence({"event": "blocked", "seen_count": 0}, p)
    append_block_evidence({"event": "recovered", "seen_count": 1200}, p)
    log = load_block_log(p)
    assert log[0]["prev_sha256"] is None
    assert log[1]["prev_sha256"] == _record_sha256(log[0])
