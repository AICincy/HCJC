"""Tests for the live-HTML freshness gate. No network: the probe fetch is
monkeypatched, so the stamp extraction, the lag decision, and the fail-closed
behavior (missing stamp, stale deploy, broken live tree) are exercised
against fixture pages."""

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

from scripts import verify_live_html_freshness as freshness

VINTAGE = "2026-09-23T19:35:00Z"

PAGE_HTML = (
    "<!doctype html><html><head><meta charset=\"utf-8\">"
    "<meta name=\"jcstream:generated-utc\" content=\"{stamp}\">"
    "</head><body><span>Generated</span></body></html>"
)


def _page(stamp: str | None) -> str:
    if stamp is None:
        return "<!doctype html><html><head><title>old deploy</title></head><body></body></html>"
    return PAGE_HTML.replace("{stamp}", stamp)


def _setup(
    tmp_path: Path,
    monkeypatch,
    live,
    *,
    candidate_stamp: str | None = VINTAGE,
    repo_stamp: str = VINTAGE,
    pages: tuple[str, ...] = ("index.html",),
    extra_argv: tuple[str, ...] = (),
) -> None:
    """Write a tip data file + candidate page tree, patch the probe fetch,
    and point argv at the fixture tree. ``live`` maps a page path to either a
    ``(status, content_type, body_bytes)`` tuple or an Exception to raise."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "current.json").write_text(
        json.dumps({"generated_utc": repo_stamp, "inmate_count": 0, "inmates": []}),
        encoding="utf-8",
    )
    for page in pages:
        page_path = tmp_path / "docs" / page
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(_page(candidate_stamp), encoding="utf-8")

    def fake_fetch(url, timeout):
        page = url[len("https://example.test/") :]
        result = live[page]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(freshness, "fetch", fake_fetch)
    argv = [freshness.__file__, "--site", "https://example.test"]
    for page in pages:
        argv += ["--page", page]
    argv += [
        "--local",
        str(tmp_path / "docs"),
        "--data",
        str(tmp_path / "data" / "current.json"),
        *extra_argv,
    ]
    monkeypatch.setattr(sys, "argv", argv)


def _live(stamp: str | None = VINTAGE):
    return (200, "text/html; charset=utf-8", _page(stamp).encode())


def test_fresh_live_passes(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()})
    assert freshness.main() == 0
    out = capsys.readouterr().out
    assert "live HTML freshness OK" in out
    assert "lag 0.00 h" in out


def test_lag_within_tolerance_passes(tmp_path, monkeypatch, capsys):
    # Sweeps are hourly with observed multi-hour cron gaps: a lag inside the
    # budget is healthy, not stale.
    older = "2026-09-23T13:35:00Z"  # 6 h behind the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 0
    assert "live HTML freshness OK" in capsys.readouterr().out


def test_lag_exactly_at_budget_passes(tmp_path, monkeypatch, capsys):
    # Boundary: lag == --max-lag-hours is within budget (strictly greater fails).
    older = "2026-09-22T17:35:00Z"  # exactly 26 h behind
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 0


def test_stale_live_fails(tmp_path, monkeypatch, capsys):
    older = "2026-09-21T15:35:00Z"  # ~52 h behind the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "live HTML is stale" in out
    assert "::error title=Live HTML freshness::" in out
    assert "Pages deploy looks broken" in out


def test_live_missing_stamp_fails(tmp_path, monkeypatch, capsys):
    # A tree deployed before the stamp rollout has no marker; once the stamp
    # has shipped this is a stale deploy by definition, so fail closed.
    _setup(tmp_path, monkeypatch, {"index.html": _live(None)})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "no jcstream:generated-utc stamp" in out
    assert "recovery" not in out.lower() or "no recovery" in out.lower()


def test_live_404_fails(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": HTTPError("https://example.test/index.html", 404, "Not Found", {}, None)},
    )
    assert freshness.main() == 1
    assert "HTTP 404" in capsys.readouterr().out


def test_live_500_fails(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": HTTPError("https://example.test/index.html", 500, "Server Error", {}, None)},
    )
    assert freshness.main() == 1


def test_live_unreachable_fails(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"index.html": URLError("connection reset")})
    assert freshness.main() == 1


def test_live_non_html_content_type_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": (200, "application/json", b"{}")})
    assert freshness.main() == 1
    assert "unexpected content type" in capsys.readouterr().out


def test_live_malformed_stamp_fails(tmp_path, monkeypatch, capsys):
    # A tampered or corrupt stamp must not parse into a bogus lag decision.
    _setup(tmp_path, monkeypatch, {"index.html": _live("Sep 23, 2026, 7:35 PM ET")})
    assert freshness.main() == 1
    assert "malformed" in capsys.readouterr().out


def test_candidate_missing_stamp_fails(tmp_path, monkeypatch, capsys):
    # A build/template regression that drops the stamp must fail the gate,
    # not silently compare nothing.
    _setup(tmp_path, monkeypatch, {"index.html": _live()}, candidate_stamp=None)
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "no jcstream:generated-utc stamp" in out
    assert "build/template" in out


def test_candidate_vintage_mismatch_fails(tmp_path, monkeypatch, capsys):
    # The candidate must be built from the tip's data, not a stale checkout.
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live()},
        candidate_stamp="2026-09-01T00:00:00Z",
    )
    assert freshness.main() == 1
    assert "candidate vintage" in capsys.readouterr().out


def test_live_newer_than_tip_warns_but_passes(tmp_path, monkeypatch, capsys):
    # A checkout that lagged the last deploy sees a newer live tree; that is
    # not a stale site, so warn and pass.
    newer = "2026-09-23T21:35:00Z"  # 2 h ahead of the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(newer)})
    assert freshness.main() == 0
    out = capsys.readouterr().out
    assert "::warning title=Live HTML freshness::" in out
    assert "newer than the tip vintage" in out


def test_unreadable_tip_data_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()}, repo_stamp="")
    (tmp_path / "data" / "current.json").write_text('{"generated_utc": 5}', encoding="utf-8")
    assert freshness.main() == 1
    assert "cannot read tip vintage" in capsys.readouterr().out


def test_tip_data_missing_stamp_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()})
    (tmp_path / "data" / "current.json").write_text('{"inmate_count": 0}', encoding="utf-8")
    assert freshness.main() == 1
    assert "cannot read tip vintage" in capsys.readouterr().out


def test_missing_candidate_file_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()}, pages=("index.html",))
    (tmp_path / "docs" / "index.html").unlink()
    assert freshness.main() == 1
    assert "candidate build unreadable" in capsys.readouterr().out


def test_multi_page_any_stale_fails(tmp_path, monkeypatch, capsys):
    pages = ("index.html", "help/index.html")
    older = "2026-09-20T15:35:00Z"
    live = {"index.html": _live(), "help/index.html": _live(older)}
    _setup(tmp_path, monkeypatch, live, pages=pages)
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "/help/index.html" in out
    assert "2 error(s)" not in out  # only the stale page errors; index passes
    assert "1 error(s)" in out


def test_extract_vintage_handles_absent_and_empty():
    assert freshness.extract_vintage(_page(VINTAGE)) == VINTAGE
    assert freshness.extract_vintage(_page(None)) is None
    assert freshness.extract_vintage(_page(VINTAGE).replace(VINTAGE, "")) is None
    assert freshness.extract_vintage("") is None


def test_parse_stamp_rejects_non_iso_shapes():
    for bad in ("Sep 23, 2026, 7:35 PM ET", "2026-09-23T19:35:00", "2026-09-23 19:35:00Z", ""):
        try:
            freshness.parse_stamp(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_stamp accepted {bad!r}")
