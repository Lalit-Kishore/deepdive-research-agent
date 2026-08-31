"""
Planner agent.

Takes the user's raw query (a fund name or stock ticker) and breaks
it into 4-5 concrete sub-questions the researcher agent will answer
in later weeks. Uses Gemini's structured output so we get a clean
Python list back instead of parsing free text.
"""

from pydantic import BaseModel, Field
from typing import List
from app.llm import get_llm
from app.state import ResearchState


class PlannerOutput(BaseModel):
    subtasks: List[str] = Field(
        description=(
            "4 to 5 specific, researchable sub-questions about the "
            "given fund or stock. Cover: recent performance drivers, "
            "cost vs peers, manager/leadership track record, and "
            "concentration or sector risk."
        )
    )


PLANNER_SYSTEM_PROMPT = """You are a research planner for a financial \
research assistant. Given a mutual fund name or a stock ticker, break \
it into 4-5 specific sub-questions a researcher could answer using \
web search and financial data tools.

Good sub-questions are specific and checkable, e.g.:
- "What has driven HDFC Flexi Cap Fund's returns over the past 3 years?"
- "How does its expense ratio compare to category peers?"

Avoid vague sub-questions like "Is this a good investment?" — that is \
not researchable. Focus on facts: performance, cost, management, risk."""


def build_planner_node():
    """Returns a function usable as a LangGraph node."""
    llm = get_llm()
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
