"""Feed-integration regression tests (Option A, Phases 1+2, 2026-09-20).

Covers web/feeds.py and the safety page contract:
aggregation math, privacy (forbidden columns never reach a template context),
graceful empty-feed handling, frozen-source labeling, plain-English mapping
coverage over the current pulls, and a strict-Undefined render of
safety.html so template errors surface here instead of at build time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from web import feeds as feeds_mod

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
TEMPLATES = REPO / "web" / "templates"


def _write_feed(tmp_path: Path, filename: str, rows: list[dict], stamp: str = "2026-09-20T12:00:00Z") -> None:
    payload = {"generated_utc": stamp, "dataset_id": "test", "row_count": len(rows), "rows": rows}
    (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def fixture_dir(tmp_path: Path) -> Path:
    _write_feed(
        tmp_path,
        "crime_stars_recent.json",
        [
            {"stars_category": "Agg Assault", "type": "Part 1 Violent", "datereported": "2026-09-19T10:00:00.000",
             "address_x": "1XX MAIN ST", "cpd_neighborhood": "DOWNTOWN"},
            {"stars_category": "Agg Assault", "type": "Part 1 Violent", "datereported": "2026-09-18T10:00:00.000",
             "address_x": "2XX MAIN ST", "cpd_neighborhood": "DOWNTOWN"},
            {"stars_category": "Part 2", "type": "Part 2", "datereported": "2026-09-17",
             "address_x": "3XX ELM ST", "sna_neighborhood": "OTR"},
            {"stars_category": "Burglary/BE", "type": "Part 1 Property", "datereported": "2026-09-16T10:00:00.000",
             "address_x": "4XX VINE ST", "cpd_neighborhood": "DOWNTOWN"},
        ],
    )
    _write_feed(
        tmp_path,
        "traffic_stops_drivers_recent.json",
        [
            {"race": "BLACK", "sex": "MALE", "action_taken_cid": "WARNING"},
            {"race": "BLACK", "sex": "FEMALE", "action_taken_cid": "CITATION TRAFFIC"},
            {"race": "WHITE", "sex": "MALE", "action_taken_cid": "WARNING"},
            {"race": "UNKNOWN", "sex": "MALE", "action_taken_cid": "NONE"},
            # Edge values seen in the real pulls: unlisted race -> "Other",
            # blank race -> "Unknown", unlisted sex -> "Unknown".
            {"race": "HISPANIC", "sex": "X", "action_taken_cid": "NONE"},
            {"race": "", "sex": "MALE", "action_taken_cid": "NONE"},
        ],
    )
    _write_feed(tmp_path, "pedestrian_stops_recent.json", [])
    _write_feed(
        tmp_path,
        "cfs_recent.json",
        [
            {"event_number": "E1", "incident_type_id": "TSTOP", "disposition_text": "CIT: CITED",
             "create_time_incident": "2026-09-19T08:00:00.000", "address_x": "4XX OAK ST",
             "cpd_neighborhood": "AVONDALE"},
            # Duplicate event_number: deduped to one incident.
            {"event_number": "E1", "incident_type_id": "TSTOP", "disposition_text": "CIT: CITED",
             "create_time_incident": "2026-09-19T08:00:00.000", "address_x": "4XX OAK ST",
             "cpd_neighborhood": "AVONDALE"},
        ],
    )
    _write_feed(tmp_path, "cfs_pdi_recent.json", [])
    _write_feed(
        tmp_path,
        "shootings_recent.json",
        [
            {"type": "NONFATAL", "datetimeoccured": "9/18/2026 11:15:00 PM",
             "streetblock": "1600 Block of MARLOWE AV", "sna_neighborhood": "College Hill"},
        ],
    )
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Aggregation math
# ---------------------------------------------------------------------------


def test_stop_aggregation_counts(fixture_dir: Path):
    stops = feeds_mod.summarize_stops(fixture_dir)
    drivers = stops["drivers"]
    assert drivers["total"] == 6
    assert dict(drivers["by_race"]) == {"Black": 2, "Unknown": 2, "White": 1, "Other": 1}
    assert dict(drivers["by_sex"]) == {"Male": 4, "Female": 1, "Unknown": 1}
    assert dict(drivers["by_action"]) == {
        "No action taken": 3,
        "Warning, no citation": 2,
        "Traffic citation": 1,
    }
    # Race counts partition the total.
    total = sum(c for _, c in drivers["by_race"])
    assert total == drivers["total"]


def test_race_action_table_consistent(fixture_dir: Path):
    drivers = feeds_mod.summarize_stops(fixture_dir)["drivers"]
    table = drivers["race_action_table"]
    assert drivers["race_columns"] == ["Black", "White", "Unknown", "Other"]
    for row in table:
        assert sum(row["counts"]) == row["total"]
    assert sum(r["total"] for r in table) == drivers["total"]
    warning = next(r for r in table if r["action"] == "Warning, no citation")
    assert warning["counts"] == [1, 1, 0, 0]
    no_action = next(r for r in table if r["action"] == "No action taken")
    # UNKNOWN + blank race -> Unknown bucket; HISPANIC -> Other bucket.
    assert no_action["counts"] == [0, 0, 2, 1]


def test_blank_and_other_actions_do_not_duplicate_rows(tmp_path: Path):
    """Regression: raw "" / None and "OTHER" must not produce duplicate
    display rows, and the race table must agree with the bars."""
    rows = [
        {"race": "BLACK", "sex": "MALE", "action_taken_cid": "OTHER"},
        {"race": "WHITE", "sex": "MALE", "action_taken_cid": ""},
        {"race": "BLACK", "sex": "FEMALE", "action_taken_cid": None},
        {"race": "WHITE", "sex": "MALE", "action_taken_cid": "other"},
    ]
    _write_feed(
        tmp_path,
        "traffic_stops_drivers_recent.json",
        rows,
    )
    _write_feed(tmp_path, "pedestrian_stops_recent.json", [])
    drivers = feeds_mod.summarize_stops(tmp_path)["drivers"]
    labels = [label for label, _ in drivers["by_action"]]
    assert labels == ["Other", "Not recorded"]
    assert dict(drivers["by_action"]) == {"Other": 2, "Not recorded": 2}
    table = drivers["race_action_table"]
    assert [r["action"] for r in table] == ["Other", "Not recorded"]
    for row in table:
        assert sum(row["counts"]) == row["total"]
    assert sum(r["total"] for r in table) == drivers["total"] == 4


def test_stars_summary(fixture_dir: Path):
    stars = feeds_mod.summarize_crime_stars(fixture_dir)
    assert stars["total"] == 4
    assert dict(stars["by_category"]) == {
        "Aggravated assault": 2,
        "Part 2": 1,
        "Burglary / breaking and entering": 1,
    }
    assert dict(stars["by_type"]) == {
        "Part 1 — violent": 2,
        "Part 2": 1,
        "Part 1 — property": 1,
    }
    assert stars["vintage"] == "2026-09-20T12:00:00Z"
    assert not stars["empty"]


def test_unknown_stars_type_is_unclassified_not_part2(tmp_path: Path):
    """Regression: an unknown STARS type must not silently inflate Part 2."""
    _write_feed(
        tmp_path,
        "crime_stars_recent.json",
        [
            {"stars_category": "Part 2", "type": "Part 9", "datereported": "2026-09-19T10:00:00.000",
             "address_x": "1XX MAIN ST", "cpd_neighborhood": "DOWNTOWN"},
        ],
    )
    stars = feeds_mod.summarize_crime_stars(tmp_path)
    assert dict(stars["by_type"]) == {"Unclassified": 1}


def test_incidents_without_event_number_are_not_deduped(tmp_path: Path):
    """Regression (blocker): rows with no event number must never collapse
    into a single incident."""
    _write_feed(
        tmp_path,
        "cfs_recent.json",
        [
            {"incident_type_id": "TSTOP", "create_time_incident": "2026-09-19T08:00:00.000",
             "address_x": "1XX MAIN ST", "cpd_neighborhood": "AVONDALE"},
            {"incident_type_id": "THEFTR", "create_time_incident": "2026-09-19T07:00:00.000",
             "address_x": "2XX ELM ST", "cpd_neighborhood": "AVONDALE"},
        ],
    )
    items = feeds_mod.latest_incidents(tmp_path)
    assert len(items) == 2


def test_latest_incidents_sorted_and_deduped(fixture_dir: Path):
    items = feeds_mod.latest_incidents(fixture_dir, n=30)
    # 4 STARS + 1 deduped CFS + 1 shooting = 6
    assert len(items) == 6
    keys = [i["sort_key"] for i in items]
    assert keys == sorted(keys, reverse=True)
    assert items[0]["when_display"] == "Sep 19, 10:00 AM"
    cfs = next(i for i in items if "citation issued" in i["what"])
    assert cfs["when_display"] == "Sep 19, 8:00 AM"
    shooting = next(i for i in items if i["what"].startswith("Shooting"))
    assert shooting["when_display"] == "Sep 18, 11:15 PM"
    # Date-only STARS rows take the date branch of the display formatter.
    part2 = next(i for i in items if i["what"] == "Reported crime — Part 2")
    assert part2["when_display"] == "Sep 17, 2026"


# ---------------------------------------------------------------------------
# 2. Privacy: forbidden columns never reach a rendered context
# ---------------------------------------------------------------------------


def _all_keys(obj) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= _all_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            keys |= _all_keys(v)
    return keys


def _all_values(obj) -> list[str]:
    vals: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            vals += _all_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            vals += _all_values(v)
    elif isinstance(obj, str):
        vals.append(obj)
    return vals


def test_no_forbidden_columns_in_context(fixture_dir: Path):
    ctx = feeds_mod.safety_context(fixture_dir)
    keys = _all_keys(ctx)
    leaked = feeds_mod.FORBIDDEN_COLUMNS & keys
    assert not leaked, f"forbidden columns in template context: {leaked}"


_FORBIDDEN_VALUE_SOURCES = {
    "traffic_stops_drivers_recent.json": ("citizen_id", "unique_case_number", "license_plate_state"),
    "pedestrian_stops_recent.json": ("citizen_id", "unique_case_number", "license_plate_state"),
    "cfs_recent.json": ("event_number",),
    "cfs_pdi_recent.json": ("event_number",),
    "crime_stars_recent.json": ("rms_no",),
    "shootings_recent.json": ("shootid",),
}


def test_no_forbidden_columns_against_real_data():
    """Belt and braces on the real pulls: the module selects only the columns
    it needs, so even the full-size feeds must not leak identifiers. Checks
    keys AND string values (an identifier inside a rendered string would
    also be a leak)."""
    ctx = feeds_mod.safety_context(DATA)
    keys = _all_keys(ctx)
    leaked = feeds_mod.FORBIDDEN_COLUMNS & keys
    assert not leaked, f"forbidden columns in template context: {leaked}"
    forbidden_values: set[str] = set()
    for filename, columns in _FORBIDDEN_VALUE_SOURCES.items():
        payload = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for r in payload.get("rows", []):
            for col in columns:
                v = r.get(col)
                if isinstance(v, str) and v.strip():
                    forbidden_values.add(v.strip())
    blob = "\n".join(_all_values(ctx))
    leaked_values = [v for v in forbidden_values if v in blob]
    assert not leaked_values, f"identifier values leaked into context strings: {leaked_values[:5]}"
    assert ctx["stops"]["drivers"]["total"] > 0


# ---------------------------------------------------------------------------
# 3. Empty / missing / corrupt feeds degrade gracefully
# ---------------------------------------------------------------------------


def test_missing_feed_files_yield_empty_summaries(tmp_path: Path):
    ctx = feeds_mod.safety_context(tmp_path)
    assert ctx["incidents"] == []
    assert ctx["stars"]["empty"] and ctx["stars"]["total"] == 0
    assert ctx["stops"]["drivers"]["empty"]
    assert ctx["stops"]["pedestrian"]["empty"]
    assert feeds_mod.vintage_of(tmp_path, "cfs_recent.json") == ""


def test_corrupt_feed_file_treated_as_empty(tmp_path: Path, caplog):
    (tmp_path / "cfs_recent.json").write_text("{not json", encoding="utf-8")
    with caplog.at_level("WARNING", logger="web.feeds"):
        items = feeds_mod.latest_incidents(tmp_path)
    assert items == []
    assert any("unreadable" in r.message for r in caplog.records)


def test_load_feed_edge_cases_never_raise(tmp_path: Path):
    (tmp_path / "cfs_recent.json").write_text("[1, 2]", encoding="utf-8")
    assert feeds_mod._load_feed(tmp_path, "cfs_recent.json")["rows"] == []
    (tmp_path / "cfs_recent.json").write_text(json.dumps({"rows": "nope"}), encoding="utf-8")
    assert feeds_mod._load_feed(tmp_path, "cfs_recent.json")["rows"] == []
    (tmp_path / "cfs_recent.json").write_text(json.dumps({}), encoding="utf-8")
    feed = feeds_mod._load_feed(tmp_path, "cfs_recent.json")
    assert feed["generated_utc"] == "" and feed["rows"] == []
    # Non-numeric row_count must not raise (the "never an exception" contract).
    payload = {"generated_utc": "2026-09-20T12:00:00Z", "row_count": "abc", "rows": [], "dataset_id": "t"}
    (tmp_path / "cfs_recent.json").write_text(json.dumps(payload), encoding="utf-8")
    assert feeds_mod._load_feed(tmp_path, "cfs_recent.json")["row_count"] == 0
    (tmp_path / "cfs_recent.json").write_text("{bad", encoding="utf-8")
    assert feeds_mod.vintage_of(tmp_path, "cfs_recent.json") == ""


def test_fatal_shooting_and_date_fallback(tmp_path: Path):
    _write_feed(
        tmp_path,
        "shootings_recent.json",
        [
            {"type": "FATAL", "dateoccurred": "09/18/2026",
             "streetblock": "X", "sna_neighborhood": "Y"},
        ],
    )
    items = feeds_mod.latest_incidents(tmp_path)
    assert items[0]["what"] == "Shooting — fatal"
    assert items[0]["when_display"] == "Sep 18, 2026"


def test_neighborhood_priority_and_casing():
    row = {
        "cpd_neighborhood": "  downtown  ",
        "community_council_neighborhood": "OTHER",
        "sna_neighborhood": "OTR",
    }
    assert feeds_mod._neighborhood_en(row) == "Downtown"
    assert feeds_mod._neighborhood_en({"sna_neighborhood": "college hill"}) == "College Hill"
    assert feeds_mod._neighborhood_en({}) == ""


def test_unparseable_timestamp_sorts_last_and_displays_raw(tmp_path: Path):
    _write_feed(
        tmp_path,
        "cfs_recent.json",
        [
            {"event_number": "E9", "incident_type_id": "TSTOP",
             "create_time_incident": "not-a-date", "address_x": "X", "cpd_neighborhood": "Y"},
            {"event_number": "E8", "incident_type_id": "TSTOP",
             "create_time_incident": "2026-09-19T08:00:00.000", "address_x": "X", "cpd_neighborhood": "Y"},
        ],
    )
    items = feeds_mod.latest_incidents(tmp_path)
    assert len(items) == 2
    assert items[0]["sort_key"] > items[1]["sort_key"]  # parseable first
    assert items[1]["when_display"] == "not-a-date"


# ---------------------------------------------------------------------------
# 4. Frozen / paused source labeling
# ---------------------------------------------------------------------------


def test_frozen_and_paused_sources_labeled():
    meta = feeds_mod.FEED_META
    assert meta["traffic_stops_drivers_recent.json"]["status"] == "frozen"
    assert meta["pedestrian_stops_recent.json"]["status"] == "frozen"
    assert meta["use_of_force_pdi_recent.json"]["status"] == "paused"
    for name in (
        "traffic_stops_drivers_recent.json",
        "pedestrian_stops_recent.json",
        "use_of_force_pdi_recent.json",
    ):
        assert meta[name]["status_note"], f"{name} needs a reader-facing status note"


# ---------------------------------------------------------------------------
# 5. Plain-English mapping coverage over the current pulls
# ---------------------------------------------------------------------------


def _distinct_raw_values(filename: str, column: str) -> set[str]:
    payload = json.loads((DATA / filename).read_text(encoding="utf-8"))
    values: set[str] = set()
    for r in payload.get("rows", []):
        v = r.get(column)
        if isinstance(v, str) and v.strip():
            values.add(v.strip())
    return values


def test_disposition_mapping_covers_current_pulls():
    """Every disposition code in today's pulls has an explicit translation.
    A new city code fails here so it gets translated instead of leaking raw."""
    uncovered: set[str] = set()
    for filename in ("cfs_recent.json", "cfs_pdi_recent.json"):
        for raw in _distinct_raw_values(filename, "disposition_text"):
            for part in [p.strip() for p in raw.split(",") if p.strip()]:
                if part not in feeds_mod._DISPOSITION_EN:
                    uncovered.add(f"{filename}: {part}")
    assert not uncovered, f"untranslated disposition codes: {sorted(uncovered)}"


def test_incident_type_normalization_properties():
    """The incident-type space (~180 CAD bases + suffixes) is normalized, not
    enumerated: every distinct raw value in today's pulls must come out as
    readable text with no CAD suffixes, no caller prefixes, and no all-caps
    codes. Spot-checks pin the important translations."""
    paren_re = re.compile(r"\([^)]*\)")
    for filename in ("cfs_recent.json", "cfs_pdi_recent.json"):
        for raw in _distinct_raw_values(filename, "incident_type_id"):
            out = feeds_mod._incident_type_en(raw)
            assert out, f"empty translation for {raw!r}"
            assert not paren_re.search(out), f"CAD suffix leaked for {raw!r}: {out!r}"
            assert out[0] not in "+=", f"prefix leaked for {raw!r}: {out!r}"
            assert not (out.isupper() and len(out) > 4), f"raw code leaked for {raw!r}: {out!r}"

    assert feeds_mod._incident_type_en("ASSAULT (JO)(W)(E)") == "Assault"
    assert feeds_mod._incident_type_en("+SHOTS FIRED - HEARD ONLY") == "Shots Fired - Heard Only"
    assert feeds_mod._incident_type_en("TSTOP") == "Traffic stop"
    assert feeds_mod._incident_type_en("BURG RESIDENTIAL (NIP)") == "Burglary Residential"
    assert feeds_mod._incident_type_en("QQ") == "Other police call"
    assert feeds_mod._incident_type_en("=CPD REQUEST BY FIRE") == "CPD Request By Fire"
    assert feeds_mod._incident_type_en("") == "Incident"


def test_compound_and_unknown_dispositions():
    assert feeds_mod._disposition_en("ARR: ARREST,SOW: SENT ON WAY") == "Arrest made; Sent on way"
    assert feeds_mod._disposition_en("XYZ: FOO") == "Xyz: Foo"
    assert feeds_mod._disposition_en("OH: OH") == "On hold"


@pytest.mark.parametrize("code, expected", sorted(feeds_mod._INCIDENT_ABBREV_EN.items()))
def test_incident_abbreviation_map_spot_checks(code: str, expected: str):
    """Every abbreviation entry is pinned: deleting one degrades the output
    to 'Other police call', which the property test cannot catch."""
    assert feeds_mod._incident_type_en(code) == expected


@pytest.mark.parametrize("word", sorted(feeds_mod._INCIDENT_ENGLISH_WORDS))
def test_incident_english_words_title_cased(word: str):
    assert feeds_mod._incident_type_en(word) == word.title()


def test_stars_category_mapping_covers_current_pulls():
    """Every STARS category in today's pulls has an explicit translation."""
    uncovered = {
        v for v in _distinct_raw_values("crime_stars_recent.json", "stars_category")
        if v not in feeds_mod._STARS_CATEGORY_EN
    }
    assert not uncovered, f"untranslated STARS categories: {sorted(uncovered)}"


