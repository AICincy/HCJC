"""CRA (Consumer Reporting Agency) boundary invariant tests.

JCStream does not furnish consumer reports and is not offered as a consumer
reporting agency as those terms are defined in 15 U.S.C. 1681a(d) and
1681a(f); use of the site as a factor in eligibility for credit, insurance,
employment, housing, tenant screening, or any other purpose described in
15 U.S.C. 1681b is prohibited by the site's legal notice. FCRA coverage is
determined by those statutory definitions, not by the notice.
These tests enforce the compliance boundary by verifying that:

1. Every rendered page carries <meta name="robots" content="noindex"> to prevent
   search-engine indexing of individual records.
2. robots.txt contains "Disallow: /" so compliant crawlers don't index.
3. The FCRA disclaimer (15 U.S.C. 1681a(d)/(f), 1681b) is present in the visit/data template.
4. The "presumed innocent" disclaimer appears in all individual-facing templates.
5. The /archive/ endpoint is a paginated view of the current custody mirror
   (not a historical record store) and carries the same CRA boundary markers
   as every other roster view.
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
    assert "15 U.S.C. 1681a(d)" in html, "visit.html must contain the FCRA disclaimer (15 U.S.C. 1681a(d)/(f), 1681b)"


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


# --- 5. /archive/ is a mirror view, not a historical archive -----------------


def test_archive_endpoint_is_mirror_view():
    """The /archive/ page paginates the current custody mirror by booking
    month (owner decision 2026-09-22: keep /archive/). It must carry the same
    CRA boundary markers as every other roster view: noindex inherited from
    base.html, and the presumed-innocent disclaimer via the shared partial.
    It renders the live snapshot, not a separate historical record store."""
    html = _read_template("archive.html")
    assert '{% extends "base.html" %}' in html, "archive.html must inherit noindex from base.html"
    assert "_legal_disclosure.html" in html, "archive.html must include the presumed-innocent disclaimer partial"
    assert "snapshot" in html, "archive.html must render the current snapshot, not a historical store"
