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
    verify_block_chain,
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


def test_save_current_drops_sealed_inmate_numbers(tmp_path: Path):
    # ORC 2953.32: a sealed inmate_number listed in data/takedowns.json must
    # not persist into current.json at the write boundary (not only the render).
    (tmp_path / "takedowns.json").write_text(json.dumps(["2"]), encoding="utf-8")
    path = tmp_path / "current.json"
    save_current(path, [_inm("1"), _inm("2", last="ROE")])
    loaded = load_current(path)
    assert set(loaded.keys()) == {"1"}
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["inmate_count"] == 1


def test_save_changelog_drops_sealed_events(tmp_path: Path):
    # ORC 2953.32: events referencing a sealed inmate_number must be dropped
    # from the rolling changelog on save.
    from scraper.models import ChangeEvent
    from scraper.store import save_changelog

    (tmp_path / "takedowns.json").write_text(json.dumps(["2"]), encoding="utf-8")
    path = tmp_path / "changelog.json"
    save_changelog(
        path,
        [
            ChangeEvent(event="booked", inmate_number="1", name="A", timestamp_utc="2026-05-14T01:00:00Z"),
            ChangeEvent(event="released", inmate_number="2", name="B", timestamp_utc="2026-05-14T02:00:00Z"),
        ],
    )
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert [r["inmate_number"] for r in rows] == ["1"]


def test_save_current_fails_closed_on_malformed_takedowns(tmp_path: Path):
    # ORC 2953.32: a takedowns.json that exists but cannot be parsed must abort
    # the write (fail closed), not silently proceed with an empty seal set and
    # republish sealed records for the cycle.
    import pytest

    from scraper.store import SnapshotCorruptError

    (tmp_path / "takedowns.json").write_text("{not json", encoding="utf-8")
    path = tmp_path / "current.json"
    with pytest.raises(SnapshotCorruptError):
        save_current(path, [_inm("1")])
    assert not path.exists()


def test_save_changelog_fails_closed_on_malformed_takedowns(tmp_path: Path):
    import pytest

    from scraper.models import ChangeEvent
    from scraper.store import SnapshotCorruptError, save_changelog

    (tmp_path / "takedowns.json").write_text("[1,", encoding="utf-8")
    path = tmp_path / "changelog.json"
    with pytest.raises(SnapshotCorruptError):
        save_changelog(
            path,
            [ChangeEvent(event="booked", inmate_number="1", name="A", timestamp_utc="2026-05-14T01:00:00Z")],
        )
    assert not path.exists()


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
    ev = ChangeEvent(event="booked", inmate_number="42", name="DOE, JOHN", timestamp_utc=now)
    path = tmp_path / "anon_changelog.json"
    enr = {"42": {"tier": "F1", "category": "violent"}}

    save_anon_changelog(path, [ev], enrichment=enr)
    first = json.loads(path.read_text(encoding="utf-8"))
    save_anon_changelog(path, [ev], enrichment=enr)
    second = json.loads(path.read_text(encoding="utf-8"))

    assert len(first) == 1
    assert len(second) == 1  # not duplicated on the second sweep


def test_anon_changelog_no_double_count_at_expiry_boundary(tmp_path: Path):
    # Regression: when an event crosses the ANON_EXPIRY_DAYS boundary, the
    # prior write left a FULL row on disk (keyed by inmate + timestamp) while
    # this write re-emits the same event from the full changelog, now expired,
    # keyed by day + tier + category. seen_keys held only the full key, so the
    # anonymized twin was appended; the re-anonymization pass then rewrote the
    # carried-over full row to the same anon shape, leaving TWO rows for one
    # event until 365-day compaction. The post-re-anon re-dedup collapses them.
    import json
    from datetime import datetime, timedelta, timezone

    from scraper.models import ChangeEvent
    from scraper.store import save_anon_changelog

    # Older than ANON_EXPIRY_DAYS (7): expired at this write.
    old = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = tmp_path / "anon_changelog.json"

    # Simulate the prior write's output: the event stored as a FULL (recent) row.
    path.write_text(
        json.dumps(
            [
                {
                    "event": "booked",
                    "timestamp_utc": old,
                    "inmate_number": "42",
                    "name": "DOE, JOHN",
                    "tier": "F1",
                    "category": "violent",
                }
            ]
        ),
        encoding="utf-8",
    )

    # This write re-emits the same event (now expired) from the full changelog.
    ev = ChangeEvent(event="booked", inmate_number="42", name="DOE, JOHN", timestamp_utc=old)
    save_anon_changelog(path, [ev], enrichment={"42": {"tier": "F1", "category": "violent"}})

    out = json.loads(path.read_text(encoding="utf-8"))
    assert len(out) == 1  # collapsed, not double-counted
    assert out[0].get("inmate_number") is None  # anonymized (PII stripped)
    assert out[0]["event"] == "booked"


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


