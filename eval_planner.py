"""
Batch-evaluate the planner across many queries at once.

    python eval_planner.py                 # run the built-in query set
    python eval_planner.py queries.txt     # run your own, one per line

Writes a timestamped markdown report to reports/ AND prints to screen,
so you can read the output side by side and judge it as a whole rather
than one query at a time.

Why this and not a UI: the thing you are evaluating is whether the
PROMPT is any good. That is a judgement you make by reading many
outputs together and spotting patterns - not by looking at one pretty
result. A UI optimises for a single interaction; this optimises for
comparison.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# The planner node on its own, not the full graph: the graph now runs
# the researcher too, which would spend Tavily credits on every query.
from app.planner import build_planner_node  # noqa: E402

# A deliberately mixed set: two broad Frappe questions, a narrow one
# (should get 3 sub-questions, not padding), a plain Python one, an API
# that does not exist, and gibberish. The last two are the ones that
# tell you something - anything can look good on easy input.
# Keep the planner prompt's own example question OUT of this list: the
# model echoes prompt examples, which would flatter the result.
DEFAULT_QUERIES = [
    "Why does a Frappe whitelisted method return 403 for a Guest user "
    "even with allow_guest=True?",
    "How do I add a custom field to a standard ERPNext DocType so it "
    "survives an app update?",
    "What does frappe.db.get_value return when no record matches?",
    "Why is my Python list comprehension slower than map() on large inputs?",
    "How do I configure frappe.db.turbo_sync for multi-site replication?",
    "asdfgh qwerty zxcvb",
]


def load_queries(argv: list[str]) -> list[str]:
    if len(argv) < 2:
        return DEFAULT_QUERIES

    path = Path(argv[1])
    if not path.exists():
        print(f"No such file: {path}")
        raise SystemExit(1)

    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def main() -> int:
    queries = load_queries(sys.argv)
    planner = build_planner_node()

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"planner_eval_{stamp}.md"

    lines = [f"# Planner evaluation — {stamp}", ""]
    total = 0.0

    for query in queries:
        print(f"\n{'=' * 64}\n{query}\n{'=' * 64}")
        lines += [f"## {query}", ""]

        started = time.perf_counter()
        try:
            plan = planner({"query": query})["plan"]
            elapsed = time.perf_counter() - started
            total += elapsed

            for i, subtask in enumerate(plan, start=1):
                print(f"{i}. {subtask}")
                lines.append(f"{i}. {subtask}")

            note = f"_{len(plan)} sub-questions, {elapsed:.1f}s_"
            print(f"\n{note}")
            lines += ["", note, ""]

        except Exception as exc:
            # One bad query should not kill the whole batch.
            elapsed = time.perf_counter() - started
            total += elapsed
            msg = f"FAILED after {elapsed:.1f}s: {type(exc).__name__}: {exc}"
            print(msg)
            lines += [f"**{msg}**", ""]

    summary = f"{len(queries)} queries in {total:.1f}s"
    lines += ["---", "", summary, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'=' * 64}\n{summary}\nReport: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
