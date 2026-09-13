"""
Tests for the planner node and the Week 1 graph.

Two reference tests are written out below. The rest of the file is
EXERCISES — specs with no implementation, for you to fill in. See
tests/EXERCISES.md for what each one should assert and why it matters.

Run:  pytest -v
"""

import pytest

from app.graph import build_graph
from app.planner import PlannerOutput, build_planner_node
from tests.conftest import FakeChatModel


# ---------------------------------------------------------------------
# Reference tests — worked examples. Read these before the exercises.
# ---------------------------------------------------------------------


def test_planner_node_returns_only_the_plan_key(fake_llm):
    """A node returns a PARTIAL state update, not the whole state.

    This is the single most important thing to internalise about
    LangGraph nodes. The planner owns exactly one field, so it returns
    exactly one key, and LangGraph merges that into the state. Returning
    the full state from a node is a common beginner mistake that causes
    fields to be silently clobbered.
    """
    node = build_planner_node(llm=fake_llm)

    result = node({"query": "HDFC Flexi Cap Fund"})

    assert set(result.keys()) == {"plan"}
    assert result["plan"] == fake_llm.subtasks


def test_planner_sends_the_query_to_the_model(fake_llm):
    """The user's query must actually reach the model.

    Worth a test because it is easy to build a beautiful prompt and
    forget to interpolate the input — and the model will still return a
    plausible-looking generic plan, so the bug does not look like a bug.
    """
    node = build_planner_node(llm=fake_llm)

    node({"query": "Parag Parikh Flexi Cap Fund"})

    assert len(fake_llm.calls) == 1
    messages = fake_llm.calls[0]
    sent = " ".join(content for _role, content in messages)

    assert "Parag Parikh Flexi Cap Fund" in sent
    # and the system prompt went along with it
    assert "research planner" in sent.lower()


# ---------------------------------------------------------------------
# EXERCISES — delete the `skip` and implement. Specs in EXERCISES.md.
# ---------------------------------------------------------------------


@pytest.mark.skip(reason="exercise 1 — not implemented yet")
def test_planner_binds_the_pydantic_schema(fake_llm):
    """Exercise 1: assert the planner bound PlannerOutput as its schema.

    Hint: the fake records this on `fake_llm.bound_schema`.
    Why it matters: proves the structured-output path is wired, not that
    someone quietly went back to parsing free text.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="exercise 2 — not implemented yet")
def test_graph_runs_end_to_end_and_preserves_the_query():
    """Exercise 2: run the compiled graph, not just the bare node.

    Hint: build_graph(planner_llm=FakeChatModel(...)), then .invoke()
    with {"query": ...}. Assert the plan arrived AND that "query" is
    still in the final state.
    Why it matters: this is the merge behaviour from THEORY.md §2 —
    prove to yourself that returning {"plan": ...} does not wipe
    "query".
    """
    raise NotImplementedError


@pytest.mark.skip(reason="exercise 3 — not implemented yet")
def test_planner_output_rejects_a_bad_shape():
    """Exercise 3: prove the Pydantic model actually validates.

    Hint: PlannerOutput(subtasks="not a list") should raise.
    Import ValidationError from pydantic and use pytest.raises.
    Why it matters: this is the "validate at the boundary" claim from
    THEORY.md §2. Either the boundary enforces the type or it doesn't.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="exercise 4 — not implemented yet")
def test_model_is_built_once_not_per_invocation():
    """Exercise 4: prove the closure-factory claim from THEORY.md §4.

    Hint: build the node once, invoke it three times, and assert
    with_structured_output was only called once. You will need to count
    that — add a counter to FakeChatModel in conftest.py.
    Why it matters: in Week 3 the critic loop re-invokes nodes. If the
    client were rebuilt per call you would pay that cost every pass.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="exercise 5 — not implemented yet")
def test_planner_propagates_model_errors():
    """Exercise 5: decide and encode what happens when the API fails.

    Hint: FakeChatModel(raises=RuntimeError("429 rate limited")).
    Today the error propagates — assert that with pytest.raises.
    Why it matters: this is THEORY.md question 10. Write the test for
    the behaviour you have, then decide whether you WANT that behaviour.
    A rate limit killing the whole run may not be what you want.
    """
    raise NotImplementedError
