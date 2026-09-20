"""Tests for the detail-fetch failure taxonomy.

Covers the HCSO incident of 2026-09-19 (44 final detail failures: 7x HTTP
404, 37x HTTP 503): failure-mode classification, per-mode bounded retries,
list-authority minimal records, stale carry-forward, the systemic
degradation guard, and append-only empty-photo evidence dedup.
"""

from collections import Counter
from typing import Any, cast

import httpx
import pytest

from scraper import sweep
from scraper.models import Inmate, ListRow
from scraper.parsers import _record_empty_photo_event
from scraper.store import (
    append_block_evidence_deduped,
    load_block_log,
    verify_block_chain,
)
from scraper.sweep import (
    DETAIL_PATH,
    WafBackoffTracker,
    _fetch_detail_with_retry,
    _fetch_details,
    _fetch_one,
    _plan_detail_fetch,
    _record_detail_degraded,
    _record_detail_page_block,
)
from scraper.sweep_guards import (
    DETAIL_DEGRADED_MAX_FAILURE_FRACTION,
    DETAIL_DEGRADED_MIN_SAMPLE,
    DetailFailureMode,
    check_detail_degraded,
    classify_detail_html,
    classify_http_status_error,
)

DETAIL_URL = "https://www.hcso.org" + DETAIL_PATH + "?id=1"


def _named_html(inmate_id: str = "1234567", pad: int = 5500) -> str:
    """A realistic-size detail page that parses to a named inmate."""
    return f"<html><body><h1>DOE, JOHN</h1><ul><li>Inmate Number : {inmate_id}</li></ul></body></html>" + (" " * pad)


def _empty_inmate(inmate_id: str = "1") -> Inmate:
    return Inmate(inmate_number=inmate_id, last_name="", first_name="", booking_date="", charges=[])


def _named_inmate(inmate_id: str = "1") -> Inmate:
    return Inmate(inmate_number=inmate_id, last_name="DOE", first_name="JOHN", booking_date="5/1/26")


class _FakeHTTPResponse:
    def __init__(self, text: str = "", status_code: int = 200, url: str = DETAIL_URL):
        self.text = text
        self.status_code = status_code
        self.url = url


class _ScriptClient:
    """Fake HcsoClient.get_response playing a script of responses/exceptions."""

    def __init__(self, script: list):
        self._script = list(script)
        self.calls = 0

    def get_response(self, path, params=None):
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://www.hcso.org/detail?id=1")
    resp = httpx.Response(status_code, request=req)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=req, response=resp)


def _timeout() -> httpx.ReadTimeout:
    return httpx.ReadTimeout("timed out", request=httpx.Request("GET", "https://www.hcso.org/detail?id=1"))


def _conn_error() -> httpx.ConnectError:
    return httpx.ConnectError("refused", request=httpx.Request("GET", "https://www.hcso.org/detail?id=1"))


def _no_sleep(monkeypatch):
    monkeypatch.setattr(sweep.time, "sleep", lambda _s: None)


# ---------------------------------------------------------------------------
# classify_detail_html
# ---------------------------------------------------------------------------


def test_classify_zero_byte():
    mode = classify_detail_html("", _empty_inmate(), None, None, final_path=None, detail_path=DETAIL_PATH)
    assert mode == DetailFailureMode.ZERO_BYTE


def test_classify_waf_block_tiny_empty():
    html = "<html><body>Access Denied</body></html>"
    mode = classify_detail_html(html, _empty_inmate(), None, None, final_path=None, detail_path=DETAIL_PATH)
    assert mode == DetailFailureMode.WAF_BLOCK


def test_classify_truncated_tiny_named():
    # A tiny body that still parsed a name is a partial page, not a success:
    # accepting it would overwrite good charges/photo with empty values.
    html = "<html><body><h1>DOE, JOHN</h1></body></html>"
    mode = classify_detail_html(html, _named_inmate(), None, None, final_path=None, detail_path=DETAIL_PATH)
    assert mode == DetailFailureMode.TRUNCATED


