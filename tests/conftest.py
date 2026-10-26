"""
Shared test fixtures.

The whole point of this file is that the test suite makes **zero API
calls**. Tests that hit a real LLM are slow, cost money, need a key in
CI, and fail for reasons that have nothing to do with your code — a
rate limit is not a bug in your graph.

So we inject a fake model. `build_planner_node(llm=...)` and
`build_graph(planner_llm=..., researcher_llm=..., search=...)` accept them.
"""

import pytest
from langchain_core.messages import AIMessage


class FakeChatModel:
    """Stands in for ChatGoogleGenerativeAI.

    Implements the two methods the agents use: `with_structured_output`
    (planner) and plain `invoke` (researcher, which wants free text).
    For the planner, `with_structured_output(schema)` That returns an object with an
    `.invoke(messages)` method — which is exactly the contract the real
    LangChain runnable has. Understanding that contract is most of
    understanding structured output.

    It also records every call, so tests can assert on what the planner
    actually sent to the model, not just on what came back.
    """

    def __init__(self, subtasks=None, raises=None, answer=None):
        # what the fake model will "return" as its plan
        self.subtasks = subtasks if subtasks is not None else [
            "What does the enqueue_after_commit argument of frappe.enqueue do?",
            "How do Frappe developers delay a job until the DB commits?",
            "What errors occur when a job is enqueued before commit?",
            "Which Frappe versions support enqueue_after_commit?",
        ]
        # what plain .invoke() "returns" as text (the researcher's draft)
        self.answer = answer if answer is not None else (
            "Pass enqueue_after_commit=True to frappe.enqueue [1][2]."
        )
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

    def invoke(self, messages, **kwargs):
        self.calls.append(messages)
        if self.raises is not None:
            raise self.raises
        return AIMessage(content=self.answer)


@pytest.fixture
def fake_llm():
    """A fake model returning a sensible 4-item plan."""
    return FakeChatModel()


class FakeSearchClient:
    """Stands in for tavily.TavilyClient.

    Same idea as FakeChatModel: implements only `.search(query, **kwargs)`,
    returns a canned Tavily-shaped response, and records every call so
    tests can check what was sent — e.g. that the cheap search depth was
    used.
    """

    def __init__(self, results=None, raises=None):
        # Tavily-shaped results, including keys our tool should drop
        self.results = results if results is not None else [
            {
                "title": "frappe.enqueue - Frappe Docs",
                "url": "https://docs.frappe.io/framework/user/en/api/background_jobs",
                "content": "enqueue_after_commit: run the job only after commit.",
                "score": 0.91,
                "raw_content": None,
            },
            {
                "title": "Job runs before doc is saved - Frappe Forum",
                "url": "https://discuss.frappe.io/t/job-before-commit/1",
                "content": "The worker could not find the record.",
                "score": 0.74,
                "raw_content": None,
            },
        ]
        self.raises = raises
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.raises is not None:
            raise self.raises
        return {"query": query, "results": self.results, "response_time": 0.5}


@pytest.fixture
def fake_search_client():
    """A fake Tavily client returning two results."""
    return FakeSearchClient()
