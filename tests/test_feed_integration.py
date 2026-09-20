"""Feed-integration regression tests (Option A, Phases 1+2, 2026-09-20).

Covers web/feeds.py and the safety page contract:
aggregation math, privacy (forbidden columns never reach a template context),
graceful empty-feed handling, frozen-source labeling, plain-English mapping
coverage over the current pulls, and a strict-Undefined render of
safety.html so template errors surface here instead of at build time.
"""

from __future__ import annotations

import json
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
    assert drivers["total"] == 4
    assert dict(drivers["by_race"]) == {"Black": 2, "White": 1, "Unknown": 1}
    assert dict(drivers["by_sex"]) == {"Male": 3, "Female": 1}
    assert dict(drivers["by_action"]) == {
        "Warning, no citation": 2,
        "Traffic citation": 1,
        "No action taken": 1,
    }
    # Race shares sum to 100%.
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
    assert stars["total"] == 3
    assert dict(stars["by_category"]) == {"Aggravated assault": 2, "Part 2": 1}
    assert stars["vintage"] == "2026-09-20T12:00:00Z"
    assert not stars["empty"]


def test_latest_incidents_sorted_and_deduped(fixture_dir: Path):
    items = feeds_mod.latest_incidents(fixture_dir, n=30)
    # 3 STARS + 1 deduped CFS + 1 shooting = 5
    assert len(items) == 5
    keys = [i["sort_key"] for i in items]
    assert keys == sorted(keys, reverse=True)
    assert items[0]["when_display"] == "Sep 19, 10:00 AM"
    cfs = next(i for i in items if "citation issued" in i["what"])
    assert cfs["when_display"] == "Sep 19, 8:00 AM"
    shooting = next(i for i in items if i["what"].startswith("Shooting"))
    assert shooting["when_display"] == "Sep 18, 11:15 PM"


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


def test_no_forbidden_columns_in_context(fixture_dir: Path):
    ctx = feeds_mod.safety_context(fixture_dir)
    keys = _all_keys(ctx)
    leaked = feeds_mod.FORBIDDEN_COLUMNS & keys
    assert not leaked, f"forbidden columns in template context: {leaked}"


def test_no_forbidden_columns_against_real_data():
    """Belt and braces on the real pulls: the module selects only the columns
    it needs, so even the full-size feeds must not leak identifiers."""
    ctx = feeds_mod.safety_context(DATA)
    keys = _all_keys(ctx)
    leaked = feeds_mod.FORBIDDEN_COLUMNS & keys
    assert not leaked, f"forbidden columns in template context: {leaked}"
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
    import re

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


def test_action_taken_mapping_covers_current_pulls():
    uncovered: set[str] = set()
    for filename in ("traffic_stops_drivers_recent.json", "pedestrian_stops_recent.json"):
        for raw in _distinct_raw_values(filename, "action_taken_cid"):
            if raw.strip().upper() not in feeds_mod._ACTION_TAKEN_EN:
                uncovered.add(f"{filename}: {raw}")
    assert not uncovered, f"untranslated action codes: {sorted(uncovered)}"


def test_no_raw_code_leaks_into_incident_text():
    """Translated incident rows must not contain SCREAMING_SNAKE codes."""
    import re

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
    html = env.get_template("safety.html").render(
        snapshot=_strict_snapshot(),
        incidents=ctx["incidents"],
        stars=ctx["stars"],
        stops=ctx["stops"],
        newest_vintage=max(s for s in stamps if s),
    )
    assert "Community safety" in html
    assert "Source frozen." in html  # frozen banner rendered
    assert "Warning, no citation" in html
    assert "Aggravated assault" in html
    assert "301:" not in html  # no raw disposition codes


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
    assert "No stop data in this pull." in html