def test_classify_redirect_wrong_path():
    mode = classify_detail_html(
        _named_html(),
        _named_inmate(),
        None,
        None,
        final_path="/somewhere-else/",
        detail_path=DETAIL_PATH,
    )
    assert mode == DetailFailureMode.REDIRECT


def test_classify_redirect_beats_tiny_body():
    # A redirect to an unexpected path is a redirect even when the body is
    # small; path mismatch is the stronger signal.
    html = "<html><body>hi</body></html>"
    mode = classify_detail_html(
        html,
        _empty_inmate(),
        None,
        None,
        final_path="/captcha/",
        detail_path=DETAIL_PATH,
    )
    assert mode == DetailFailureMode.REDIRECT


def test_classify_ok():
    mode = classify_detail_html(
        _named_html(),
        _named_inmate(),
        None,
        None,
        final_path=None,
        detail_path=DETAIL_PATH,
    )
    assert mode == DetailFailureMode.OK


def test_classify_ok_with_matching_path():
    mode = classify_detail_html(
        _named_html(),
        _named_inmate(),
        None,
        None,
        final_path=DETAIL_PATH,
        detail_path=DETAIL_PATH,
    )
    assert mode == DetailFailureMode.OK


# ---------------------------------------------------------------------------
# classify_http_status_error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected",
    [
        (404, DetailFailureMode.HTTP_404),
        (429, DetailFailureMode.HTTP_429),
        (500, DetailFailureMode.HTTP_5XX),
        (502, DetailFailureMode.HTTP_5XX),
        (503, DetailFailureMode.HTTP_5XX),
        (418, DetailFailureMode.ERROR),
        (None, DetailFailureMode.ERROR),
    ],
)
def test_classify_http_status(status, expected):
    assert classify_http_status_error(status) == expected


# ---------------------------------------------------------------------------
# _fetch_detail_with_retry: per-mode bounded retries
# ---------------------------------------------------------------------------


def test_retry_timeout_then_success(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_timeout(), _FakeHTTPResponse(_named_html())])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client), "1234567", previous={}, waf_tracker=WafBackoffTracker()
    )
    assert client.calls == 2
    assert outcome.mode == DetailFailureMode.OK
    assert inm is not None and inm.last_name == "DOE"


def test_retry_connection_error_then_success(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_conn_error(), _FakeHTTPResponse(_named_html())])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client), "1234567", previous={}, waf_tracker=WafBackoffTracker()
    )
    assert client.calls == 2
    assert outcome.mode == DetailFailureMode.OK
    assert inm is not None


def test_no_retry_on_404(tmp_path, monkeypatch):
    _no_sleep(monkeypatch)
    log_path = tmp_path / "waf_block_log.json"
    client = _ScriptClient([_http_status_error(404)])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client),
        "1234567",
        previous={},
        waf_tracker=WafBackoffTracker(),
        waf_block_log_path=log_path,
    )
    assert client.calls == 1  # 404 will not heal on retry
    assert outcome.mode == DetailFailureMode.HTTP_404
    assert outcome.http_status == 404
    assert inm is None
    # Evidence recorded with the failure mode.
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["failure_mode"] == "http_404"
    assert records[0]["http_status"] == 404
    assert verify_block_chain(records) == []


def test_no_retry_on_503(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_http_status_error(503)])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client), "1234567", previous={}, waf_tracker=WafBackoffTracker()
    )
    assert client.calls == 1
    assert outcome.mode == DetailFailureMode.HTTP_5XX
    assert inm is None


def test_zero_byte_retries_once_then_fails(tmp_path, monkeypatch):
    _no_sleep(monkeypatch)
    log_path = tmp_path / "waf_block_log.json"
    client = _ScriptClient([_FakeHTTPResponse(""), _FakeHTTPResponse("")])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client),
        "1234567",
        previous={},
        waf_tracker=WafBackoffTracker(),
        waf_block_log_path=log_path,
    )
    assert client.calls == 2
    assert outcome.mode == DetailFailureMode.ZERO_BYTE
    assert inm is None
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["failure_mode"] == "zero_byte"


