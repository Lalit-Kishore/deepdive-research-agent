"""
Shared test fixtures.

The whole point of this file is that the test suite makes **zero API
calls**. Tests that hit a real LLM are slow, cost money, need a key in
CI, and fail for reasons that have nothing to do with your code — a
rate limit is not a bug in your graph.

So we inject a fake model. `build_planner_node(llm=...)` and
`build_graph(planner_llm=...)` both accept one.
"""

import pytest


class FakeChatModel:
    """Stands in for ChatGoogleGenerativeAI.

    Only implements the one method the planner actually uses:
    `with_structured_output(schema)`. That returns an object with an
    `.invoke(messages)` method — which is exactly the contract the real
    LangChain runnable has. Understanding that contract is most of
    understanding structured output.

    It also records every call, so tests can assert on what the planner
    actually sent to the model, not just on what came back.
    """

    def __init__(self, subtasks=None, raises=None):
        # what the fake model will "return" as its plan
        self.subtasks = subtasks if subtasks is not None else [
            "What drove the fund's 3-year returns?",
            "How does its expense ratio compare to peers?",
            "What is the fund manager's track record?",
            "What is the portfolio concentration risk?",
        ]
        # set to an Exception instance to simulate an API failure
        self.raises = raises

        # call recorder
        self.bound_schema = None
        self.calls = []

    def with_structured_output(self, schema):
        outer = self
        outer.bound_schema = schema

        class _Bound:
            def invoke(self, messages, **kwargs):
                outer.calls.append(messages)
                if outer.raises is not None:
                    raise outer.raises
                return schema(subtasks=outer.subtasks)

        return _Bound()


@pytest.fixture
def fake_llm():
    """A fake model returning a sensible 4-item plan."""
    return FakeChatModel()
