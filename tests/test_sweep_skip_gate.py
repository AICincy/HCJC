"""Skip-gate must not block a manual refresh_known or --force run."""

from scraper.sweep_skip import should_skip_sweep


def test_fresh_snapshot_skips() -> None:
    assert should_skip_sweep(60.0) is True


def test_stale_or_unknown_does_not_skip() -> None:
    assert should_skip_sweep(None) is False
    assert should_skip_sweep(21 * 60) is False


def test_refresh_known_bypasses_skip_gate() -> None:
    assert should_skip_sweep(60.0, refresh_known=True) is False


def test_force_flag_bypasses_skip_gate() -> None:
    assert should_skip_sweep(60.0, force=True) is False


def test_force_env_bypasses_skip_gate(monkeypatch) -> None:
    monkeypatch.setenv("JCSTREAM_FORCE_SWEEP", "1")
    assert should_skip_sweep(60.0) is False