def test_stars_type_mapping_covers_current_pulls():
    """Every STARS type in today's pulls has an explicit classification."""
    uncovered = {
        v for v in _distinct_raw_values("crime_stars_recent.json", "type")
        if v not in feeds_mod._STARS_TYPE_EN
    }
    assert not uncovered, f"untranslated STARS types: {sorted(uncovered)}"


def test_action_taken_mapping_covers_current_pulls():
    uncovered: set[str] = set()
    for filename in ("traffic_stops_drivers_recent.json", "pedestrian_stops_recent.json"):
        for raw in _distinct_raw_values(filename, "action_taken_cid"):
            if raw.strip().upper() not in feeds_mod._ACTION_TAKEN_EN:
                uncovered.add(f"{filename}: {raw}")
    assert not uncovered, f"untranslated action codes: {sorted(uncovered)}"


def test_no_raw_code_leaks_into_incident_text():
    """Translated incident rows must not contain SCREAMING_SNAKE codes."""
    code_re = re.compile(r"\b[A-Z]{2,}:[A-Z ]+\b")
    for item in feeds_mod.latest_incidents(DATA, n=60):
        assert not code_re.search(item["what"]), f"raw code leaked: {item['what']}"


# ---------------------------------------------------------------------------
# 6. Template renders under StrictUndefined
# ---------------------------------------------------------------------------


