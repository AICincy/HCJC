"""Coverage for the pure helpers in web/build.py.

This is the prerequisite test bed for the future build.py refactor: every
helper that derives a card field, a tier label, a bond figure, or a stat
should have a fixed-point regression here so a later reorg can't silently
change rendered output.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper.models import ChangeEvent, Charge, Inmate
from web import build


def _inm(charges=None, dob="", booking_date="") -> Inmate:
    return Inmate(
        inmate_number="1",
        last_name="DOE",
        first_name="JOHN",
        date_of_birth=dob,
        booking_date=booking_date,
        charges=charges or [],
    )


# ----- _charge_tier ---------------------------------------------------------

def test_charge_tier_uses_explicit_degree_suffix():
    c = Charge(orc_code="2903.02", description="MURDER F1")
    assert build._charge_tier(c, {}) == {"label": "F1", "kind": "felony"}


def test_charge_tier_uses_orc_default_when_no_suffix():
    offenses = {"2903.02": {"degree": "F1", "title": "MURDER"}}
    c = Charge(orc_code="2903.02", description="MURDER")
    assert build._charge_tier(c, offenses) == {"label": "F1", "kind": "felony"}


def test_charge_tier_falls_back_to_common_pleas_venue():
    # NONE-coded hold with a Common Pleas case# => felony venue.
    c = Charge(orc_code="NONE", description="HOLD", common_pleas_case="B2400001")
    assert build._charge_tier(c, {}) == {"label": "F", "kind": "felony"}


def test_charge_tier_falls_back_to_municipal_venue():
    c = Charge(orc_code="NONE", description="HOLD", municipal_case="C24001")
    assert build._charge_tier(c, {}) == {"label": "M", "kind": "misdemeanor"}


def test_charge_tier_returns_none_when_nothing_decides():
    assert build._charge_tier(Charge(orc_code="NONE", description=""), {}) is None


def test_charge_tier_regex_rejects_invalid_degree_letters():
    # ORC defines F1-F5 and M1-M4 (plus MM). A widened regex like [FM]\d
    # accepts F6/F9/M5/M0, etc., which are parsing artifacts, not degrees.
    # With NONE ORC + no venue hint, an invalid suffix must fall through.
    assert build._charge_tier(Charge(orc_code="NONE", description="MURDER F6"), {}) is None
    assert build._charge_tier(Charge(orc_code="NONE", description="ROBBERY M5"), {}) is None
    assert build._charge_tier(Charge(orc_code="NONE", description="ASSAULT F0"), {}) is None


def test_charge_tier_regex_anchors_to_end_of_description():
    # The regex must require the degree as the final non-whitespace token.
    # Without the \s*$ anchor, a mid-string degree fragment would match.
    c = Charge(orc_code="NONE", description="F1 PRELIM HEARING NOT SET")
    assert build._charge_tier(c, {}) is None


# ----- _tier_counts / _primary_tier ----------------------------------------

def test_tier_counts_splits_felony_and_misdemeanor():
    inm = _inm(charges=[
        Charge(orc_code="2903.02", description="MURDER F1"),
        Charge(orc_code="2913.02", description="THEFT M1"),
        Charge(orc_code="2903.13", description="ASSAULT F4"),
    ])
    counts = build._tier_counts(inm, {})
    assert counts == {"felony": 2, "misdemeanor": 1, "unknown": 0}


def test_primary_tier_prefers_more_serious_degree():
    inm = _inm(charges=[
        Charge(orc_code="2913.02", description="THEFT M1"),
        Charge(orc_code="2903.02", description="MURDER F1"),
    ])
    t = build._primary_tier(inm)
    assert t is not None and t["kind"] == "felony"
    assert t["label"].startswith("F1")


def test_primary_tier_returns_none_for_no_chargeable_signal():
    assert build._primary_tier(_inm()) is None


# ----- _avatar_initials ----------------------------------------------------

def test_avatar_initials_first_and_last():
    assert build._avatar_initials("DOE JOHN") == "DJ"


def test_avatar_initials_single_word():
    assert build._avatar_initials("CHER") == "CH"


def test_avatar_initials_empty_uses_question_mark():
    assert build._avatar_initials("") == "?"
    assert build._avatar_initials("   ") == "?"


# ----- _expand_race / _expand_sex ------------------------------------------

def test_expand_race_known_codes():
    assert build._expand_race("W") == "White"
    assert build._expand_race("B") == "Black"
    assert build._expand_race("") == "—"


def test_expand_sex_known_codes():
    assert build._expand_sex("M") == "Male"
    assert build._expand_sex("F") == "Female"
    assert build._expand_sex("") == "—"


def test_expand_race_passthrough_unknown():
    assert build._expand_race("XYZ") == "XYZ"


# ----- _approx_age ---------------------------------------------------------

def test_approx_age_handles_two_digit_year():
    # '90 -> 1990 (mapping rule: 1900 + yr if that makes the person older
    # than ~25 today). Compute the expectation off datetime.now() so the
    # assertion stays exact rather than drifting with the calendar.
    today = datetime.now()
    expected = today.year - 1990 - ((today.month, today.day) < (1, 1))
    assert build._approx_age("1/1/90") == expected


def test_approx_age_invalid_returns_none():
    assert build._approx_age("") is None
    assert build._approx_age("not a date") is None
    assert build._approx_age("13/45/99") is None


# ----- _pct_ordinal --------------------------------------------------------

@pytest.mark.parametrize("p,expected", [
    (0.01, "1st"),
    (0.02, "2nd"),
    (0.03, "3rd"),
    (0.04, "4th"),
    (0.11, "11th"),
    (0.12, "12th"),
    (0.13, "13th"),
    (0.21, "21st"),
    (0.22, "22nd"),
    (0.23, "23rd"),
    (0.50, "50th"),
    (0.79, "79th"),
    (0.99, "99th"),
    (1.00, "100th"),
    (0.0, "0th"),
])
def test_pct_ordinal_handles_ones_place_and_teens(p, expected):
    assert build._pct_ordinal(p) == expected


def test_pct_ordinal_none_or_zero_safe():
    assert build._pct_ordinal(0) == "0th"
    assert build._pct_ordinal(None) == "0th"


# ----- _rfc822 -------------------------------------------------------------

def test_rfc822_iso_utc_z_form():
    # Trailing Z (Zulu / UTC) is the format ChangeEvent.timestamp_utc uses.
    out = build._rfc822("2026-05-14T17:16:37Z")
    # Format is "Day, DD Mon YYYY HH:MM:SS +0000"
    assert out == "Thu, 14 May 2026 17:16:37 +0000"


def test_rfc822_iso_with_offset():
    # +00:00 form is the other common UTC representation; both should pass.
    assert build._rfc822("2026-05-14T17:16:37+00:00") == "Thu, 14 May 2026 17:16:37 +0000"


def test_rfc822_naive_treated_as_utc():
    # Naive datetimes get tagged UTC (the rest of the codebase is UTC-only).
    out = build._rfc822("2026-01-01T00:00:00")
    assert out == "Thu, 01 Jan 2026 00:00:00 +0000"


@pytest.mark.parametrize("bad", ["", None, "not a date", "2026-99-99T00:00:00Z"])
def test_rfc822_garbage_returns_empty(bad):
    assert build._rfc822(bad) == ""


# ----- _feed_description ---------------------------------------------------

def test_feed_description_booked_with_note_in_note_form():
    out = build._feed_description("booked", "DOE JANE", "12345", "booked 5/14/26")
    assert "DOE JANE" in out and "(#12345)" in out and "5/14/26" in out


def test_feed_description_released_drops_redundant_note():
    # The old form was "released no longer on HCSO public roster" — broken
    # English. The new form composes a clean sentence regardless of note.
    out = build._feed_description("released", "DOE JOHN", "67890", "no longer on HCSO public roster")
    assert "DOE JOHN" in out
    assert "released" not in out.split(" ", 1)[0]  # no awkward leading "released"
    assert "(#67890)" in out
    assert out.endswith(".")


def test_feed_description_unknown_event_falls_through():
    out = build._feed_description("custodial-transfer", "ROE J", "1", "moved to JC-B")
    assert "ROE J" in out and "custodial-transfer" in out and "moved to JC-B" in out


# ----- feed.xml renders as strict XML (regression: &middot; bug) -----------

def test_feed_template_emits_strict_xml(tmp_path):
    """Lock in PR #34's fix: titles + descriptions must not contain HTML
    entities that strict XML parsers reject (`&middot;`, `&rsquo;`, etc).
    Renders feed.xml with a synthetic event and parses with ElementTree
    — any undefined entity would raise ParseError."""
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).resolve().parent.parent / "web" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["rfc822"] = build._rfc822
    env.globals["feed_description"] = build._feed_description

    class _E:
        event = "released"
        name = "DOE JANE"
        inmate_number = "12345"
        timestamp_utc = "2026-05-14T17:16:37Z"
        note = "no longer on HCSO public roster"

    xml_str = env.get_template("feed.xml").render(
        events=[_E()],
        site_url="https://example.com",
        feed_title="test",
        feed_desc="test",
        self_path="/feed.xml",
    )
    # If the template emits `&middot;` instead of the unicode character,
    # this parse will raise. The whole point of this test is to fail loudly.
    root = ET.fromstring(xml_str)
    items = root.findall(".//item")
    assert len(items) == 1
    title = items[0].findtext("title")
    pub = items[0].findtext("pubDate")
    cat = items[0].findtext("category")
    desc = items[0].findtext("description")
    assert title == "released · DOE JANE"
    assert pub == "Thu, 14 May 2026 17:16:37 +0000"  # RFC 822, not ISO
    assert cat == "released"
    assert "DOE JANE" in desc and "(#12345)" in desc


# ----- _booking_seq --------------------------------------------------------

def test_booking_seq_formats_year_and_sequence():
    assert build._booking_seq("26002740") == "booking #2,740 of 2026"


def test_booking_seq_returns_empty_on_garbage():
    assert build._booking_seq("") == ""
    assert build._booking_seq("ABC") == ""


# ----- _bond_by_tier -------------------------------------------------------

def test_bond_by_tier_sums_by_kind():
    inm = _inm(charges=[
        Charge(orc_code="2903.02", description="MURDER F1", bond_amount="$50,000.00"),
        Charge(orc_code="2913.02", description="THEFT M1", bond_amount="$500"),
        Charge(orc_code="NONE", description="HOLD", bond_amount="$100"),
    ])
    bonds = build._bond_by_tier(inm, {})
    assert bonds["felony"] == "$50,000"
    assert bonds["misdemeanor"] == "$500"
    # NONE with no venue => "other".
    assert bonds["other"] == "$100"
    assert bonds["total"] == "$50,600"


def test_bond_by_tier_zero_for_empty_amounts():
    inm = _inm(charges=[Charge(orc_code="2903.02", description="ASSAULT F4", bond_amount="")])
    assert build._bond_by_tier(inm, {})["total"] == "$0"


# ----- _days_in_custody ----------------------------------------------------

def test_days_in_custody_positive_for_past_booking():
    d = datetime.now() - timedelta(days=3)
    three_days_ago = f"{d.month}/{d.day}/{d.year % 100:02d}"
    days = build._days_in_custody(_inm(booking_date=three_days_ago))
    assert days == 3


def test_days_in_custody_unparseable_returns_none():
    assert build._days_in_custody(_inm(booking_date="not a date")) is None
    assert build._days_in_custody(_inm()) is None


# ----- _short_month_label --------------------------------------------------

def test_short_month_label_formats_to_apostrophe_year():
    assert build._short_month_label("May 2026") == "May '26"


def test_short_month_label_passes_through_unrecognized():
    assert build._short_month_label("Unknown") == "Unknown"


# ----- _chap_slug ----------------------------------------------------------

def test_chap_slug_lowercases_and_dashes():
    assert build._chap_slug("Violence / Sex") == "violence-sex"
    assert build._chap_slug("Drugs") == "drugs"


# ----- _events_in_window / _events_for_recent ------------------------------

def _evt(event: str, when: datetime, note: str = "") -> ChangeEvent:
    return ChangeEvent(
        event=event,
        inmate_number="1",
        name="DOE JOHN",
        timestamp_utc=when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        note=note,
    )


def test_events_in_window_drops_old_events():
    now = datetime.now(timezone.utc)
    recent = _evt("updated", now - timedelta(hours=1))
    old = _evt("updated", now - timedelta(hours=48))
    kept = build._events_in_window([recent, old], hours=8)
    assert kept == [recent]


def test_events_for_recent_filters_booked_by_actual_booking_date():
    now = datetime.now(timezone.utc)
    # 'booked' observation is fresh, but the actual HCSO booking date is old:
    # this should be dropped to keep the first-sweep seeding out of the feed.
    stale_booking = _evt(
        "booked",
        now - timedelta(hours=1),
        note=(now - timedelta(days=30)).strftime("booked %m/%d/%y"),
    )
    fresh_booking = _evt(
        "booked",
        now - timedelta(hours=1),
        note=now.strftime("booked %m/%d/%y"),
    )
    kept = build._events_for_recent([stale_booking, fresh_booking], hours=8)
    assert kept == [fresh_booking]


def test_events_for_recent_keeps_releases_regardless_of_note():
    now = datetime.now(timezone.utc)
    rel = _evt("released", now - timedelta(hours=1))
    assert build._events_for_recent([rel], hours=8) == [rel]


# ----- _offense_for_code ---------------------------------------------------

def test_offense_for_code_falls_back_to_other_for_unknown():
    # Codes that don't match any known chapter still get classified as the
    # generic "other" bucket so the renderer never has a missing color.
    off = build._offense_for_code("9999.99")
    assert off is not None and off["cls"] == "traffic"


@pytest.mark.parametrize("code,expected_cls", [
    ("2903.02", "2903"),  # homicide / violence
    ("2925.11", "2925"),  # drugs
    ("2913.02", "2913"),  # theft / fraud
])
def test_offense_for_code_classifies_known_chapters(code, expected_cls):
    off = build._offense_for_code(code)
    assert off is not None
    assert off["cls"] == expected_cls


# ----- _load_caselaw_cache -------------------------------------------------
#
# The function reads the hard-coded relative path Path("data/orc_caselaw.json"),
# so each test shifts CWD into tmp_path with monkeypatch.chdir to control where
# it looks. Failure modes (missing file, malformed JSON, missing key) must all
# degrade silently to {} so the /statute/ page renders without the case-law
# block instead of 500-ing.

def test_load_caselaw_cache_returns_empty_when_file_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # No data/ directory at all — the missing-file path.
    assert build._load_caselaw_cache() == {}


def test_load_caselaw_cache_returns_empty_on_malformed_json(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "orc_caselaw.json").write_text("{not valid json", encoding="utf-8")
    assert build._load_caselaw_cache() == {}


def test_load_caselaw_cache_returns_by_code_dict(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    payload = {
        "by_code": {
            "2903.02": [{"name": "State v. Doe", "cite": "1 Ohio St.3d 1"}],
            "2913.02": [{"name": "State v. Roe", "cite": "2 Ohio St.3d 2"}],
        },
        "generated_utc": "2026-05-14T00:00:00Z",
    }
    (tmp_path / "data" / "orc_caselaw.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    out = build._load_caselaw_cache()
    assert out == payload["by_code"]
    assert "2903.02" in out and out["2903.02"][0]["name"] == "State v. Doe"


def test_load_caselaw_cache_returns_empty_when_by_code_key_missing(tmp_path: Path, monkeypatch):
    # Valid JSON, but no by_code key — the .get("by_code", {}) fallback path.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "orc_caselaw.json").write_text(
        json.dumps({"generated_utc": "2026-05-14T00:00:00Z"}), encoding="utf-8"
    )
    assert build._load_caselaw_cache() == {}


# ----- _iso_booking_date ----------------------------------------------------

def test_iso_booking_date_parses_short_year():
    # HCSO's MM/DD/YY form should round-trip to ISO-8601 YYYY-MM-DD.
    inm = _inm(booking_date="5/12/26")
    assert build._iso_booking_date(inm) == "2026-05-12"


def test_iso_booking_date_parses_four_digit_year():
    inm = _inm(booking_date="11/3/2025")
    assert build._iso_booking_date(inm) == "2025-11-03"


def test_iso_booking_date_returns_none_for_empty():
    assert build._iso_booking_date(_inm(booking_date="")) is None
    assert build._iso_booking_date(_inm()) is None  # default empty


def test_iso_booking_date_returns_none_for_garbage():
    assert build._iso_booking_date(_inm(booking_date="not a date")) is None
    assert build._iso_booking_date(_inm(booking_date="2026-05-12")) is None  # ISO input is rejected; only HCSO MM/DD forms
