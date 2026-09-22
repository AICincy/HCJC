"""Skip-gate must not block a manual refresh_known or --force run."""

from __future__ import annotations

from scraper import sweep
from scraper.models import Inmate
from scraper.store import save_current


def _fresh_roster(tmp_path, monkeypatch):
    prev = [
        Inmate(
            inmate_number=str(1000 + i),
            last_name="DOE",
            first_name=f"F{i}",
            booking_date="5/10/26",
        )
        for i in range(60)
    ]
    cur = tmp_path / "current.json"
    save_current(cur, prev)
    monkeypatch.setattr(sweep, "CURRENT_PATH", cur)
    monkeypatch.setattr(sweep, "PHOTOS_DIR", tmp_path / "photos")
    monkeypatch.setattr(sweep, "CHANGELOG_PATH", tmp_path / "changelog.json")
    monkeypatch.setattr(sweep, "ANON_CHANGELOG_PATH", tmp_path / "anon.json")
    monkeypatch.setattr(sweep, "WAF_BLOCK_LOG_PATH", tmp_path / "wbl.json")
    monkeypatch.setattr(sweep, "MIN_SWEEP_INTERVAL_S", 20 * 60)
    calls: list[int] = []

    def _record_call_and_return(c, s):
        calls.append(1)
        return ([], 0, {}, None)

    monkeypatch.setattr(sweep, "_sweep_list", _record_call_and_return)

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sweep, "make_client", lambda: FakeClient())
    return calls


def test_skip_gate_still_trips_on_fresh_data(tmp_path, monkeypatch):
    calls = _fresh_roster(tmp_path, monkeypatch)
    sweep.run(surnames=list("AB"), max_surnames=None, refresh_known=False, dry_run=False)
    assert calls == []


def test_refresh_known_bypasses_skip_gate(tmp_path, monkeypatch):
    calls = _fresh_roster(tmp_path, monkeypatch)
    sweep.run(surnames=list("AB"), max_surnames=None, refresh_known=True, dry_run=False)
    assert calls == [1]


def test_force_flag_bypasses_skip_gate(tmp_path, monkeypatch):
    calls = _fresh_roster(tmp_path, monkeypatch)
    sweep.run(surnames=list("AB"), max_surnames=None, refresh_known=False, dry_run=False, force=True)
    assert calls == [1]


def test_force_env_bypasses_skip_gate(tmp_path, monkeypatch):
    calls = _fresh_roster(tmp_path, monkeypatch)
    monkeypatch.setenv("JCSTREAM_FORCE_SWEEP", "1")
    sweep.run(surnames=list("AB"), max_surnames=None, refresh_known=False, dry_run=False)
    assert calls == [1]
