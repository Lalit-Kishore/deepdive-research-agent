"""
Manual smoke test for the planner agent: one real API call, printed
for you to judge by eye. The automated suite lives in tests/ and runs
offline.

    python run_planner.py "HDFC Flexi Cap Fund"

Prints the sub-questions the planner produced so you can judge them
by eye: are they specific and researchable, or vague and generic?
Prompt quality is the whole deliverable of Week 1.
"""

import sys

from dotenv import load_dotenv

load_dotenv()  # must run before the graph builds its Gemini client

from app.graph import build_graph  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python run_planner.py "HDFC Flexi Cap Fund"')
        return 1

    query = " ".join(sys.argv[1:])
    graph = build_graph()

    result = graph.invoke({"query": query})

    print(f"\nQuery: {query}")
    print("-" * 60)
    for i, subtask in enumerate(result["plan"], start=1):
        print(f"{i}. {subtask}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
