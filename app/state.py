"""
Shared state for the DeepDive research graph.

Every agent node (planner, researcher, critic) reads from and writes
back to this one object. LangGraph merges each node's return dict
into this state automatically.
"""

from typing import TypedDict, List, Dict


class ResearchState(TypedDict):
    # user query
    query: str

    # filled by the planner: list of sub-questions to research
    plan: List[str]

    # filled by the researcher: {sub_question: finding_text}
    # left empty for week 1 — researcher doesn't exist yet
    findings: Dict[str, str]

    # filled by the researcher: the draft report text
    draft: str

    # filled by the critic: feedback if the draft needs revision
    critique: str

    # how many times the critic has sent the draft back for revision
    iteration: int
