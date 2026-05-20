"""Tests for the sweep health heuristic - the guard that stops a rate-limited
or partially-failed list sweep from being written as the live roster."""
import logging
from pathlib import Path

from scraper import sweep
from scraper.models import Inmate, ListRow
from scraper.sweep import _fetch_one
from scraper.sweep_guards import (
    check_detail_watchdog,
    sweep_looks_healthy as _sweep_looks_healthy,
)


# Old underscore alias is kept by sweep.py for back-compat; new code uses the
# public names from sweep_guards. The local rebinding keeps the existing test
# body unchanged below.
_check_detail_watchdog = check_detail_watchdog


def test_bootstrap_is_always_accepted():
    # First run (no prior data) and tiny datasets are trusted unconditionally.
    assert _sweep_looks_healthy(prev_count=0, seen_count=0, n_surnames=26, n_failed=0)
    assert _sweep_looks_healthy(prev_count=10, seen_count=2, n_surnames=26, n_failed=20)


def test_normal_sweeps_pass():
    # Roster grew a little, nothing failed.
    assert _sweep_looks_healthy(prev_count=1200, seen_count=1240, n_surnames=26, n_failed=0)
    # One letter errored, roster basically stable — still fine.
    assert _sweep_looks_healthy(prev_count=1200, seen_count=1185, n_surnames=26, n_failed=1)
    # Real churn: a meaningful drop but well above half.
    assert _sweep_looks_healthy(prev_count=1200, seen_count=1000, n_surnames=26, n_failed=0)


def test_too_many_failed_fetches_is_rejected():
    # 5 of 26 surname fetches errored (~19%) — don't trust this roster.
    assert not _sweep_looks_healthy(prev_count=1200, seen_count=1100, n_surnames=26, n_failed=5)


def test_collapsed_roster_is_rejected():
    # Fetches "succeeded" but came back with less than half the population.
    assert not _sweep_looks_healthy(prev_count=1200, seen_count=500, n_surnames=26, n_failed=0)
    assert not _sweep_looks_healthy(prev_count=1200, seen_count=0, n_surnames=26, n_failed=0)


def test_prune_photos_skips_when_most_would_disappear(tmp_path: Path, monkeypatch):
    photos = tmp_path / "photos"
    photos.mkdir()
    for i in range(10):
        (photos / f"{i}.jpg").write_bytes(b"x")
    monkeypatch.setattr(sweep, "PHOTOS_DIR", photos)
    # Active roster only includes one of the ten — 9/10 would be deleted, way
    # above the safety threshold.
    sweep._prune_photos({"0"})
    assert sum(1 for _ in photos.glob("*.jpg")) == 10, "anomaly guard should have skipped"


def test_prune_photos_removes_only_inactive(tmp_path: Path, monkeypatch):
    photos = tmp_path / "photos"
    photos.mkdir()
    for i in range(10):
        (photos / f"{i}.jpg").write_bytes(b"x")
    monkeypatch.setattr(sweep, "PHOTOS_DIR", photos)
    # Drop just two — well under the threshold.
    sweep._prune_photos({str(i) for i in range(10) if i not in (3, 7)})
    survivors = {p.stem for p in photos.glob("*.jpg")}
    assert survivors == {"0", "1", "2", "4", "5", "6", "8", "9"}


def test_watchdog_silent_below_min_sample(caplog):
    # tests-F1: with too few attempts the watchdog is silent regardless of
    # rates, so a tiny cycle doesn't trigger noisy false positives.
    caplog.set_level(logging.WARNING, logger="scraper.sweep")
    _check_detail_watchdog(attempts=5, named=0, with_photo=0)
    assert not any("detail watchdog" in r.message for r in caplog.records)


def test_watchdog_warns_on_low_name_rate(caplog):
    # tests-F1: at or above the min sample, a name-rate under the floor warns.
    caplog.set_level(logging.WARNING, logger="scraper.sweep")
    _check_detail_watchdog(attempts=20, named=5, with_photo=20)
    messages = [r.message for r in caplog.records]
    assert any("parsed a name" in m for m in messages), messages
    # Photo rate is fine; no photo warning expected.
    assert not any("yielded a photo" in m for m in messages), messages


