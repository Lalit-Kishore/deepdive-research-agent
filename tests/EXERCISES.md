# Exercises — write the code yourself

The point of this file is **active recall**. Retyping code you can see
teaches almost nothing; producing code you can't see is what builds the
memory. So none of these give you the answer.

Rules that make this work:

- Look at the LangGraph/pytest docs as much as you like. Do **not** look
  at a finished solution.
- Run `pytest -v` after every attempt. A failing test is information.
- If you're stuck for more than ~15 minutes on one, ask me for a *hint*,
  not the code.

```bash
.venv\Scripts\activate
pytest -v            # 2 pass, 5 skipped -> your job is to unskip them
```

---

## Part A — the pytest exercises (in `tests/test_planner.py`)

Delete the `@pytest.mark.skip` line and replace `raise
NotImplementedError` with a real test body.

### 1. `test_planner_binds_the_pydantic_schema`

Assert that the planner bound `PlannerOutput` as its structured-output
schema.

- The fake records it on `fake_llm.bound_schema`.
- **Why it matters:** proves the structured-output path is actually
  wired. If someone later replaced it with free-text parsing, every
  other test would still pass — this is the one that would fail.

### 2. `test_graph_runs_end_to_end_and_preserves_the_query`

Run the **compiled graph**, not the bare node.

- `build_graph(planner_llm=FakeChatModel(subtasks=[...]))`, then
  `.invoke({"query": "..."})`.
- Assert the plan arrived **and** that `query` survived in the final
  state.
- **Why it matters:** this is the merge behaviour from THEORY.md §2.
  Prove to yourself that returning `{"plan": ...}` doesn't wipe
  `query`. Don't take my word for it — that's the whole point.

### 3. `test_planner_output_rejects_a_bad_shape`

Prove the Pydantic model actually validates.

- `PlannerOutput(subtasks="not a list")` should raise.
- `from pydantic import ValidationError`, then `pytest.raises`.
- **Why it matters:** THEORY.md §2 claims "validate at the boundary."
  Either the boundary enforces the type or the claim is decoration.

### 4. `test_model_is_built_once_not_per_invocation`

Prove the closure-factory claim from THEORY.md §4.

- Build the node once, invoke it three times, assert
  `with_structured_output` was called exactly **once**.
- You'll need to count that — **add a counter to `FakeChatModel`** in
  `conftest.py`. Editing the fixture is part of the exercise.
- **Why it matters:** in Week 3 the critic loop re-invokes nodes
  repeatedly. If the client were rebuilt per call you'd pay setup cost
  on every pass.

### 5. `test_planner_propagates_model_errors`

Encode what happens when the API fails.

- `FakeChatModel(raises=RuntimeError("429 rate limited"))`.
- Today the error propagates. Assert that with `pytest.raises`.
- Then **decide whether you want that.** A rate limit killing an
  entire research run is a design choice, not a law. This is THEORY.md
  question 10 — the test is how you pin down your answer.

---

## Part B — a real bug to fix (this one matters)

### 6. The planner accepts nonsense

Verified on 2026-09-13:

```
$ python run_planner.py "asdfgh qwerty zxcvb"

1. What has driven the recent 3-year and 5-year annualized returns of
   the target asset relative to its benchmark?
2. How does the expense ratio or management fee structure of this asset
   compare with its category peer average?
...
```

It produced a confident, plausible, completely generic plan for a fund
that does not exist. It did not refuse, and it did not flag anything.

**Why this is worse than it looks.** Nothing downstream will catch it
either. The Week 2 researcher will dutifully search the web for a
nonexistent asset, the Week 3 critic will score whatever prose comes
back, and DeepDive will emit a cited-looking report about nothing. The
failure is *silent*, which is the worst kind.

**Your task.** Make the planner able to say "I don't recognise this."

Design decisions that are genuinely yours to make — think before you
type:

- Where does the check belong? In `PlannerOutput` as an extra field, or
  as a separate node before the planner?
- If it's a field: what shape? A `bool`? A confidence score? An enum of
  `fund | stock | unrecognised`?
- What does the **graph** do about it? This is the interesting part —
  you'll need a conditional edge from the planner that routes either to
  `END` or onward. That's your first `add_conditional_edges`, and it's
  the same mechanism Week 3's critic loop needs. Getting it wrong here
  is much cheaper than getting it wrong there.
- How do you test it without an API call? (The fake model can return
  whatever you want.)

Write the test **first**, watch it fail, then make it pass.

---

## Part C — the 15-minute blank-slate drill

Do this at the start of a session, before touching real code. It is the
highest-value-per-minute thing on this page for syntax retention.

```bash
mkdir scratch && cd scratch      # scratch/ is gitignored
```

From memory, with **all project files closed**, write a working
LangGraph that:

1. defines a `TypedDict` state with `topic: str` and `notes: list[str]`
2. has a node that appends one string to `notes`
3. compiles and runs, printing the final state

No LLM, no API key — pure LangGraph. Then diff your mental model
against `app/state.py` and `app/graph.py`.

You will forget `StateGraph(...)` vs `builder.compile()`, whether it's
`add_edge(START, "x")` or `set_entry_point("x")`, and the exact import
path for `END`. **That forgetting is the exercise.** Looking it up after
failing to recall it is what makes it stick; reading it beforehand
doesn't.

Escalate it over the weeks:

- **Week 2:** add a second node and a reducer with `Annotated`.
- **Week 3:** add a conditional edge that loops back, with a counter
  that caps the loop. (This is DeepDive's critic in miniature — build it
  here first.)
