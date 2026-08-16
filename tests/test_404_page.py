from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scraper.models import Snapshot
from web.pages import _render_404_page, _render_data_page


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
    try:
        _render_data_page(_env(), snapshot, tmp_path)
    except Exception:
        pass
    cases = tmp_path / "data" / "courtclerk_cases.json"
    assert cases.is_file()
    assert '"cases"' in cases.read_text(encoding="utf-8")
