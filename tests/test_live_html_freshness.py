"""Tests for the live-HTML freshness gate.

No network is used: the probe fetch is monkeypatched, so the stamp extraction,
strict parsing, lag decision, multi-page policy, and fail-closed HTTP behavior
are exercised against fixture pages.  The cases intentionally mirror the
on-call stress matrix in ``audit-output/full-stack-live-parity-2026-09-24.md``.
"""

import json
import socket
import ssl
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
    """Write a tip data file + candidate page tree and patch the probe fetch.

    ``live`` maps a page path to either a ``(status, content_type, body_bytes)``
    tuple or an Exception to raise. This keeps every scenario deterministic.
    """
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
    older = "2026-09-23T13:35:00Z"  # 6 h behind the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 0
    assert "live HTML freshness OK" in capsys.readouterr().out


def test_lag_exactly_at_budget_passes(tmp_path, monkeypatch):
    # Boundary policy: lag == --max-lag-hours is within budget; strictly
    # greater than the threshold fails.
    older = "2026-09-22T17:35:00Z"  # exactly 26 h behind
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 0


def test_lag_just_inside_budget_with_microseconds_passes(tmp_path, monkeypatch, capsys):
    repo = "2026-09-24T00:00:00.000000Z"
    live = "2026-09-22T22:00:00.036000Z"  # 25.99999 h behind
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live(live)},
        repo_stamp=repo,
        candidate_stamp=repo,
    )
    assert freshness.main() == 0
    assert "live HTML freshness OK" in capsys.readouterr().out


def test_lag_just_outside_budget_with_microseconds_fails(tmp_path, monkeypatch, capsys):
    repo = "2026-09-24T00:00:00.000000Z"
    live = "2026-09-22T21:59:59.964000Z"  # 26.00001 h behind
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live(live)},
        repo_stamp=repo,
        candidate_stamp=repo,
    )
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "26.00001 h" in out
    assert "live HTML is stale" in out


def test_stale_live_72_hours_fails_with_actionable_message(tmp_path, monkeypatch, capsys):
    older = "2026-09-20T19:35:00Z"  # 72 h behind the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(older)})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "live HTML is stale" in out
    assert "Pages deploy looks broken" in out


def test_live_one_hour_ahead_warns_by_default(tmp_path, monkeypatch, capsys):
    newer = "2026-09-23T20:35:00Z"  # one hour newer than the tip
    _setup(tmp_path, monkeypatch, {"index.html": _live(newer)})
    assert freshness.main() == 0
    out = capsys.readouterr().out
    assert "lag -1.00 h" in out
    assert "negative means live is newer" in out
    assert "::warning title=Live HTML freshness::" in out


def test_candidate_regression_fails_when_production_gate_is_strict(tmp_path, monkeypatch, capsys):
    # T1 is the candidate/tip vintage, T2 is live. The diagnostic default may
    # warn, but the production parity option must reject a regression.
    newer = "2026-09-23T20:35:00Z"
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live(newer)},
        extra_argv=("--fail-on-live-newer",),
    )
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "Candidate data vintage" in out
    assert "older than live data" in out
    assert "this rebuild would regress" in out


def test_live_missing_stamp_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live(None)})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "live tree lacks freshness stamp" in out
    assert "predates deployment" in out


def test_live_404_fails_with_domain_hint(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": HTTPError("https://example.test/index.html", 404, "Not Found", {}, None)},
    )
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "live tree returned 404" in out
    assert "domain/path or DNS" in out


def test_live_500_fails_with_health_hint(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": HTTPError("https://example.test/index.html", 500, "Server Error", {}, None)},
    )
    assert freshness.main() == 1
    assert "check server health" in capsys.readouterr().out


def test_live_unreachable_fails(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"index.html": URLError("connection reset")})
    assert freshness.main() == 1