def test_redirect_not_retried(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_FakeHTTPResponse(_named_html(), url="https://www.hcso.org/wrong/")])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client), "1234567", previous={}, waf_tracker=WafBackoffTracker()
    )
    assert client.calls == 1
    assert outcome.mode == DetailFailureMode.REDIRECT
    assert inm is None


def test_timeout_exhausted_records_evidence(tmp_path, monkeypatch):
    _no_sleep(monkeypatch)
    log_path = tmp_path / "waf_block_log.json"
    client = _ScriptClient([_timeout(), _timeout()])
    inm, _, _, outcome = _fetch_detail_with_retry(
        cast(Any, client),
        "1234567",
        previous={},
        waf_tracker=WafBackoffTracker(),
        waf_block_log_path=log_path,
    )
    assert client.calls == 2
    assert outcome.mode == DetailFailureMode.TIMEOUT
    assert inm is None
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["failure_mode"] == "timeout"


# ---------------------------------------------------------------------------
# _fetch_one: list authority and freshness marking
# ---------------------------------------------------------------------------


def test_fetch_one_new_inmate_404_with_list_row(monkeypatch):
    # List-page authority: a newly listed inmate whose detail 404s is kept
    # as a minimal record, marked stale, never dropped.
    _no_sleep(monkeypatch)
    client = _ScriptClient([_http_status_error(404)])
    list_row = ListRow(inmate_number="9990001", last_name="ROE", first_name="JANE", admit_date="5/12/26")
    inm, named, had_photo, outcome = _fetch_one(
        cast(Any, client),
        "9990001",
        previous={},
        list_row=list_row,
        waf_tracker=WafBackoffTracker(),
    )
    assert outcome.mode == DetailFailureMode.HTTP_404
    assert inm is not None
    assert inm.last_name == "ROE"
    assert inm.first_name == "JANE"
    assert inm.booking_date == "5/12/26"
    assert inm.detail_stale is True
    assert inm.last_detail_fetch_utc == ""
    assert named is False
    assert had_photo is False


def test_fetch_one_new_inmate_404_without_list_row_returns_none(monkeypatch):
    # Without a list row there is nothing authoritative to keep.
    _no_sleep(monkeypatch)
    client = _ScriptClient([_http_status_error(404)])
    inm, _, _, outcome = _fetch_one(
        cast(Any, client),
        "9990002",
        previous={},
        list_row=None,
        waf_tracker=WafBackoffTracker(),
    )
    assert outcome.mode == DetailFailureMode.HTTP_404
    assert inm is None


def test_fetch_one_known_inmate_503_returns_none_for_carry_forward(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_http_status_error(503)])
    prior = Inmate(inmate_number="7770001", last_name="DOE", first_name="JOHN", booking_date="5/1/26")
    inm, _, _, outcome = _fetch_one(
        cast(Any, client),
        "7770001",
        previous={"7770001": prior},
        list_row=None,
        waf_tracker=WafBackoffTracker(),
    )
    assert outcome.mode == DetailFailureMode.HTTP_5XX
    assert inm is None  # caller carries the previous-good record forward


def test_fetch_one_success_marks_fresh(monkeypatch):
    _no_sleep(monkeypatch)
    client = _ScriptClient([_FakeHTTPResponse(_named_html("1234567"))])
    inm, named, _, outcome = _fetch_one(
        cast(Any, client),
        "1234567",
        previous={},
        list_row=None,
        waf_tracker=WafBackoffTracker(),
    )
    assert outcome.mode == DetailFailureMode.OK
    assert inm is not None
    assert named is True
    assert inm.detail_stale is False
    assert inm.last_detail_fetch_utc != ""


# ---------------------------------------------------------------------------
# _fetch_details: stale carry-forward
# ---------------------------------------------------------------------------


