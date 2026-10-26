"""
The DeepDive research graph.

Current shape:

    START -> planner -> researcher -> END

Week 3 adds the critic node and the conditional edge that sends a weak
draft back to the researcher. The graph is built here and nowhere else
so that the CLI, the tests, and (later) the eval all run the exact same
pipeline.
"""

from langgraph.graph import StateGraph, START, END

from app.state import ResearchState
from app.planner import build_planner_node
from app.researcher import build_researcher_node


def build_graph(planner_llm=None, researcher_llm=None, search=None):
    """Wire the nodes together and return a compiled, runnable graph.

    Every argument is injectable for tests; production passes nothing and
    each node builds its own model (app.llm) and search tool (app.search).
    """
    builder = StateGraph(ResearchState)

    builder.add_node("planner", build_planner_node(planner_llm))
    builder.add_node(
        "researcher", build_researcher_node(llm=researcher_llm, search=search)
    )

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", END)

    return builder.compile()
