import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.models import Charge, Inmate, Snapshot
from scripts import backfill_anon_changelog as backfill_mod


def _now_iso(delta: timedelta = timedelta()) -> str:
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def _inmate(number: str, code: str = "2913.02", first: str = "JANE") -> Inmate:
    return Inmate(
        inmate_number=number,
        last_name="DOE",
        first_name=first,
        booking_date="9/24/26",
        charges=[Charge(orc_code=code)],
    )


def test_best_historical_record_prefers_event_side_of_timestamp():
    event_time = _now_iso()
    before = _inmate("100", first="BEFORE")
    after = _inmate("100", first="AFTER")
    snapshots = [
        backfill_mod.HistoricalSnapshot(
            datetime.now(timezone.utc) - timedelta(hours=1),
            {"100": before},
        ),
        backfill_mod.HistoricalSnapshot(
            datetime.now(timezone.utc) + timedelta(hours=1),
            {"100": after},
        ),
    ]

    released = backfill_mod._best_historical_record(
        snapshots,
        {"event": "released", "inmate_number": "100", "timestamp_utc": event_time},
    )
    booked = backfill_mod._best_historical_record(
        snapshots,
        {"event": "booked", "inmate_number": "100", "timestamp_utc": event_time},
    )

    assert released is before
    assert booked is after



def test_best_recovery_record_prefers_live_roster_for_non_release():
    event_time = _now_iso()
    historical = _inmate("108", first="HISTORY")
    live = _inmate("108", first="LIVE")
    snapshots = [
        backfill_mod.HistoricalSnapshot(
            datetime.now(timezone.utc) - timedelta(minutes=10),
            {"108": historical},
        )
    ]
    current = backfill_mod.HistoricalSnapshot(
        datetime.now(timezone.utc),
        {"108": live},
    )

    record, source = backfill_mod._best_recovery_record(
        snapshots,
        current,
        {"event": "booked", "inmate_number": "108", "timestamp_utc": event_time},
    )

    assert record is live
    assert source == "live"


def test_best_recovery_record_requires_history_for_release():
    released = _inmate("109", first="RELEASED")
    current = backfill_mod.HistoricalSnapshot(
        datetime.now(timezone.utc),
        {"109": released},
    )

    record, source = backfill_mod._best_recovery_record(
        [],
        current,
        {"event": "released", "inmate_number": "109", "timestamp_utc": _now_iso()},
    )

    assert record is None
    assert source is None


def test_load_snapshots_skips_malformed_history(monkeypatch):
    now = _now_iso()
    valid = Snapshot(
        generated_utc=now,
        inmate_count=1,
        inmates=[_inmate("101")],
    ).model_dump(mode="json")

    monkeypatch.setattr(backfill_mod, "_snapshot_commits", lambda since: ["bad", "good"])

    def fake_run_git(*args: str) -> str:
        if args[0] == "show" and args[1] == "bad:data/current.json":
            return "[]"
        if args[0] == "show" and args[1] == "good:data/current.json":
            return json.dumps(valid)
        raise AssertionError(args)

    monkeypatch.setattr(backfill_mod, "_run_git", fake_run_git)

    snapshots = backfill_mod._load_snapshots(datetime.now(timezone.utc) - timedelta(days=1))

    assert len(snapshots) == 1
    assert snapshots[0].inmates["101"].first_name == "JANE"


