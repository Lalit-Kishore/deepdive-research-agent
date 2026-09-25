"""
Tests for the planner node and the Week 1 graph.

HOW TO READ THIS FILE, top to bottom:

  1. Two REFERENCE tests  — written for you. Read them first.
  2. One WORKED exercise  — written for you, with every line explained.
  3. Four SCAFFOLDS       — skeletons with TODO blanks. Your job.

Run:  pytest -v
A skipped test is one you haven't done yet. Remove the @pytest.mark.skip
line when you start it.
"""

import pytest

from app.graph import build_graph
from app.planner import PlannerOutput, build_planner_node
from tests.conftest import FakeChatModel


# =====================================================================
# PART 1 — REFERENCE TESTS (already written, just read them)
# =====================================================================
#
# Every pytest test has the same three-part shape. It is worth naming
# the parts out loud the first few times you write one:
#
#   ARRANGE — set up the world
#   ACT     — do the one thing you are testing
#   ASSERT  — state what must be true afterwards
#
# A test is just a function whose name starts with `test_`. pytest finds
# it, runs it, and counts it as passing if no assert fails.


def test_planner_node_returns_only_the_plan_key(fake_llm):
    """A node returns a PARTIAL state update, not the whole state."""
    # ARRANGE: build the node with a fake model instead of a real one
    node = build_planner_node(llm=fake_llm)

    # ACT: call it the way LangGraph would - pass it the state
    result = node({"query": "HDFC Flexi Cap Fund"})

    # ASSERT: it returned exactly one key, and the right value
    assert set(result.keys()) == {"plan"}
    assert result["plan"] == fake_llm.subtasks


def test_planner_sends_the_query_to_the_model(fake_llm):
    """The user's query must actually reach the model."""
    node = build_planner_node(llm=fake_llm)

    node({"query": "Parag Parikh Flexi Cap Fund"})

    # The fake recorded every call, so we can inspect what was sent.
    assert len(fake_llm.calls) == 1
    messages = fake_llm.calls[0]
    sent = " ".join(content for _role, content in messages)

    assert "Parag Parikh Flexi Cap Fund" in sent
    assert "research planner" in sent.lower()


# =====================================================================
# PART 2 — WORKED EXERCISE (written for you, as the pattern to copy)
# =====================================================================


def test_planner_output_rejects_a_bad_shape():
    """PlannerOutput must reject data of the wrong type.

    THEORY.md §2 claims we "validate at the boundary". This test is how
    you check that claim is true rather than decorative.

    Notice this test touches NO graph and NO model. PlannerOutput is
    just a Pydantic class - you can test it entirely on its own. When
    something feels hard to test, that usually means you should test a
    smaller piece of it.
    """
    # ARRANGE + ACT + ASSERT, all in one, using pytest.raises.
    #
    # pytest.raises says: "I EXPECT the code in this block to blow up
    # with this exception. Fail the test if it does NOT." It is how you
    # test error paths - you cannot use a plain assert, because the line
    # would raise before reaching it.
    with pytest.raises(Exception):
        PlannerOutput(subtasks="this is a string, not a list")

    # And the happy path still works - always check both directions, or
    # a test that rejects EVERYTHING would also pass.
    ok = PlannerOutput(subtasks=["one", "two"])
    assert ok.subtasks == ["one", "two"]


# =====================================================================
# PART 3 — YOUR TURN
# =====================================================================
#
# Each one below has the shape filled in and the thinking left to you.
# Work top to bottom; they get harder.
#
# To start one: delete its `@pytest.mark.skip(...)` line, then replace
# each `# TODO` with a real line of code. Run `pytest -v` after every
# change - a failing test tells you something, so read the message.


