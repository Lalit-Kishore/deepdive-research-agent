"""
Tests for app/llm.py: the shared rate limiter. Building the model object
makes no API call, so these run offline with a dummy key.
"""

from app import llm


def test_rate_limiter_paces_to_the_requested_rpm():
    limiter = llm.build_rate_limiter(5)

    assert limiter.requests_per_second == 5 / 60


def test_zero_rpm_turns_pacing_off():
    assert llm.build_rate_limiter(0) is None


def test_every_model_shares_one_limiter(monkeypatch):
    """Google counts calls per project, so two nodes must draw from ONE bucket.
    With a limiter per model, planner + researcher could each send 4/min."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key-for-tests")

    planner_model = llm.get_llm()
    researcher_model = llm.get_llm()

    assert planner_model.rate_limiter is llm.RATE_LIMITER
    assert researcher_model.rate_limiter is planner_model.rate_limiter