def test_live_timeout_has_explicit_timeout_message(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": socket.timeout("timed out")})
    assert freshness.main() == 1
    assert "unresponsive (timeout)" in capsys.readouterr().out


def test_live_tls_failure_has_certificate_message(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": ssl.SSLCertVerificationError("certificate verify failed")})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "TLS verification failed" in out
    assert "certificate" in out.lower()


def test_live_non_html_content_type_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": (200, "application/json", b"{}")})
    assert freshness.main() == 1
    assert "Expected HTML" in capsys.readouterr().out


def test_live_redirect_fails_instead_of_following(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": HTTPError("https://example.test/index.html", 302, "Found", {}, None)},
    )
    assert freshness.main() == 1
    assert "redirect" in capsys.readouterr().out


def test_live_malformed_stamp_fails_and_identifies_value(tmp_path, monkeypatch, capsys):
    bad = "garbage"
    _setup(tmp_path, monkeypatch, {"index.html": _live(bad)})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "live vintage malformed" in out
    assert repr(bad) in out



def test_live_offset_stamp_is_rejected(tmp_path, monkeypatch, capsys):
    bad = "2026-09-23T23:35:42+05:30"
    _setup(tmp_path, monkeypatch, {"index.html": _live(bad)})
    assert freshness.main() == 1
    assert "strict ISO-8601 UTC stamp" in capsys.readouterr().out


def test_candidate_malformed_stamp_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()}, candidate_stamp="garbage")
    assert freshness.main() == 1
    assert "candidate vintage malformed" in capsys.readouterr().out


def test_candidate_missing_stamp_fails(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live()}, candidate_stamp=None)
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "no jcstream:generated-utc stamp" in out
    assert "build/template" in out


def test_candidate_vintage_mismatch_fails(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live()},
        candidate_stamp="2026-09-01T00:00:00Z",
    )
    assert freshness.main() == 1
    assert "candidate vintage" in capsys.readouterr().out


def test_live_newer_than_tip_warns_but_passes_without_strict_flag(tmp_path, monkeypatch, capsys):
    newer = "2026-09-23T21:35:00Z"  # 2 h ahead of the tip vintage
    _setup(tmp_path, monkeypatch, {"index.html": _live(newer)})
    assert freshness.main() == 0
    out = capsys.readouterr().out
    assert "::warning title=Live HTML freshness::" in out
    assert "newer than candidate/tip vintage" in out


def test_future_tampered_stamp_warns_only(tmp_path, monkeypatch, capsys):
    future = "2099-01-01T00:00:00Z"
    _setup(
        tmp_path,
        monkeypatch,
        {"index.html": _live(future)},
        extra_argv=("--fail-on-live-newer",),
    )
    assert freshness.main() == 0
    out = capsys.readouterr().out
    assert "suspiciously in the future" in out
    assert "::warning" in out


def test_epoch_stamp_fails_as_suspiciously_old(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, {"index.html": _live("1970-01-01T00:00:00Z")})
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "suspiciously old timestamp" in out
    assert "possible tampering or clock skew" in out


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
    pages = ("index.html", "help/index.html", "stats/index.html")
    older = "2026-09-20T15:35:00Z"
    live = {"index.html": _live(), "help/index.html": _live(older), "stats/index.html": _live()}
    _setup(tmp_path, monkeypatch, live, pages=pages)
    assert freshness.main() == 1
    out = capsys.readouterr().out
    assert "/help/index.html" in out
    assert "1 error(s)" in out


def test_marker_attribute_order_is_not_significant():
    html = '<meta content="2026-09-23T19:35:00Z" data-x="1" NAME="jcstream:generated-utc">'
    assert freshness.extract_vintage(html) == VINTAGE


def test_extract_vintage_handles_absent_and_empty():
    assert freshness.extract_vintage(_page(VINTAGE)) == VINTAGE
    assert freshness.extract_vintage(_page(None)) is None
    assert freshness.extract_vintage(_page(VINTAGE).replace(VINTAGE, "")) is None
    assert freshness.extract_vintage("") is None


def test_parse_stamp_accepts_microseconds_without_truncating():
    parsed = freshness.parse_stamp("2026-09-23T19:35:00.123456Z")
    assert parsed.microsecond == 123456


def test_parse_stamp_rejects_malformed_or_non_utc_shapes():
    for bad in (
        "Sep 23, 2026, 7:35 PM ET",
        "2026-09-23T19:35:00",
        "2026-09-23 19:35:00Z",
        "2026-09-23T19:35:00+05:30",
        "2026-13-45T99:99:99Z",
        "",
    ):
        try:
            freshness.parse_stamp(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_stamp accepted {bad!r}")