def _strict_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["base_url"] = ""
    env.globals["site_url"] = "https://www.aretheyinjail.com"
    env.globals["css_version"] = "test"
    env.globals["main_js_version"] = "test"
    env.globals["theme_js_version"] = "test"
    env.globals["human_utc"] = lambda s: s or "pending"
    env.globals["giscus"] = {"repo": "", "repo_id": "", "category": "", "category_id": ""}
    return env


def _strict_snapshot():
    # Production passes a Snapshot object with attribute access; mirror that.
    return SimpleNamespace(generated_utc="2026-09-20T00:00:00Z", inmate_count=1074)


def test_safety_template_renders_strict(fixture_dir: Path):
    env = _strict_env()
    ctx = feeds_mod.safety_context(fixture_dir)
    stamps = [feeds_mod.vintage_of(fixture_dir, f) for f in (
        "cfs_recent.json", "cfs_pdi_recent.json", "shootings_recent.json", "crime_stars_recent.json")]
    # Mirror production's expression exactly (web/pages.py): same contract.
    html = env.get_template("safety.html").render(
        snapshot=_strict_snapshot(),
        incidents=ctx["incidents"],
        stars=ctx["stars"],
        stops=ctx["stops"],
        newest_vintage=max(stamps) if stamps else "",
    )
    assert "Community safety" in html
    assert "Source frozen." in html  # frozen banner rendered
    assert "Warning, no citation" in html
    assert "Aggravated assault" in html
    assert "301:" not in html  # no raw disposition codes


def test_live_feed_renders_no_frozen_banner(fixture_dir: Path, monkeypatch):
    for name in ("traffic_stops_drivers_recent.json", "pedestrian_stops_recent.json"):
        meta = dict(feeds_mod.FEED_META[name])
        meta["status"] = "live"
        monkeypatch.setitem(feeds_mod.FEED_META, name, meta)
    env = _strict_env()
    ctx = feeds_mod.safety_context(fixture_dir)
    html = env.get_template("safety.html").render(
        snapshot=_strict_snapshot(),
        incidents=ctx["incidents"],
        stars=ctx["stars"],
        stops=ctx["stops"],
        newest_vintage="2026-09-20T12:00:00Z",
    )
    assert "Source frozen." not in html


def test_safety_template_renders_empty_gracefully(tmp_path: Path):
    env = _strict_env()
    ctx = feeds_mod.safety_context(tmp_path)
    html = env.get_template("safety.html").render(
        snapshot=SimpleNamespace(generated_utc="", inmate_count=0),
        incidents=ctx["incidents"],
        stars=ctx["stars"],
        stops=ctx["stops"],
        newest_vintage="",
    )
    assert "No incident data in this pull." in html
    assert "No reported-crime data in this pull." in html
    assert "No stop data in this pull." in html