def test_backfill_respects_cutoff_and_fills_only_missing_fields(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    orc_path.write_text(
        json.dumps({"offenses": {"2913.02": {"title": "Assault", "degree": "M1"}}}),
        encoding="utf-8",
    )

    recent = _now_iso(timedelta(hours=-1))
    old = _now_iso(timedelta(days=-8))
    rows = [
        {
            "event": "booked",
            "timestamp_utc": recent,
            "inmate_number": "102",
            "name": "DOE, JANE",
            "tier": "F1",
            "category": None,
        },
        {
            "event": "released",
            "timestamp_utc": recent,
            "inmate_number": "103",
            "name": "DOE, JOHN",
            "tier": None,
            "category": "Existing",
        },
        {
            "event": "booked",
            "timestamp_utc": old,
            "inmate_number": "104",
            "name": "DOE, OLD",
            "tier": None,
            "category": None,
        },
    ]
    anon_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(
        backfill_mod,
        "_load_snapshots",
        lambda since: [
            backfill_mod.HistoricalSnapshot(
                datetime.now(timezone.utc) - timedelta(minutes=30),
                {
                    "102": _inmate("102"),
                    "103": _inmate("103"),
                    "104": _inmate("104"),
                },
            )
        ],
    )

    result = backfill_mod.backfill(days=7)

    written = json.loads(anon_path.read_text(encoding="utf-8"))
    assert result["eligible"] == 2
    assert result["updated"] == 2
    assert written[0]["tier"] == "F1"
    assert written[0]["category"] == "Assault"
    assert written[1]["tier"] == "M1"
    assert written[1]["category"] == "Existing"
    assert written[2]["tier"] is None
    assert written[2]["category"] is None
    assert written[0]["inmate_number"] == "102"


def test_backfill_dry_run_does_not_write(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    orc_path.write_text(
        json.dumps({"offenses": {"2913.02": {"title": "Assault", "degree": "M1"}}}),
        encoding="utf-8",
    )
    row = {
        "event": "booked",
        "timestamp_utc": _now_iso(timedelta(hours=-1)),
        "inmate_number": "105",
        "name": "DOE, JANE",
        "tier": None,
        "category": None,
    }
    original = json.dumps([row], indent=2)
    anon_path.write_text(original, encoding="utf-8")

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(
        backfill_mod,
        "_load_snapshots",
        lambda since: [
            backfill_mod.HistoricalSnapshot(
                datetime.now(timezone.utc) - timedelta(minutes=30),
                {"105": _inmate("105")},
            )
        ],
    )

    result = backfill_mod.backfill(days=7, dry_run=True)

    assert result["updated"] == 1
    assert anon_path.read_text(encoding="utf-8") == original


def test_backfill_anonymizes_takedowns_before_write(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    orc_path.write_text(json.dumps({"offenses": {}}), encoding="utf-8")
    (data_dir / "takedowns.json").write_text(json.dumps(["106"]), encoding="utf-8")
    anon_path.write_text(
        json.dumps(
            [
                {
                    "event": "booked",
                    "timestamp_utc": _now_iso(timedelta(hours=-1)),
                    "inmate_number": "106",
                    "name": "DOE, SEALED",
                    "tier": "F3",
                    "category": "Assault",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(backfill_mod, "_load_snapshots", lambda since: [])

    result = backfill_mod.backfill(days=7)

    written = json.loads(anon_path.read_text(encoding="utf-8"))
    assert result["takedown_anonymized"] == 1
    assert result["eligible"] == 0
    assert "inmate_number" not in written[0]
    assert "name" not in written[0]
    assert written[0]["tier"] == "F3"
    assert written[0]["category"] == "Assault"


def test_backfill_noop_when_recent_rows_are_already_enriched(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    orc_path.write_text(json.dumps({"offenses": {}}), encoding="utf-8")
    rows = [
        {
            "event": "booked",
            "timestamp_utc": _now_iso(timedelta(hours=-1)),
            "inmate_number": "107",
            "name": "DOE, JANE",
            "tier": "M1",
            "category": "Assault",
        }
    ]
    original = json.dumps(rows, indent=2)
    anon_path.write_text(original, encoding="utf-8")

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(backfill_mod, "_load_snapshots", lambda since: [])

    result = backfill_mod.backfill(days=7)

    assert result["updated"] == 0
    assert anon_path.read_text(encoding="utf-8") == original


def test_backfill_uses_live_roster_when_history_is_unavailable(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    current_path = data_dir / "current.json"
    orc_path.write_text(
        json.dumps({"offenses": {"2913.02": {"title": "Assault", "degree": "M1"}}}),
        encoding="utf-8",
    )
    now = _now_iso(timedelta(hours=-1))
    anon_path.write_text(
        json.dumps(
            [
                {
                    "event": "booked",
                    "timestamp_utc": now,
                    "inmate_number": "110",
                    "name": "DOE, JANE",
                    "tier": None,
                    "category": None,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    current_path.write_text(
        json.dumps(
            Snapshot(
                generated_utc=_now_iso(),
                inmate_count=1,
                inmates=[_inmate("110")],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "CURRENT_PATH", current_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(backfill_mod, "_load_snapshots", lambda since: [])

    result = backfill_mod.backfill(days=7)

    written = json.loads(anon_path.read_text(encoding="utf-8"))
    assert result["updated"] == 1
    assert result["live_fallback"] == 1
    assert result["historical_recovery"] == 0
    assert written[0]["tier"] == "M1"
    assert written[0]["category"] == "Assault"


def test_backfill_does_not_use_live_roster_for_release(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anon_path = data_dir / "anon_changelog.json"
    orc_path = data_dir / "orc_offenses.json"
    current_path = data_dir / "current.json"
    orc_path.write_text(
        json.dumps({"offenses": {"2913.02": {"title": "Assault", "degree": "M1"}}}),
        encoding="utf-8",
    )
    now = _now_iso(timedelta(hours=-1))
    anon_path.write_text(
        json.dumps(
            [
                {
                    "event": "released",
                    "timestamp_utc": now,
                    "inmate_number": "111",
                    "name": "DOE, RELEASED",
                    "tier": None,
                    "category": None,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    current_path.write_text(
        json.dumps(
            Snapshot(
                generated_utc=_now_iso(),
                inmate_count=1,
                inmates=[_inmate("111")],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(backfill_mod, "ANON_CHANGELOG_PATH", anon_path)
    monkeypatch.setattr(backfill_mod, "CURRENT_PATH", current_path)
    monkeypatch.setattr(backfill_mod, "ORC_OFFENSES_PATH", orc_path)
    monkeypatch.setattr(backfill_mod, "_load_snapshots", lambda since: [])

    result = backfill_mod.backfill(days=7)

    written = json.loads(anon_path.read_text(encoding="utf-8"))
    assert result["updated"] == 0
    assert result["unresolved"] == 1
    assert result["live_fallback"] == 0
    assert written[0]["tier"] is None
    assert written[0]["category"] is None