def test_verify_block_chain_detects_intact_and_tampered(tmp_path: Path):
    p = tmp_path / "waf_block_log.json"
    append_block_evidence({"event": "blocked", "seen_count": 0}, p)
    append_block_evidence({"event": "recovered", "seen_count": 5}, p)
    entries = load_block_log(p)
    assert verify_block_chain(entries) == []  # intact straight off disk
    # Edit the first record in place: the link from record 1 to it breaks.
    entries[0]["seen_count"] = 999
    problems = verify_block_chain(entries)
    assert len(problems) == 1
    assert problems[0].startswith("record 1")


def test_verify_block_log_cli(tmp_path: Path, capsys):
    from scraper import verify_block_log

    p = tmp_path / "waf_block_log.json"
    append_block_evidence({"event": "blocked"}, p)
    rc = verify_block_log.main([str(p)])
    assert rc == 0
    assert "intact" in capsys.readouterr().out


def test_compact_anon_entries_is_idempotent():
    from datetime import datetime, timedelta, timezone

    from scraper.store import _compact_anon_entries

    old_day = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
    recent_day = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")

    entries = [
        {"event": "booked", "date": old_day, "tier": "F5", "category": "theft"},
        {"event": "booked", "date": old_day, "tier": "F5", "category": "theft"},
        {"event": "released", "date": recent_day, "tier": "M1", "category": "traffic"},
    ]

    first = _compact_anon_entries(entries)
    second = _compact_anon_entries(first)

    assert first == second, "compaction must be idempotent"
    assert any(r.get("event_summary") and r.get("count") == 2 for r in first)
    assert any(r.get("event") == "released" and not r.get("event_summary") for r in first)


def test_compact_anon_entries_merges_existing_summaries():
    from scraper.store import _compact_anon_entries

    entries = [
        {"event_summary": True, "month": "2024-01", "event": "booked", "tier": "F5", "category": "theft", "count": 5},
        {"event_summary": True, "month": "2024-01", "event": "booked", "tier": "F5", "category": "theft", "count": 3},
    ]
    out = _compact_anon_entries(entries)
    summaries = [r for r in out if r.get("event_summary")]
    assert len(summaries) == 1
    assert summaries[0]["count"] == 8


def test_anon_changelog_anonymizes_sealed_inmates(tmp_path: Path):
    # ORC 2953.32: a sealed inmate_number must not keep name/number in the
    # anon changelog, either for incoming events or rows already on disk.
    from datetime import datetime, timezone

    from scraper.models import ChangeEvent
    from scraper.store import save_anon_changelog

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ev = ChangeEvent(event="booked", inmate_number="7", name="ROE, JANE", timestamp_utc=now)
    path = tmp_path / "anon_changelog.json"
    enr = {"7": {"tier": "M1", "category": "other"}}

    # First write: not sealed; PII row lands on disk.
    save_anon_changelog(path, [ev], enrichment=enr)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert rows[0]["inmate_number"] == "7"

    # Takedown added afterwards: next write must retro-purge the on-disk row.
    (tmp_path / "takedowns.json").write_text(json.dumps(["7"]), encoding="utf-8")
    save_anon_changelog(path, [], enrichment=enr)
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        assert row.get("inmate_number") != "7"
        assert "ROE" not in json.dumps(row)

    # And a fresh sealed event never lands with PII in the first place.
    ev2 = ChangeEvent(event="released", inmate_number="7", name="ROE, JANE", timestamp_utc=now)
    save_anon_changelog(path, [ev2], enrichment=enr)
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        assert row.get("inmate_number") != "7"
        assert "ROE" not in json.dumps(row)
