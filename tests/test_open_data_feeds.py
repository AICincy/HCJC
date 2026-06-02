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
    assert rows == []
