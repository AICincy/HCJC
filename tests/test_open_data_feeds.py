from __future__ import annotations

import httpx

from scraper import open_data_feeds


def test_pull_one_swallows_transport_errors(monkeypatch):
    def fake_query(*args, **kwargs):
        raise httpx.ConnectError("Socrata connection timed out")

    monkeypatch.setattr(open_data_feeds, "query", fake_query)

    spec = open_data_feeds.FeedSpec(
        dataset_id="test-id",
        filename="test_feed.json",
        label="Test Feed",
        where_candidates=("interview_date > '{since}'",),
    )
    rows = open_data_feeds._pull_one(spec)
    assert rows is None


def test_frozen_contact_card_feeds_have_no_date_filter():
    """Traffic + pedestrian Contact Card sources froze in 2024-2025; a date
    filter zeroes them out, so they must pull most-recent rows unfiltered
    (like the paused PDI use-of-force feed). Regression guard for the
    2026-07 zero-row fix."""
    frozen = {"w2kv-5pdg", "swrz-ak2i"}
    seen = set()
    for spec in open_data_feeds.FEEDS:
        if spec.dataset_id in frozen:
            seen.add(spec.dataset_id)
            assert spec.where_candidates == (), (
                f"{spec.label} ({spec.dataset_id}) must not date-filter; "
                "the source is frozen and a filter zeroes it out"
            )
            assert spec.order == "interview_date DESC"
    assert seen == frozen, f"missing frozen feed specs: {frozen - seen}"


def test_pull_all_skips_save_on_error(monkeypatch, tmp_path):
    # Setup data directory inside temporary directory
    monkeypatch.setattr(open_data_feeds, "DATA_DIR", tmp_path)

    # Pre-write a dummy cached feed file
    dummy_file = tmp_path / "use_of_force_pdi_recent.json"
    dummy_file.write_text("dummy cached data", encoding="utf-8")

    # Mock recently_refreshed to return False so we force a pull
    monkeypatch.setattr(open_data_feeds, "recently_refreshed", lambda *a, **k: False)

    # Mock _pull_one to return None (failure)
    monkeypatch.setattr(open_data_feeds, "_pull_one", lambda *a, **k: None)

    # Track if _save is called
    save_called = False

    def fake_save(spec, rows):
        nonlocal save_called
        save_called = True

    monkeypatch.setattr(open_data_feeds, "_save", fake_save)

    refreshed = open_data_feeds.pull_all(force=True)

    # Assert pull_all completed without updating refreshed count,
    # without calling save, and leaving the pre-existing file intact.
    assert refreshed == 0
    assert not save_called
    assert dummy_file.read_text(encoding="utf-8") == "dummy cached data"