def test_fetch_details_carries_forward_stale_on_failure(tmp_path, monkeypatch):
    _no_sleep(monkeypatch)
    log_path = tmp_path / "waf_block_log.json"
    client = _ScriptClient([_http_status_error(503)])
    prior = Inmate(
        inmate_number="7770002",
        last_name="DOE",
        first_name="JOHN",
        booking_date="5/1/26",
        photo_filename="7770002.jpg",
        last_detail_fetch_utc="2026-09-19T20:00:00Z",
    )
    current: dict[str, Inmate] = {}
    attempts, named, with_photo, failure_counts = _fetch_details(
        client=cast(Any, client),
        to_fetch=["7770002"],
        previous={"7770002": prior},
        current=current,
        row_by_id={},
        dry_run=True,
        waf_tracker=WafBackoffTracker(),
        current_path=tmp_path / "current.json",
        photos_dir=tmp_path,
        waf_block_log_path=log_path,
    )
    assert attempts == 1
    assert failure_counts["http_5xx"] == 1
    # The listed inmate is kept, previous-good bio/photo preserved, marked stale.
    assert "7770002" in current
    carried = current["7770002"]
    assert carried.last_name == "DOE"
    assert carried.photo_filename == "7770002.jpg"
    assert carried.detail_stale is True
    assert carried.last_seen_utc != ""


# ---------------------------------------------------------------------------
# check_detail_degraded: systemic failure signal
# ---------------------------------------------------------------------------


def test_degraded_guard_flags_incident_shape():
    # The 2026-09-19 incident: 44 final failures / 133 planned = 33% > 25%.
    assert check_detail_degraded(133, {"http_503": 37, "http_404": 7}) is True


def test_degraded_guard_quiet_below_threshold():
    assert check_detail_degraded(133, {"http_503": 5}) is False


def test_degraded_guard_ignores_small_sample():
    # 5/8 = 62% failures but below the minimum sample: not systemic evidence.
    assert check_detail_degraded(8, {"http_503": 5}) is False


def test_degraded_guard_empty():
    assert check_detail_degraded(0, {}) is False
    assert check_detail_degraded(100, {}) is False


def test_degraded_guard_boundary():
    # Exactly 25% is accepted (strict >); 26% trips.
    assert check_detail_degraded(100, {"http_503": 25}) is False
    assert check_detail_degraded(100, {"http_503": 26}) is True
    assert DETAIL_DEGRADED_MIN_SAMPLE == 10
    assert DETAIL_DEGRADED_MAX_FAILURE_FRACTION == 0.25