def test_watchdog_warns_on_low_photo_rate(caplog):
    # tests-F1: at or above the min sample, a photo-rate under the floor warns.
    caplog.set_level(logging.WARNING, logger="scraper.sweep")
    _check_detail_watchdog(attempts=20, named=20, with_photo=5)
    messages = [r.message for r in caplog.records]
    assert any("yielded a photo" in m for m in messages), messages
    assert not any("parsed a name" in m for m in messages), messages


def test_watchdog_returns_true_for_warn_only_thresholds(caplog):
    # sweep-F4: WARN-only floors do NOT block writes. Below the BLOCK sample
    # the watchdog must still return True even when the WARN floors trip.
    caplog.set_level(logging.WARNING, logger="scraper.sweep")
    assert _check_detail_watchdog(attempts=20, named=5, with_photo=20) is True


def test_watchdog_blocks_when_large_sample_and_name_rate_collapsed(caplog):
    # sweep-F4: with at least DETAIL_WATCHDOG_BLOCK_MIN_SAMPLE attempts and
    # a name rate under DETAIL_WATCHDOG_BLOCK_NAME_FLOOR, refuse the write.
    caplog.set_level(logging.WARNING, logger="scraper.sweep")
    # 100 attempts, 30 named (30% < 60% block floor) -> block.
    assert _check_detail_watchdog(attempts=100, named=30, with_photo=100) is False
    assert any("BLOCK" in r.message for r in caplog.records)


def test_watchdog_does_not_block_below_block_sample():
    # sweep-F4: even a catastrophic name rate below DETAIL_WATCHDOG_BLOCK_
    # MIN_SAMPLE attempts must NOT block; the smaller sample isn't trusted.
    assert _check_detail_watchdog(attempts=50, named=0, with_photo=50) is True


class _FakeClient:
    """Stub HcsoClient.get that returns a fixed HTML string."""

    def __init__(self, html: str):
        self.html = html

    def get(self, path, params=None):
        return self.html


def test_fetch_one_uses_list_row_name_when_detail_heading_missing(tmp_path, monkeypatch):
    # tests-F2: a detail page whose heading drifted (no comma + all-caps,
    # no og:title, no <title>) must fall back to the list-row Last/First.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)
    html = "<html><body><h1>Some interstitial</h1></body></html>"
    client = _FakeClient(html)
    list_row = ListRow(
        inmate_number="9876543", last_name="ROE", first_name="JANE", admit_date="5/10/26"
    )
    inm, named, had_photo = _fetch_one(client, "9876543", previous={}, list_row=list_row)
    # detail parser produced no name, so detail_named must be False.
    assert named is False
    assert had_photo is False
    # list-row fallback rescued the name on the merged Inmate.
    assert inm is not None
    assert inm.last_name == "ROE"
    assert inm.first_name == "JANE"
    assert inm.booking_date == "5/10/26"


def test_fetch_one_carries_existing_photo_when_no_inline_image(tmp_path, monkeypatch):
    # tests-F2: when the detail page has no inline photo but we already have
    # one on disk from a prior cycle, keep showing the cached photo rather
    # than dropping the photo_filename to None.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)
    cached = tmp_path / "1234567.jpg"
    cached.write_bytes(b"\xff\xd8\xff\xe0cached-jpeg-bytes")
    html = (
        "<html><body><h1>DOE, JOHN</h1>"
        "<ul><li>Inmate Number : 1234567</li></ul></body></html>"
    )
    client = _FakeClient(html)
    inm, named, had_photo = _fetch_one(client, "1234567", previous={}, list_row=None)
    assert had_photo is False  # no inline image on the page
    assert inm is not None
    # carry-forward kicked in because the photo file existed on disk.
    assert inm.photo_filename == "1234567.jpg"


