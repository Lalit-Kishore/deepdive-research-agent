"""
Researcher agent.

Runs one web search per planner sub-question, pools the results into a
single numbered source list, reads the full text of the top pages, and
makes ONE model call that writes the answer with [n] citations.

One call for the whole question, not one per sub-question: fewer calls
is lower cost and latency, and the model sees every source at once, so
it can reconcile sources that disagree. See DEVLOG.md (2026-10-25).
"""

from itertools import chain, zip_longest
from typing import Callable, Dict, List

from app.llm import get_llm
from app.search import SearchResult, build_reader, build_search
from app.state import ResearchState


RESEARCHER_SYSTEM_PROMPT = """You are a technical researcher. Answer the \
user's question using ONLY the numbered sources provided.

Rules:
- Cite every factual claim with its source number in square brackets, \
e.g. [2]. When several sources agree, cite them together, e.g. [1][3].
- If the sources do not answer part of the question, say so plainly. \
Do not fill the gap from memory.
- When sources disagree, say so. Prefer official docs and source code \
over forum posts.
- Include a code example only if a source shows one.
- Lead with the direct answer, then the details. No preamble."""

# 5 is what one Tavily Extract credit buys. Snippets alone often miss the
# answer, even on the right page. See DEVLOG.md Finding #12.
PAGES_TO_READ = 5

NO_SOURCES_DRAFT = (
    "No sources were found for this question, so it cannot be answered "
    "with citations."
)


def collect_sources(
    plan: List[str], search: Callable[[str], List[SearchResult]]
) -> List[SearchResult]:
    """Search every sub-question and pool the results, one entry per URL.

    The same page often comes back for two sub-questions. Keeping it once
    means one citation number per page, so [n] always means one thing.

    Pooled by rank across sub-questions (every question's best result,
    then every second best...), so the top of the list covers the whole
    plan rather than only the first sub-question.
    """
    results_per_question = [search(sub_question) for sub_question in plan]
    by_rank = chain.from_iterable(zip_longest(*results_per_question))

    sources: List[SearchResult] = []
    seen_urls = set()
    for result in by_rank:
        if result is not None and result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            sources.append(result)
    return sources


def read_top_sources(
    sources: List[SearchResult],
    read: Callable[[List[str]], Dict[str, str]],
    pages: int = PAGES_TO_READ,
) -> List[SearchResult]:
    """Swap the snippet for full page text on the top sources.

    A page that could not be fetched keeps its snippet, so one blocked
    site costs some detail rather than the whole source.
    """
    texts = read([s["url"] for s in sources[:pages]])
    return [{**s, "content": texts.get(s["url"], s["content"])} for s in sources]


def format_sources(sources: List[SearchResult]) -> str:
    """Number sources from 1, the way the model is told to cite them."""
    return "\n\n".join(
        f"[{i}] {s['title']}\n{s['url']}\n{s['content']}"
        for i, s in enumerate(sources, start=1)
    )


def build_researcher_node(llm=None, search=None, read=None):
    """Returns a function usable as a LangGraph node.

    llm, search and read are injectable so tests can pass fakes and never
    hit either API. Same closure-factory shape as build_planner_node.
    """
    llm = llm if llm is not None else get_llm()
    search = search if search is not None else build_search()
    read = read if read is not None else build_reader()

    def researcher_node(state: ResearchState) -> dict:
        sources = collect_sources(state["plan"], search)

        # Nothing to cite from: skip the model call entirely rather than
        # pay for an answer that could only come from memory.
        if not sources:
            return {"sources": [], "draft": NO_SOURCES_DRAFT}

        sources = read_top_sources(sources, read)

        response = llm.invoke(
            [
                ("system", RESEARCHER_SYSTEM_PROMPT),
                (
                    "human",
                    f"Question: {state['query']}\n\n"
                    f"Sources:\n\n{format_sources(sources)}",
                ),
            ]
        )
        # .text, not .content: Gemini 3 can return content as a list of
        # blocks, and .text joins them into one string.
        return {"sources": sources, "draft": response.text}

    return researcher_node