def test_record_detail_degraded_appends_evidence(tmp_path):
    log_path = tmp_path / "waf_block_log.json"
    _record_detail_degraded(133, Counter({"http_503": 37, "http_404": 7}), waf_block_log_path=log_path)
    records = load_block_log(log_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["event"] == "detail_degraded"
    assert rec["detail_attempts"] == 133
    assert rec["detail_failures"] == 44
    assert rec["failure_modes"] == {"http_404": 7, "http_503": 37}
    assert verify_block_chain(records) == []


# ---------------------------------------------------------------------------
# _plan_detail_fetch: stale records are retried next cycle
# ---------------------------------------------------------------------------


def test_plan_detail_fetch_retries_stale():
    stale = Inmate(
        inmate_number="1",
        last_name="DOE",
        first_name="J",
        booking_date="5/1/26",
        photo_filename="1.jpg",
        detail_stale=True,
    )
    fresh = Inmate(
        inmate_number="2",
        last_name="ROE",
        first_name="J",
        booking_date="5/1/26",
        photo_filename="2.jpg",
        detail_stale=False,
    )
    no_photo = Inmate(inmate_number="3", last_name="POE", first_name="J", booking_date="5/1/26")
    previous = {"1": stale, "2": fresh, "3": no_photo}
    to_fetch = _plan_detail_fetch({"1", "2", "3", "4"}, previous, refresh_known=False)
    assert "1" in to_fetch  # stale -> retried until a fetch succeeds
    assert "2" not in to_fetch  # fresh with photo -> skipped
    assert "3" in to_fetch  # no photo -> fetched
    assert "4" in to_fetch  # new -> fetched


# ---------------------------------------------------------------------------
# _plan_detail_fetch: rebooking forces a detail refetch (newest photo)
# ---------------------------------------------------------------------------


def _known_inmate(inmate_id, booking_date, **kw):
    base = dict(
        inmate_number=inmate_id,
        last_name="DOE",
        first_name="J",
        booking_date=booking_date,
        photo_filename=f"{inmate_id}.jpg",
        detail_stale=False,
    )
    base.update(kw)
    return Inmate(**base)


def _row(inmate_id, admit_date):
    return ListRow(inmate_number=inmate_id, last_name="DOE", first_name="J", admit_date=admit_date)


def test_plan_detail_fetch_refetches_on_rebooking():
    # Same inmate number, new admit date on the list page: HCSO rebooked the
    # person, so the detail page is refetched and the newest booking photo
    # replaces the prior booking's cached file.
    previous = {"1": _known_inmate("1", "5/1/26")}
    rows = {"1": _row("1", "9/20/2026")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id=rows) == ["1"]


def test_plan_detail_fetch_same_booking_not_refetched():
    previous = {"1": _known_inmate("1", "9/20/2026")}
    rows = {"1": _row("1", "9/20/2026")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id=rows) == []


def test_plan_detail_fetch_format_drift_not_rebooking():
    # Same day in different zero-padding must not look like a new booking.
    previous = {"1": _known_inmate("1", "9/20/26")}
    rows = {"1": _row("1", "09/20/2026")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id=rows) == []


def test_plan_detail_fetch_unparseable_dates_fail_safe():
    # Missing or unparseable dates never force a refetch: parser drift must
    # not be able to trigger a refetch storm.
    previous = {"1": _known_inmate("1", "")}
    rows = {"1": _row("1", "9/20/2026")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id=rows) == []
    previous = {"1": _known_inmate("1", "9/20/2026")}
    rows = {"1": _row("1", "not-a-date")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id=rows) == []


def test_plan_detail_fetch_missing_row_not_rebooking():
    previous = {"1": _known_inmate("1", "5/1/26")}
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False, row_by_id={}) == []
    assert _plan_detail_fetch({"1"}, previous, refresh_known=False) == []


def _make_jpeg(color) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (800, 1000), color=color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_rebooking_newest_photo_overwrites_cached(tmp_path):
    # The newest successfully decoded photo replaces the prior booking's file.
    photos_dir = tmp_path / "photos"
    old = _make_jpeg((200, 30, 30))
    from scraper.photos import downscale_and_save

    assert downscale_and_save(old, photos_dir / "1.jpg") is True
    before = (photos_dir / "1.jpg").read_bytes()

    inm = _known_inmate("1", "5/1/26")
    new = _make_jpeg((30, 30, 200))
    sweep._attach_photo_filename(inm, new, photos_dir)
    after = (photos_dir / "1.jpg").read_bytes()
    assert inm.photo_filename == "1.jpg"
    assert after != before  # newest photo replaced the cached one


def test_rebooking_corrupt_new_bytes_keep_cached_photo(tmp_path):
    # F-02 disposition lock-in: corrupt fresh bytes must not destroy a valid
    # cached photo; the prior booking's photo is preserved.
    photos_dir = tmp_path / "photos"
    from scraper.photos import downscale_and_save

    good = _make_jpeg((200, 30, 30))
    assert downscale_and_save(good, photos_dir / "1.jpg") is True
    before = (photos_dir / "1.jpg").read_bytes()

    inm = _known_inmate("1", "5/1/26")
    sweep._attach_photo_filename(inm, b"not an image", photos_dir)
    assert inm.photo_filename == "1.jpg"
    assert (photos_dir / "1.jpg").read_bytes() == before


# ---------------------------------------------------------------------------
# Empty-photo evidence dedup (append-only; history never rewritten)
# ---------------------------------------------------------------------------


def _empty_photo_record(inmate_id="1", field="booking_photo", ts="2026-09-20T02:00:00Z"):
    return {
        "event": "empty_photo_observed",
        "timestamp_utc": ts,
        "inmate_id": inmate_id,
        "photo_field_path": field,
        "payload_length": 0,
    }