def test_fetch_one_falls_back_to_disk_when_pillow_rejects_bytes(tmp_path, monkeypatch):
    # Regression: if Pillow can't decode the bytes (downscale_and_save returns
    # False) but a previously-good photo is sitting on disk, we should NOT
    # drop the cached photo from the snapshot. The prior bug used an
    # `if photo_bytes: if downscale_and_save: set` outer-if that skipped the
    # disk-cached fallback `elif` whenever bytes were present-but-corrupt.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)
    cached = tmp_path / "5550000.jpg"
    cached.write_bytes(b"\xff\xd8\xff\xe0cached-jpeg-bytes")

    def _always_fail_downscale(raw, dest):
        return False  # simulate Pillow UnidentifiedImageError

    monkeypatch.setattr(sweep, "downscale_and_save", _always_fail_downscale)
    html = (
        '<html><body><h1>DOE, JOHN</h1>'
        '<ul><li>Inmate Number : 5550000</li></ul>'
        '<img src="data:image/png;base64,UExBQ0VIT0xERVI=" style="width:274px;">'
        '</body></html>'
    )
    client = _FakeClient(html)
    inm, _, had_photo = _fetch_one(client, "5550000", previous={}, list_row=None)
    assert had_photo is True  # detail parser found inline bytes
    assert inm is not None
    # Cached file on disk rescued the snapshot even though decode failed.
    assert inm.photo_filename == "5550000.jpg"


def test_fetch_one_returns_none_on_waf_blocked_response_for_known_inmate(tmp_path, monkeypatch):
    # Regression: HCSO's WAF returns a tiny truncated response (<5 KB) that
    # parses to an empty Inmate. For inmates already in `previous`, we should
    # return None so the carry-forward path in `run()` preserves the prior-
    # good record. For NEW inmates (not in previous), we still fall through
    # so the list_row fallback can rescue a name into a minimal Inmate.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)
    # Stub out the backoff sleep so the test doesn't actually wait 2-16s
    # for each WAF-block path. The retry loop itself is still exercised.
    monkeypatch.setattr(sweep.time, "sleep", lambda _s: None)
    sweep._reset_waf_block_streak_for_tests()
    tiny_blocked_html = "<html><body>Access Denied</body></html>"  # 41 bytes
    client = _FakeClient(tiny_blocked_html)

    # Known inmate (in previous): WAF block triggers carry-forward path.
    prior = Inmate(inmate_number="7770000", last_name="DOE", first_name="JOHN", booking_date="5/1/26")
    inm, named, had_photo = _fetch_one(client, "7770000", previous={"7770000": prior}, list_row=None)
    assert inm is None  # signals run() to carry forward from previous
    assert named is False
    assert had_photo is False

    # Unknown inmate (not in previous): list_row fallback still works.
    sweep._reset_waf_block_streak_for_tests()
    list_row = ListRow(
        inmate_number="8880000", last_name="ROE", first_name="JANE", admit_date="5/12/26"
    )
    inm, _, _ = _fetch_one(client, "8880000", previous={}, list_row=list_row)
    assert inm is not None  # falls through; list_row rescues the name
    assert inm.last_name == "ROE"


def test_fetch_one_retries_within_same_cycle_and_recovers_on_second_attempt(tmp_path, monkeypatch):
    # Regression: the same-cycle WAF-retry loop should call the client a
    # second time when the first response is WAF-block-shaped. If the
    # second attempt succeeds, the inmate is returned WITHOUT a carry-
    # forward, photo extraction runs normally, and the streak is reset.
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path)
    monkeypatch.setattr(sweep.time, "sleep", lambda _s: None)
    sweep._reset_waf_block_streak_for_tests()
    tiny = "<html><body>Access Denied</body></html>"
    full = (
        "<html><body><h1>DOE, JOHN</h1>"
        "<ul><li>Inmate Number : 6660000</li></ul></body></html>"
        + (" " * 5500)  # pad to clear the <5 KB WAF-block threshold
    )

    class _FlipClient:
        def __init__(self):
            self.calls = 0
        def get(self, path, params=None):
            self.calls += 1
            return tiny if self.calls == 1 else full

    client = _FlipClient()
    inm, named, _ = _fetch_one(client, "6660000", previous={}, list_row=None)
    assert client.calls == 2  # retry actually ran
    assert inm is not None
    assert inm.last_name == "DOE"
    assert named is True


