# Exercises — how to actually do these

**The exercises now live inside `tests/test_planner.py`, not in this
file.** Open it. Everything is in order, with the blanks marked `# TODO`
and the shape already written out. This file is just the map.

## The loop

```bash
.venv\Scripts\activate
pytest -v
```

Right now: **3 pass, 4 skipped.** The 4 skipped ones are yours. Do them
top to bottom — they get harder in order.

For each one:

1. Delete its `@pytest.mark.skip(...)` line. Run `pytest -v`. It fails.
   **That's correct** — you want to see it fail before you make it pass.
2. Replace each `# TODO` with a real line of code.
3. Run `pytest -v` again. Read the failure message — it tells you what
   Python actually saw versus what you asserted.

## Before you start: how a pytest test is shaped

Every test is a plain function whose name starts with `test_`. pytest
finds it, runs it, and calls it passing if no `assert` fails. The body
is always three parts:

```python
def test_something():
    thing = build_the_thing()        # ARRANGE — set up the world
    result = thing.do_one_action()   # ACT     — the one thing you're testing
    assert result == "expected"      # ASSERT  — what must be true after
```

That's the whole framework. `pytest.raises` is the one extra piece, and
it's fully explained in the worked example.

## What's in the file

| Part | What | Status |
|---|---|---|
| 1 | Two **reference tests** | written — read them first |
| 2 | One **worked exercise** (`PlannerOutput` validation) | written, every line explained — this is your pattern |
| 3 | Exercises **A–D** | scaffolds with `# TODO` blanks — yours |

**Read Part 2 carefully before starting Part 3.** It's deliberately the
simplest possible test — no graph, no model, just a Pydantic class — so
you can see the shape without anything else in the way.

Rules that make this work: docs are fine, a finished solution is not.
Stuck more than ~15 minutes? Ask me for a **hint**, not the code.

---

## Part B — the real bug (do this after A–D)

### The planner invents a plan for things that don't exist

Verified again on 2026-09-25 via `eval_planner.py`:

```
$ python eval_planner.py

asdfgh qwerty zxcvb
1. What are the 1-year, 3-year, and 5-year annualized returns for
   asdfgh qwerty zxcvb compared to its primary benchmark?
2. How does the expense ratio and fee structure of asdfgh qwerty zxcvb
   compare to its direct category peers?
```

It's now interpolating the gibberish directly into confident, cited-
looking research questions.

**Why it happens** — and this follows directly from THEORY.md §3.
`PlannerOutput` has exactly one field, `subtasks: List[str]`. So *"I
don't recognise this"* is **not a representable answer**. Constrained
decoding forces a list of sub-questions, so the model produces the most
plausible list it can.

The schema that makes the planner reliable is the same thing that makes
refusal impossible.

**Why it's serious:** nothing downstream catches it either. The Week 2
researcher will search for a nonexistent asset, the Week 3 critic will
score whatever prose comes back, and DeepDive emits a cited-looking
report about nothing. Silent failure — the worst kind.

**Your task.** Give the planner a way to say "I don't recognise this."

Decisions that are genuinely yours — think before typing:

- Where does the check belong: a new field on `PlannerOutput`, or a
  separate node before the planner?
- If a field: what shape? `bool`? A confidence score? An enum of
  `fund | stock | unrecognised`?
- **What does the graph do about it?** This is the interesting part. You
  need a conditional edge out of the planner that routes either to `END`
  or onward. That's your first `add_conditional_edges` — the same
  mechanism Week 3's critic loop needs. Much cheaper to get wrong here.
- How do you test it with no API call? (The fake returns whatever you
  want.)

Write the test first, watch it fail, then make it pass.

---

## Part C — the 15-minute blank-slate drill

Do this at the start of a session, before real code. Highest value per
minute on this page for syntax retention.

```bash
mkdir scratch && cd scratch      # gitignored
```

From memory, with **all project files closed**, write a working
LangGraph that:

1. defines a `TypedDict` state with `topic: str` and `notes: list[str]`
2. has a node that appends one string to `notes`
3. compiles and runs, printing the final state

No LLM, no API key — pure LangGraph.

You will forget whether it's `add_edge(START, "x")` or
`set_entry_point("x")`, and where `END` imports from. **That forgetting
is the exercise.** Looking it up *after* failing to recall it is what
makes it stick; reading it first doesn't.

Escalate weekly:

- **Week 2:** a second node, and a reducer with `Annotated`.
- **Week 3:** a conditional edge that loops back, with a counter that
  caps the loop. That's DeepDive's critic in miniature — build it here
  first, where it's disposable.