def test_empty_photo_dedup_appends_first_observation(tmp_path):
    log_path = tmp_path / "waf_block_log.json"
    appended = append_block_evidence_deduped(
        _empty_photo_record(),
        log_path,
        dedupe_event="empty_photo_observed",
        dedupe_keys=("inmate_id", "photo_field_path"),
    )
    assert appended is True
    assert len(load_block_log(log_path)) == 1


def test_empty_photo_dedup_skips_repeat_within_window(tmp_path):
    log_path = tmp_path / "waf_block_log.json"

    def _append(record):
        return append_block_evidence_deduped(
            record,
            log_path,
            dedupe_event="empty_photo_observed",
            dedupe_keys=("inmate_id", "photo_field_path"),
        )

    assert _append(_empty_photo_record(ts="2026-09-20T02:00:00Z")) is True
    # Same inmate+field 15 minutes later: skipped, provenance is the first record.
    assert _append(_empty_photo_record(ts="2026-09-20T02:15:00Z")) is False
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["timestamp_utc"] == "2026-09-20T02:00:00Z"
    assert verify_block_chain(records) == []


def test_empty_photo_dedup_distinguishes_inmates_and_fields(tmp_path):
    log_path = tmp_path / "waf_block_log.json"

    def _append(record):
        return append_block_evidence_deduped(
            record,
            log_path,
            dedupe_event="empty_photo_observed",
            dedupe_keys=("inmate_id", "photo_field_path"),
        )

    assert _append(_empty_photo_record(inmate_id="1")) is True
    assert _append(_empty_photo_record(inmate_id="2")) is True
    assert _append(_empty_photo_record(inmate_id="1", field="other")) is True
    assert len(load_block_log(log_path)) == 3


def test_empty_photo_dedup_reappends_after_window(tmp_path):
    log_path = tmp_path / "waf_block_log.json"

    def _append(record):
        return append_block_evidence_deduped(
            record,
            log_path,
            dedupe_event="empty_photo_observed",
            dedupe_keys=("inmate_id", "photo_field_path"),
            dedupe_hours=24.0,
        )

    assert _append(_empty_photo_record(ts="2026-09-18T02:00:00Z")) is True
    # 48h later the window expired: a fresh anchor record is appended.
    assert _append(_empty_photo_record(ts="2026-09-20T02:00:00Z")) is True
    records = load_block_log(log_path)
    assert len(records) == 2
    assert verify_block_chain(records) == []


def test_record_empty_photo_event_dedups_via_parsers(tmp_path):
    # End to end through the parser hook: two identical observations in one
    # process collapse to a single hash-chained record.
    _record_empty_photo_event("42", "booking_photo", 0)
    _record_empty_photo_event("42", "booking_photo", 0)
    log_path = tmp_path / "waf_block_log.json"  # conftest redirects here
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["event"] == "empty_photo_observed"
    assert records[0]["inmate_id"] == "42"
    assert verify_block_chain(records) == []


def test_record_detail_page_block_dedupes_within_24h(tmp_path):
    # M-1: a stale inmate is refetched every cycle until its detail succeeds,
    # so repeated per-inmate failures within 24h collapse to one hash-chained
    # record. The per-cycle detail_degraded summary keeps the systemic signal.
    log_path = tmp_path / "waf_block_log.json"
    _record_detail_page_block(
        "1234567", 403, "<html>blocked</html>", DetailFailureMode.WAF_BLOCK, log_path
    )
    _record_detail_page_block(
        "1234567", 403, "<html>blocked</html>", DetailFailureMode.WAF_BLOCK, log_path
    )
    records = load_block_log(log_path)
    assert len(records) == 1
    assert records[0]["event"] == "detail_page_waf_block"
    assert records[0]["inmate_id"] == "1234567"
    assert verify_block_chain(records) == []
    # A different inmate or a different failure mode is a distinct observation.
    _record_detail_page_block(
        "7654321", 403, "<html>blocked</html>", DetailFailureMode.WAF_BLOCK, log_path
    )
    _record_detail_page_block(
        "1234567", 503, "<html>err</html>", DetailFailureMode.HTTP_5XX, log_path
    )
    assert len(load_block_log(log_path)) == 3