def test_sweep_healthy_at_failure_fraction_boundary():
    # tests-F4: SWEEP_MAX_FAILED_FRACTION=0.10 uses strict `>`, so exactly
    # 10% must still be accepted. Anything strictly above is rejected.
    # 10/100 = 0.10 exactly -> True.
    assert _sweep_looks_healthy(prev_count=1000, seen_count=900, n_surnames=100, n_failed=10)
    # 11/100 = 0.11 > 0.10 -> False.
    assert not _sweep_looks_healthy(prev_count=1000, seen_count=900, n_surnames=100, n_failed=11)


def test_sweep_healthy_at_roster_fraction_boundary():
    # tests-F4: SWEEP_MIN_ROSTER_FRACTION=0.5 uses strict `<`, so exactly
    # half is still accepted; anything strictly below half is rejected.
    assert _sweep_looks_healthy(prev_count=1000, seen_count=500, n_surnames=26, n_failed=0)
    assert not _sweep_looks_healthy(prev_count=1000, seen_count=499, n_surnames=26, n_failed=0)


def test_sweep_bootstrap_floor_edge():
    # tests-F4: SWEEP_BOOTSTRAP_FLOOR=50 uses `<`, so prev_count below 50 is
    # bootstrap (accept anything). At 50 the regular guards kick in and a
    # tiny seen_count fails the roster-fraction check.
    assert _sweep_looks_healthy(prev_count=49, seen_count=0, n_surnames=26, n_failed=0)
    assert not _sweep_looks_healthy(prev_count=50, seen_count=0, n_surnames=26, n_failed=0)


def test_read_surnames_strips_utf8_bom(tmp_path: Path):
    # sweep-F7: a Windows editor saving data/surnames.txt prepends a BOM.
    # Without stripping it, the first surname becomes "﻿A", HCSO returns
    # zero rows, and no guard fires (one zero-row letter is below 10%).
    p = tmp_path / "surnames.txt"
    p.write_text("﻿A\nB\nC\n", encoding="utf-8")
    assert sweep._read_surnames(p) == ["A", "B", "C"]


def test_read_surnames_handles_comments_and_blanks(tmp_path: Path):
    p = tmp_path / "surnames.txt"
    p.write_text("# comment\nA\n\n  B  \n", encoding="utf-8")
    assert sweep._read_surnames(p) == ["A", "B"]


def test_interrupted_sweep_does_not_append_released_events(tmp_path: Path, monkeypatch):
    """sweep-F2: a KeyboardInterrupt mid-sweep must persist the partial
    snapshot but MUST NOT diff and emit synthetic 'released' events for
    every id the sweep never reached."""
    import json

    from scraper.models import Inmate

    # Pre-populate a previous snapshot with 60 inmates (above the 50 bootstrap
    # floor so the healthy guard actually evaluates fractions).
    previous_inmates = [
        Inmate(inmate_number=str(1000 + i), last_name="DOE", first_name=f"F{i}", booking_date="5/10/26")
        for i in range(60)
    ]
    current_path = tmp_path / "current.json"
    changelog_path = tmp_path / "changelog.json"
    photos = tmp_path / "photos"
    photos.mkdir()

    from scraper.store import save_current
    save_current(current_path, previous_inmates)

    monkeypatch.setattr(sweep, "CURRENT_PATH", current_path)
    monkeypatch.setattr(sweep, "CHANGELOG_PATH", changelog_path)
    monkeypatch.setattr(sweep, "PHOTOS_DIR", photos)

    # Stub HTTP layer so no network is touched. _sweep_list raising
    # KeyboardInterrupt simulates a runner cancellation mid-orchestration.
    def fake_sweep_list(client, surnames):
        raise KeyboardInterrupt()

    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(sweep, "_sweep_list", fake_sweep_list)
    monkeypatch.setattr(sweep, "make_client", lambda: FakeClient())

    rc = sweep.run(surnames=["A"], max_surnames=None, refresh_known=False, dry_run=False)
    assert rc == 0

    # The changelog must not have been written (or must contain zero events).
    if changelog_path.exists():
        events = json.loads(changelog_path.read_text(encoding="utf-8"))
        assert events == [], (
            f"interrupted sweep emitted {len(events)} bogus events into the "
            f"changelog; clean_finish gate failed"
        )
