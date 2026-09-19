from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper.models import Snapshot
from web.pages import _render_404_page, _render_data_page
from web.shape.common import _human_utc


def _env() -> Environment:
    templates = Path(__file__).resolve().parent.parent / "web" / "templates"
    env = Environment(
        loader=FileSystemLoader(templates),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["base_url"] = ""
    env.globals["site_url"] = "https://www.aretheyinjail.com"
    env.globals["css_version"] = "test"
    env.globals["main_js_version"] = "test"
    # data.html/base.html render timestamps through human_utc; reuse the real
    # helper so the footer renders exactly as in production.
    env.globals["human_utc"] = _human_utc
    # data.html documents the roster-freeze posture via roster_stale; the
    # real build registers this from _roster_stale_context(). A static stub
    # keeps this render unit test hermetic (no read of the real evidence log).
    env.globals["roster_stale"] = {
        "blocked": False,
        "since": None,
        "ever_blocked": False,
        "last_updated": "",
    }
    return env


def test_render_404_is_branded_jcstream(tmp_path: Path):
    _render_404_page(_env(), tmp_path)
    html = (tmp_path / "404.html").read_text(encoding="utf-8")
    assert "Page not found" in html
    assert "Search the roster" in html
    assert "JCStream" in html
    assert "GitHub Pages" not in html
    assert 'rel="icon"' in html
    assert 'id="lb-img"' in html
    assert '<img id="lb-img" src=""' not in html


def test_empty_courtclerk_cases_is_published(tmp_path: Path):
    snapshot = Snapshot(generated_utc="2026-08-16T15:00:00Z", inmate_count=0, inmates=[])
    # A render failure is a real failure: no broad swallow. _render_data_page
    # writes courtclerk_cases.json before rendering data.html, so a masked
    # template error used to pass on the JSON write alone.
    _render_data_page(_env(), snapshot, tmp_path)
    cases = tmp_path / "data" / "courtclerk_cases.json"
    assert cases.is_file()
    assert '"cases"' in cases.read_text(encoding="utf-8")
