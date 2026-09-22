"""Regression gates for the two 2026-09-22 UI audits, without live data."""
import hashlib
import json
import re
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from scraper.models import Charge, Inmate, Snapshot
from web.build import _build_env
from web.outputs import _copy_static, _write_search_json
from web.pages import IndexContext, _homepage_slice, _render_archive_page, _render_index

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def roster():
    inmates = [Inmate(inmate_number=str(i), first_name="TEST", last_name=f"PERSON{i}",
                      booking_date="9/20/26", charges=[Charge(description="Example F2", orc_code="2903.11")])
               for i in range(65)]
    snapshot = Snapshot(generated_utc="2026-09-22T12:00:00Z", inmate_count=len(inmates), inmates=inmates)
    return snapshot, _build_env(snapshot, {}, "/prefix", "https://example.test")


def test_homepage_slice_caps_total_without_mutating_groups():
    groups = [("September", list(range(30))), ("August", list(range(40))), ("July", [1])]
    assert _homepage_slice(groups) == [("September", list(range(30))), ("August", list(range(18)))]
    assert len(groups[1][1]) == 40
    assert _homepage_slice([]) == []
    assert _homepage_slice([("Empty", [])]) == []


def test_homepage_bound_archive_complete_and_prefix_safe(tmp_path, roster):
    snapshot, env = roster
    groups = [("September 2026", snapshot.inmates)]
    ctx = IndexContext(snapshot, groups, [], set(), 0, 0, {}, [], [], 0)
    _render_index(env, ctx, tmp_path)
    _render_archive_page(env, snapshot, groups, [], tmp_path)
    home = HTMLParser((tmp_path / "index.html").read_text())
    archive = HTMLParser((tmp_path / "archive/index.html").read_text())
    assert len(home.css(".card-inmate")) == 48
    assert len(archive.css(".card-inmate")) == 65
    form = home.css_first("form[data-roster-preview]")
    assert form.attributes["action"] == "/prefix/archive/"
    assert form.css_first('input[name="q"]')
    assert "17 more bookings" in home.text()
    assert not home.css(".masthead-seal")
    assert "not a government site" in home.text()
    assert not archive.css("[data-roster-preview]")


def test_search_index_includes_records_outside_preview_and_all_charges(tmp_path, roster):
    snapshot, _ = roster
    snapshot.inmates[-1].charges.append(Charge(description="SECOND CHARGE", orc_code="2925.11"))
    _write_search_json(tmp_path, snapshot, {})
    rows = json.loads((tmp_path / "search.json").read_text())["rows"]
    assert len(rows) == 65
    assert "second charge" in rows[-1]["s"]
    assert "2925.11" in rows[-1]["s"]
    assert "2903.11" in rows[-1]["s"]


def test_fold_stylesheet_is_content_versioned(roster):
    _, env = roster
    expected = hashlib.sha256((ROOT / "web/static/fold-chrome.css").read_bytes()).hexdigest()[:10]
    assert env.globals["fold_css_version"] == expected
    assert "fold_css_version" in (ROOT / "web/templates/base.html").read_text()


def test_published_fonts_are_exactly_the_referenced_fonts(tmp_path):
    _copy_static(tmp_path)
    css = (ROOT / "web/static/style.css").read_text()
    referenced = set(re.findall(r'/static/fonts/([^"\)]+\.woff2)', css))
    assert {p.name for p in (tmp_path / "static/fonts").glob("*.woff2")} == referenced


def test_strip_and_judge_contracts():
    roster = (ROOT / "web/templates/_roster_tool.html").read_text()
    assert 'role="img" aria-label="Roster by most serious degree:' in roster
    assert 'Select a color' not in roster
    assert 'class="legend" aria-hidden="true"' not in roster
    assert '.tier-strip-seg' not in (ROOT / "web/static/main.js").read_text()
    assert 'Profile for {{ judge.name }}' in (ROOT / "web/templates/judges.html").read_text()


def test_stackable_table_labels_and_legal_notice(roster):
    snapshot, env = roster
    html = env.get_template("inmate.html").render(inmate=snapshot.inmates[0], snapshot=snapshot,
                                                  cfs_matches=[], inmate_events=[], crowdsourced_for_inmate=[])
    dom = HTMLParser(html)
    table = dom.css_first("table.stackable")
    assert table.attributes["role"] == "table"
    assert [td.attributes["data-label"] for td in table.css("tbody td")] == [
        "ORC", "Description", "Charge level", "Court date", "Bond", "Disposition", "Case #"]
    assert all(td.css_first(".cell-value") for td in table.css("tbody td"))
    assert "15 U.S.C. 1681b" in dom.css_first(".record-legal").text()
    assert "legally presumed innocent" in dom.css_first(".inmate-hero .alert").text()
    assert dom.css_first(".record-legal").parent.tag != "details"


def _tokens(theme):
    sheets = [(ROOT / "web/static" / name).read_text() for name in ("style.css", "fold-chrome.css")]
    tokens = {}
    # Root declarations before theme declarations mirrors their specificity.
    selectors = [r"^:root\s*\{(.*?)\}"]
    if theme == "dark":
        selectors.append(r'^:root\[data-theme="dark"\]\s*\{(.*?)\}')
    for selector in selectors:
        for sheet in sheets:
            for block in re.findall(selector, sheet, re.S | re.M):
                tokens.update(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", block))
    return tokens


def _luminance(hex_color):
    rgb = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722), strict=True))


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("surface", ["--bg", "--bg-soft", "--surface", "--warn-bg", "--accent-bg"])
def test_normal_text_semantic_tokens_meet_aa(theme, surface):
    tokens = _tokens(theme)
    # Tokens used by the audited normal-text selectors, not decorative fills.
    text_tokens = ["--fg", "--fg-soft", "--fg-muted", "--fg-dim", "--link", "--cat-family"]
    text_tokens.append("--accent-text" if theme == "dark" else "--accent")
    for token in text_tokens:
        a, b = sorted((_luminance(tokens[token]), _luminance(tokens[surface])))
        assert (b + .05) / (a + .05) >= 4.5, (theme, token, surface)
