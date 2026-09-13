"""
The DeepDive research graph.

Week 1 shape:

    START -> planner -> END

Weeks 2 and 3 add the researcher node, the critic node, and the
conditional edge that sends a weak draft back to the researcher.
The graph is built here and nowhere else so that the CLI, the tests,
and (later) the FastAPI endpoint all run the exact same pipeline.
"""

from langgraph.graph import StateGraph, START, END

from app.state import ResearchState
from app.planner import build_planner_node


def build_graph(planner_llm=None):
    """Wire the nodes together and return a compiled, runnable graph.

    planner_llm is injectable for tests; production passes nothing and
    each node builds its own model from app.llm.
    """
    builder = StateGraph(ResearchState)

    builder.add_node("planner", build_planner_node(planner_llm))

    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)

    return builder.compile()