@pytest.mark.skip(reason="YOUR TURN - exercise A")
def test_planner_binds_the_pydantic_schema(fake_llm):
    """Exercise A: prove the planner bound PlannerOutput as its schema.

    Why this matters: if someone later ripped out structured output and
    went back to parsing free text with regex, every other test in this
    file would still pass. This is the one that would catch it.

    Difficulty: easiest of the four. It is one assert.
    """
    # ARRANGE
    node = build_planner_node(llm=fake_llm)

    # ACT - we must actually invoke it, because the schema gets bound
    # when build_planner_node runs. Try commenting this line out after
    # it passes and see whether the test still passes. (It should! Why?)
    node({"query": "HDFC Flexi Cap Fund"})

    # ASSERT
    # The fake stores whatever schema it was handed on `.bound_schema`
    # (look at tests/conftest.py to see it do this).
    # TODO: assert fake_llm.bound_schema is the PlannerOutput class.
    #       Careful: compare to the CLASS itself, not an instance of it.


@pytest.mark.skip(reason="YOUR TURN - exercise B")
def test_graph_runs_end_to_end_and_preserves_the_query():
    """Exercise B: run the compiled GRAPH, not the bare node.

    Why this matters: this is the merge behaviour from THEORY.md §2.
    The planner returns only {"plan": ...}. Prove to yourself that doing
    so does not wipe out "query". Do not take my word for it.

    Difficulty: easy, but you build the fake yourself this time instead
    of using the `fake_llm` fixture.
    """
    # ARRANGE
    # Note: no `fake_llm` argument in the function signature this time -
    # build your own so you control exactly what comes back.
    fake = FakeChatModel(subtasks=["Q1", "Q2", "Q3"])
    # TODO: build the graph, passing `fake` in.
    #       Look at app/graph.py for the parameter name.

    # ACT
    # TODO: invoke the graph with {"query": "HDFC Flexi Cap Fund"}.
    #       A compiled graph is called with .invoke(state) and it
    #       returns the FINAL state as a dict.

    # ASSERT
    # TODO: assert the plan came back as ["Q1", "Q2", "Q3"]
    # TODO: assert "query" is still in the final state, unchanged


@pytest.mark.skip(reason="YOUR TURN - exercise C")
def test_planner_propagates_model_errors():
    """Exercise C: pin down what happens when the API fails.

    This is not hypothetical. Running eval_planner.py on 2026-09-25,
    two of six queries came back `503 UNAVAILABLE - high demand`.
    Whatever this test asserts is your system's real behaviour today.

    Difficulty: moderate. You use pytest.raises again - copy the
    pattern from the worked exercise above.
    """
    # ARRANGE
    # FakeChatModel takes a `raises=` argument: give it an exception
    # instance and it will raise that instead of returning a plan.
    # TODO: build a FakeChatModel that raises
    #       RuntimeError("503 UNAVAILABLE")
    # TODO: build a planner node with it

    # ACT + ASSERT
    # TODO: assert that invoking the node raises RuntimeError,
    #       using `with pytest.raises(RuntimeError):`

    # THEN STOP AND THINK - this is the actual point of the exercise:
    # you have now proven one bad response kills the whole run. In
    # Week 2 the researcher will make ~5 calls per query, so the odds
    # of hitting one 503 go UP, not down. Is "crash the whole run" the
    # behaviour you want? Write your answer in DEVLOG.md. You do not
    # have to fix it today - but decide, don't drift.


@pytest.mark.skip(reason="YOUR TURN - exercise D")
def test_model_is_built_once_not_per_invocation():
    """Exercise D: prove the closure-factory claim from THEORY.md §4.

    Why this matters: in Week 3 the critic loop re-invokes nodes several
    times per run. If the client were rebuilt on every call you would
    pay that setup cost on every pass of the loop.

    Difficulty: hardest of the four, because the fake cannot do this
    yet. You have to CHANGE tests/conftest.py first. That is deliberate
    - real testing usually means improving your test tools, not just
    writing asserts.
    """
    # FIRST: open tests/conftest.py and add a counter to FakeChatModel.
    #   - initialise something like `self.bind_count = 0` in __init__
    #   - increment it inside with_structured_output
    #
    # ARRANGE
    # TODO: build ONE node from ONE fake

    # ACT
    # TODO: invoke that node three times with different queries

    # ASSERT
    # TODO: assert the fake recorded 3 calls   (it ran three times)
    # TODO: assert bind_count == 1             (but built the model once)
