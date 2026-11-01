"""
Web search and page reading, both on Tavily.

The researcher calls this once per planner sub-question. It is a plain
function, not a LangChain tool: the plan already decides what to
search, so no model needs to choose when to call it, and every search
saved is an LLM call saved.

Uses Tavily's own client rather than langchain-tavily. The LangChain
tool returns errors as values (a string for "no results", a dict for a
bad key) instead of raising them, which is easy to miss.
"""

import os
from typing import Dict, List, TypedDict

from tavily import TavilyClient


class SearchResult(TypedDict):
    title: str
    url: str
    # Tavily's extract of the page most relevant to the query, not the
    # whole page. The researcher swaps in full text for its top sources.
    content: str


def build_client() -> TavilyClient:
    """Build the real client, or fail now if TAVILY_API_KEY is missing.

    TavilyClient does not check this itself: with no key it silently
    drops to a limited keyless mode, so the failure would only appear
    mid-run.
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not set. Add it to .env "
            "(get a key at https://app.tavily.com)."
        )
    return TavilyClient(api_key=api_key)


def build_search(client=None, max_results: int = 5):
    """Returns a search(query) function.

    client is injectable so tests can pass a fake and never hit the
    API. Without one, a missing key fails here, at build time.
    """
    client = client if client is not None else build_client()

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


def build_reader(client=None, max_chars: int = 30_000):
    """Returns a read(urls) function: {url: page text}.

    Pages Tavily could not fetch are simply absent from the result, and
    are not charged. max_chars caps a huge page: 30k chars is about 7.5k
    tokens, which covers a long docs page and keeps cost predictable.
    """
    client = client if client is not None else build_client()

    def read(urls: List[str]) -> Dict[str, str]:
        # "basic" costs 1 credit per 5 pages; pinned for the same reason
        # as search_depth above.
        response = client.extract(urls, extract_depth="basic", format="text")
        return {
            r["url"]: r["raw_content"][:max_chars]
            for r in response.get("results", [])
            if r.get("raw_content")
        }

    return read
