"""
Tests for the researcher node and the planner -> researcher graph.
Offline: FakeChatModel and FakeSearchClient (tests/conftest.py) stand in
for Gemini and Tavily.
"""

from app.graph import build_graph
from app.researcher import (
    NO_SOURCES_DRAFT,
    build_researcher_node,
    collect_sources,
)
from app.search import build_search
from tests.conftest import FakeChatModel, FakeSearchClient


def test_researcher_searches_every_sub_question(fake_llm, fake_search_client):
    node = build_researcher_node(llm=fake_llm, search=build_search(client=fake_search_client))

    node({"query": "Q", "plan": ["sub one", "sub two", "sub three"]})

    searched = [query for query, _kwargs in fake_search_client.calls]
    assert searched == ["sub one", "sub two", "sub three"]


def test_same_url_from_two_searches_is_kept_once(fake_search_client):
    """The fake returns the same 2 pages for every query. Two sub-questions
    must still give 2 sources, not 4, so each [n] means exactly one page."""
    search = build_search(client=fake_search_client)

    sources = collect_sources(["sub one", "sub two"], search)

    assert [s["url"] for s in sources] == [
        "https://docs.frappe.io/framework/user/en/api/background_jobs",
        "https://discuss.frappe.io/t/job-before-commit/1",
    ]


def test_model_gets_question_and_numbered_sources(fake_llm, fake_search_client):
    """The citation contract: the model sees sources numbered [1], [2]...,
    matching their order in state['sources']."""
    node = build_researcher_node(llm=fake_llm, search=build_search(client=fake_search_client))

    result = node({"query": "How do I delay a job until commit?", "plan": ["sub"]})

    sent = " ".join(content for _role, content in fake_llm.calls[0])
    assert "How do I delay a job until commit?" in sent
    assert "[1] frappe.enqueue - Frappe Docs" in sent
    assert "[2] Job runs before doc is saved" in sent
    assert result["draft"] == fake_llm.answer
    assert len(result["sources"]) == 2


def test_no_sources_skips_the_model_call(fake_llm):
    """Nothing to cite from: no paid model call, and an honest draft."""
    node = build_researcher_node(
        llm=fake_llm, search=build_search(client=FakeSearchClient(results=[]))
    )

    result = node({"query": "frappe.db.turbo_sync?", "plan": ["sub"]})

    assert fake_llm.calls == []
    assert result == {"sources": [], "draft": NO_SOURCES_DRAFT}


def test_graph_runs_planner_then_researcher():
    fake = FakeChatModel(subtasks=["Q1", "Q2"])
    graph = build_graph(
        planner_llm=fake,
        researcher_llm=fake,
        search=build_search(client=FakeSearchClient()),
    )

    final = graph.invoke({"query": "How do I delay a job until commit?"})

    assert final["plan"] == ["Q1", "Q2"]
    assert final["draft"] == fake.answer
    assert len(final["sources"]) == 2
    assert final["query"] == "How do I delay a job until commit?"
