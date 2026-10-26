"""
Researcher agent.

Runs one web search per planner sub-question, pools the results into a
single numbered source list, and makes ONE model call that writes the
answer with [n] citations into that list.

One call for the whole question, not one per sub-question: fewer calls
is lower cost and latency, and the model sees every source at once, so
it can reconcile sources that disagree. See DEVLOG.md (2026-10-25).
"""

from typing import Callable, List

from app.llm import get_llm
from app.search import SearchResult, build_search
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
    """
    sources: List[SearchResult] = []
    seen_urls = set()
    for sub_question in plan:
        for result in search(sub_question):
            if result["url"] not in seen_urls:
                seen_urls.add(result["url"])
                sources.append(result)
    return sources


def format_sources(sources: List[SearchResult]) -> str:
    """Number sources from 1, the way the model is told to cite them."""
    return "\n\n".join(
        f"[{i}] {s['title']}\n{s['url']}\n{s['content']}"
        for i, s in enumerate(sources, start=1)
    )


def build_researcher_node(llm=None, search=None):
    """Returns a function usable as a LangGraph node.

    llm and search are injectable so tests can pass fakes and never hit
    either API. Same closure-factory shape as build_planner_node.
    """
    llm = llm if llm is not None else get_llm()
    search = search if search is not None else build_search()

    def researcher_node(state: ResearchState) -> dict:
        sources = collect_sources(state["plan"], search)

        # Nothing to cite from: skip the model call entirely rather than
        # pay for an answer that could only come from memory.
        if not sources:
            return {"sources": [], "draft": NO_SOURCES_DRAFT}

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
