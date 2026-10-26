"""
Tests for the search tool. Offline: a FakeSearchClient (tests/conftest.py)
stands in for Tavily, so no key and no credits are needed.
"""

import pytest

from app.search import build_search
from tests.conftest import FakeSearchClient


def test_search_returns_only_title_url_content(fake_search_client):
    """Extra Tavily fields (score, raw_content) are dropped: they only cost tokens."""
    search = build_search(client=fake_search_client)

    results = search("frappe.enqueue enqueue_after_commit")

    assert len(results) == 2
    for r in results:
        assert set(r.keys()) == {"title", "url", "content"}
    assert results[0]["url"].startswith("https://docs.frappe.io")


def test_search_uses_basic_depth_and_max_results(fake_search_client):
    """Credit control: basic = 1 credit. This test fails if anyone changes it."""
    search = build_search(client=fake_search_client, max_results=3)

    search("frappe.db.get_value no match")

    query, kwargs = fake_search_client.calls[0]
    assert query == "frappe.db.get_value no match"
    assert kwargs["search_depth"] == "basic"
    assert kwargs["max_results"] == 3


def test_search_with_no_results_returns_empty_list():
    """A made-up API (frappe.db.turbo_sync) finds nothing. That is data
    for the researcher, not a crash."""
    search = build_search(client=FakeSearchClient(results=[]))

    assert search("frappe.db.turbo_sync multi-site") == []


def test_search_propagates_client_errors():
    """A bad key or a network failure must surface, not become fake 'no results'."""
    search = build_search(client=FakeSearchClient(raises=RuntimeError("401 invalid key")))

    with pytest.raises(RuntimeError):
        search("anything")
