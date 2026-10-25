"""
Planner agent.

Takes the user's technical question and breaks it into 3-5 concrete
sub-questions the researcher agent will answer in later weeks, one
web search each. Uses Gemini's structured output so we get a clean
Python list back instead of parsing free text.
"""

from pydantic import BaseModel, Field
from typing import List
from app.llm import get_llm
from app.state import ResearchState


class PlannerOutput(BaseModel):
    subtasks: List[str] = Field(
        description=(
            "3 to 5 specific sub-questions that together answer the "
            "user's technical question. Each must work on its own as a "
            "web search query. Cover: what the official docs say, how "
            "developers actually solved it (forums, GitHub issues, Q&A "
            "sites), and the known pitfalls or trade-offs of the fix."
        )
    )


PLANNER_SYSTEM_PROMPT = """You are a research planner for a technical \
research assistant. Given a technical question or a problem to solve, \
break it into 3-5 specific sub-questions a researcher could answer with \
one web search each and by reading the pages it finds.

Good sub-questions are specific and checkable. For the question \
"How do I run a Frappe background job only after the current database \
transaction commits?", good sub-questions are:
- "What does the enqueue_after_commit argument of frappe.enqueue do?"
- "How do Frappe developers handle background jobs that read a record \
before the transaction that created it has committed?"
- "What errors occur when a Frappe background job is enqueued before \
the database commit?"

Avoid vague sub-questions like "What is Frappe?" or "What are best \
practices for background jobs?" — they drift away from the user's \
question and a search returns generic pages. Name the specific \
library, function, version or error message involved, so each \
sub-question works as a search query without the original question \
next to it.

Use fewer sub-questions for a narrow question; do not pad. Focus on \
what sources can confirm: documented behaviour, working code, version \
differences, and known bugs."""


def build_planner_node(llm=None):
    """Returns a function usable as a LangGraph node.

    llm is injectable so tests can pass a fake and never hit the API.
    Built once here rather than inside planner_node, so the client and
    the bound schema are reused across every invocation — including
    every pass of the Week 3 critic loop.
    """
    llm = llm if llm is not None else get_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)

    def planner_node(state: ResearchState) -> dict:
        result: PlannerOutput = structured_llm.invoke(
            [
                ("system", PLANNER_SYSTEM_PROMPT),
                ("human", f"Query: {state['query']}"),
            ]
        )
        return {"plan": result.subtasks}

    return planner_node
