"""CRA (Consumer Reporting Agency) boundary invariant tests.

JCStream is NOT a consumer reporting agency under the FCRA, 15 U.S.C. § 1681.
These tests enforce the compliance boundary by verifying that:

1. Every rendered page carries <meta name="robots" content="noindex"> to prevent
   search-engine indexing of individual records.
2. robots.txt contains "Disallow: /" so compliant crawlers don't index.
3. The FCRA disclaimer is present in the visit/data template.
4. The "presumed innocent" disclaimer appears in all individual-facing templates.
5. No historical archive endpoint exists (we mirror, not archive).
"""

from __future__ import annotations

from pathlib import Path

from web.outputs import _write_well_known

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


# --- 1. noindex meta tag ---------------------------------------------------


def test_base_template_has_noindex():
    html = _read_template("base.html")
    assert 'content="noindex' in html, "base.html must carry noindex meta tag"


# --- 2. robots.txt disallow -------------------------------------------------


def test_robots_txt_disallow_all(tmp_path):
    """The real _write_well_known generator must emit 'Disallow: /' in the
    robots.txt it writes (not just contain the string somewhere in source)."""
    _write_well_known(tmp_path, "https://www.aretheyinjail.com", "2026-06-15T12:00:00Z")
    robots = (tmp_path / "robots.txt").read_text(encoding="utf-8")
    assert "Disallow: /" in robots, "generated robots.txt must disallow all crawling"


# --- 3. FCRA disclaimer -----------------------------------------------------


def test_visit_template_has_fcra_disclaimer():
    html = _read_template("visit.html")
    assert "consumer reporting agency" in html.lower(), "visit.html must contain the FCRA disclaimer"


def test_data_template_has_presumed_innocent():
    html = _read_template("data.html")
    assert "presumed innocent" in html.lower(), "data.html must contain presumed-innocent language"


# --- 4. presumed-innocent disclaimer on individual-facing pages -------------


def test_index_has_presumed_innocent():
    html = _read_template("index.html")
    assert "presumed innocent" in html.lower()


def test_inmate_has_presumed_innocent():
    html = _read_template("inmate.html")
    assert "presumed innocent" in html.lower()


def test_court_has_presumed_innocent():
    html = _read_template("court.html")
    assert "presumed innocent" in html.lower()


def test_stats_has_presumed_innocent():
    html = _read_template("stats.html")
    assert "presumed innocent" in html.lower()


# --- 5. no historical archive -----------------------------------------------


def test_no_archive_endpoint():
    """No template named 'archive' should exist — we mirror, not archive."""
    archive_templates = list(TEMPLATE_DIR.glob("*archive*"))
    assert archive_templates == [], f"unexpected archive template(s): {archive_templates}"
