"""
Manual smoke test for the search tool: one real Tavily search (1 credit),
printed for you to judge by eye.

    python run_search.py "frappe.enqueue enqueue_after_commit"

Are the sources the ones you would have opened yourself? Is the
content snippet enough to cite from, or does the researcher need the
full page?
"""

import sys

from dotenv import load_dotenv

load_dotenv()  # must run before the Tavily client reads its key

from app.search import build_search  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python run_search.py "frappe.enqueue enqueue_after_commit"')
        return 1

    query = " ".join(sys.argv[1:])
    results = build_search()(query)

    print(f"\nQuery: {query}")
    print("-" * 60)
    for i, r in enumerate(results, start=1):
        print(f"[{i}] {r['title']}\n    {r['url']}\n    {r['content'][:300]}\n")
    print(f"{len(results)} results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
