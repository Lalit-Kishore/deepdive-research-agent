"""
Run the full pipeline on one question: plan, search, cited answer.

    python run.py "How do I run a Frappe job only after the DB commits?"

Costs real money: one Tavily credit per sub-question (3-5) plus two
Gemini calls (planner, researcher).
"""

import sys

from dotenv import load_dotenv

load_dotenv()  # must run before the graph builds its clients

from app.graph import build_graph  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python run.py "How do I run a Frappe job only after the DB commits?"')
        return 1

    query = " ".join(sys.argv[1:])
    result = build_graph().invoke({"query": query})

    print(f"\nQuestion: {query}")
    print("\nPlan:")
    for i, subtask in enumerate(result["plan"], start=1):
        print(f"  {i}. {subtask}")

    print(f"\n{'-' * 60}\n{result['draft']}\n{'-' * 60}")

    print("\nSources:")
    for i, s in enumerate(result["sources"], start=1):
        print(f"  [{i}] {s['title']}\n      {s['url']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
