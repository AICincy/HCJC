"""Ingested courtclerk records must reach the matching inmate page.

scraper.ingest_issue.save_cases writes the canonical {"cases": [...]}
envelope (the published /data/courtclerk_cases.json contract), but
web.pages._load_crowdsourced_cases only accepted a bare list, so every
ingested record was published as JSON yet never rendered on an inmate page.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from scraper.ingest_dispatch import sections_from_inputs
from scraper.ingest_issue import build_case_record
from scraper.models import Charge, Inmate, Snapshot
from web import pages
from web.build import _build_env

SOURCE = "https://www.courtclerk.org/data/case_summary.php?casenumber=B%2024%201234"


def _record() -> dict:
    inputs = {
        "case_number": "B 24 1234",
        "defendant_name": "DOE, JOHN",
        "defendant_dob": "01/15/1985",
        "judge": "Hon. Jane Roe",
        "charges": "2903.11 Felonious assault",
        "next_hearing": "06/02/2026",
        "disposition": "Bound over to grand jury",
        "source_url": SOURCE,
        "confirm_own_browser": "true",
        "confirm_verbatim": "true",
    }
    return build_case_record(sections_from_inputs(inputs), 0, "", "AICincy")


@pytest.fixture
def site(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr("web.feeds.DATA_DIR", data_dir)
    inmates = [
        Inmate(inmate_number="111", first_name="JOHN", last_name="DOE", date_of_birth="1/15/1985",
               booking_date="9/20/26", charges=[Charge(description="FELONIOUS ASSAULT F2", orc_code="2903.11")]),
        Inmate(inmate_number="222", first_name="MARY", last_name="POE", date_of_birth="2/2/1990",
               booking_date="9/20/26", charges=[Charge(description="THEFT M1", orc_code="2913.02")]),
    ]
    snapshot = Snapshot(generated_utc="2026-09-22T12:00:00Z", inmate_count=len(inmates), inmates=inmates)
    env = _build_env(snapshot, {}, "", "https://example.test")

    def render(payload) -> dict[str, HTMLParser]:
        (data_dir / "courtclerk_cases.json").write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "out"
        pages._render_inmates(env, snapshot, {}, [], out)
        return {n: HTMLParser((out / "inmate" / n / "index.html").read_text(encoding="utf-8")) for n in ("111", "222")}

    return snapshot, render


def test_envelope_record_renders_on_matching_inmate_page(site):
    _, render = site
    html = render({"cases": [_record()]})
    block = html["111"].css_first("aside.crowdsource-block")
    assert block is not None, "envelope-shaped record did not render"
    text = block.text()
    assert "Case # B 24 1234" in text
    assert "Hon. Jane Roe" in text
    assert "Bound over to grand jury" in text
    assert "@AICincy" in text
    links = [a.attributes.get("href") for a in block.css("a")]
    assert SOURCE in links
    assert "" not in links, "empty issue_url must not render as an href"
    assert html["222"].css_first("aside.crowdsource-block") is None


def test_envelope_loader_matches_and_bare_list_still_accepted(site):
    snapshot, _ = site
    data = Path(pages.feeds_mod.DATA_DIR) / "courtclerk_cases.json"
    for payload in ({"cases": [_record()]}, [_record()]):
        data.write_text(json.dumps(payload), encoding="utf-8")
        loaded = pages._load_crowdsourced_cases(snapshot.inmates)
        assert list(loaded) == ["111"]
        assert loaded["111"][0]["case_number"] == "B 24 1234"
        assert loaded["111"][0]["dob_verified"] is True


@pytest.mark.parametrize("payload", [{"cases": []}, {"cases": "nope"}, {"other": []}, {}, "x", 7])
def test_empty_or_malformed_payload_renders_nothing(site, payload):
    snapshot, render = site
    assert render(payload)["111"].css_first("aside.crowdsource-block") is None
    assert pages._load_crowdsourced_cases(snapshot.inmates) == {}
