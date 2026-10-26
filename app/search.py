"""
Web search tool.

The researcher calls this once per planner sub-question. It is a plain
function, not a LangChain tool: the plan already decides what to
search, so no model needs to choose when to call it, and every search
saved is an LLM call saved.

Uses Tavily's own client rather than langchain-tavily. The LangChain
tool returns errors as values (a string for "no results", a dict for a
bad key) instead of raising them, which is easy to miss.
"""

from typing import List, TypedDict

from tavily import TavilyClient


class SearchResult(TypedDict):
    title: str
    url: str
    # Tavily's extract of the page most relevant to the query, not the
    # whole page. Enough to cite from; the page reader comes later.
    content: str


def build_search(client=None, max_results: int = 5):
    """Returns a search(query) function.

    client is injectable so tests can pass a fake and never hit the
    API. The real client reads TAVILY_API_KEY and fails here, at build
    time, if it is missing — not halfway through a run.
    """
    client = client if client is not None else TavilyClient()

    def search(query: str) -> List[SearchResult]:
        # "basic" costs 1 credit. Pinned explicitly so a library default
        # can never silently upgrade a run to "advanced" (2 credits).
        response = client.search(
            query,
            search_depth="basic",
            max_results=max_results,
        )
        # Keep only what the researcher needs. Tavily also returns a
        # relevance score, timings and more, which would only cost tokens.
        return [
            {
                "title": r.get("title", ""),
                "url": r["url"],
                "content": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]

    return search
