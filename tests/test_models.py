import pytest

from scraper.models import HistoryRecord, Inmate, Snapshot


def test_full_name_joins_present_parts():
    inm = Inmate(inmate_number="1", last_name="DOE", first_name="JOHN", middle_name="Q")
    assert inm.full_name == "DOE JOHN Q"


def test_full_name_is_empty_when_no_parts():
    assert Inmate(inmate_number="1").full_name == ""


def test_full_name_caps_each_part_and_total_length():
    huge = "X" * 5000
    inm = Inmate(inmate_number="1", last_name=huge, first_name=huge, middle_name=huge)
    # Per-part 80-char cap + " " join => 80 + 1 + 80 + 1 + 80 = 242 chars max.
    assert len(inm.full_name) <= 256
    assert "X" * 80 in inm.full_name
    assert "X" * 81 not in inm.full_name


def test_inmate_rejects_empty_inmate_number():
    # data-F4: empty inmate_number would bucket multiple records together on
    # diff and could escape into filesystem paths via photo_filename.
    with pytest.raises(ValueError, match="non-empty"):
        Inmate(inmate_number="")
    with pytest.raises(ValueError, match="non-empty"):
        Inmate(inmate_number="   ")


def test_inmate_rejects_non_digit_inmate_number():
    # tpl-sec-F3: a parser-drift override could put "..", "/", or query-string
    # characters into inmate_number, which then flows into photo_filename and
    # template URLs. Fail closed at the model layer.
    for bad in ("..", "/etc/passwd", "1234?", "abc", "12 34"):
        with pytest.raises(ValueError, match="digits"):
            Inmate(inmate_number=bad)


def test_inmate_accepts_pure_digits():
    inm = Inmate(inmate_number="14502205")
    assert inm.inmate_number == "14502205"
    # Surrounding whitespace is stripped, not rejected.
    inm2 = Inmate(inmate_number="  14502205  ")
    assert inm2.inmate_number == "14502205"


def test_snapshot_rejects_mismatched_count():
    # data-F2: inmate_count must agree with len(inmates), both on save and on
    # load. The validator runs on both.
    with pytest.raises(ValueError, match="inmate_count"):
        Snapshot(
            generated_utc="",
            inmate_count=2,
            inmates=[Inmate(inmate_number="1")],
        )


def test_snapshot_rejects_duplicate_inmate_numbers():
    with pytest.raises(ValueError, match="duplicate inmate_number"):
        Snapshot(
            generated_utc="",
            inmate_count=2,
            inmates=[Inmate(inmate_number="1"), Inmate(inmate_number="1")],
        )


def test_snapshot_accepts_empty_generated_utc():
    # web/build.py constructs an empty Snapshot at bootstrap when there is
    # no data file. Empty must remain valid.
    s = Snapshot(generated_utc="", inmate_count=0, inmates=[])
    assert s.generated_utc == ""


def test_snapshot_rejects_non_iso_z_generated_utc():
    # data-F5: a hand-edited or NTP-skewed timestamp without the strict
    # ...Z shape breaks downstream sort and compare logic.
    with pytest.raises(ValueError, match="generated_utc"):
        Snapshot(generated_utc="2026-05-14 01:00:00", inmate_count=0, inmates=[])
    with pytest.raises(ValueError, match="generated_utc"):
        Snapshot(generated_utc="2026-05-14T01:00:00+00:00", inmate_count=0, inmates=[])


def test_snapshot_accepts_strict_utcnow_iso():
    s = Snapshot(generated_utc="2026-05-14T01:00:00Z", inmate_count=0, inmates=[])
    assert s.generated_utc == "2026-05-14T01:00:00Z"


def test_history_record_round_trip():
    # data-F7: history.json records are now validated on load. Round trip
    # confirms the shape committed by web/build.py loads back equivalent.
    r = HistoryRecord(date="2026-05-14", count=1210, booked_24h=42, released_24h=37)
    dumped = r.model_dump()
    assert dumped == {
        "date": "2026-05-14", "count": 1210, "booked_24h": 42, "released_24h": 37,
    }
    assert HistoryRecord(**dumped) == r


def test_history_record_rejects_malformed_date():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        HistoryRecord(date="May 14, 2026", count=1210)
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        HistoryRecord(date="2026/05/14", count=1210)


def test_history_record_defaults_booked_and_released_to_zero():
    r = HistoryRecord(date="2026-05-14", count=1210)
    assert r.booked_24h == 0
    assert r.released_24h == 0
