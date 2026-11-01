"""
Tests for the search tool. Offline: a FakeSearchClient (tests/conftest.py)
stands in for Tavily, so no key and no credits are needed.
"""

import pytest

from app.search import build_reader, build_search
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


@pytest.mark.parametrize("value", [None, "", "   "])
@pytest.mark.parametrize("builder", [build_search, build_reader])
def test_missing_key_fails_at_build_time(monkeypatch, builder, value):
    """TavilyClient would silently go keyless, so we must check ourselves."""
    if value is None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TAVILY_API_KEY", value)

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        builder()


def test_key_present_builds_without_a_network_call(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-dummy")

    assert callable(build_search())


def test_injected_client_needs_no_key(monkeypatch, fake_search_client):
    """Tests and fakes must never depend on a real key."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    assert callable(build_search(client=fake_search_client))


def test_reader_uses_basic_depth_and_caps_page_size():
    url = "https://x/1"
    client = FakeSearchClient(pages={url: "a" * 50})

    texts = build_reader(client=client, max_chars=10)([url])

    assert texts == {url: "a" * 10}
    _urls, kwargs = client.extract_calls[0]
    assert kwargs["extract_depth"] == "basic"


def test_reader_leaves_out_pages_it_could_not_fetch():
    client = FakeSearchClient(pages={})

    assert build_reader(client=client)(["https://blocked"]) == {}
