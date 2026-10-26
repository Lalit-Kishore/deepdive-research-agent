"""
Single place where the LLM is configured.

Every agent node (planner, researcher, critic) asks for its model
here instead of constructing one itself. When the model name changes
or a node needs different settings, this is the only file to touch.
"""

import os

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

# Gemini 1.5 and 2.0 were retired on the free API; the deprecation
# response points at the 3.x flash line. See DEVLOG.md (2026-08-31).
DEFAULT_MODEL = os.getenv("DEEPDIVE_MODEL", "gemini-3.6-flash")

# Gemini calls allowed per minute, across ALL nodes. The free tier is
# 5 RPM, so the default leaves one call of headroom. Raise it in .env
# to match your tier once billing is on; 0 turns pacing off.
DEFAULT_RPM = float(os.getenv("DEEPDIVE_RPM", "4"))


def build_rate_limiter(rpm: float) -> InMemoryRateLimiter | None:
    """Token bucket that releases one call every 60/rpm seconds.

    A call waits for a token before it is sent; the model itself runs
    at normal speed. The bucket starts empty, so the very first call
    also waits one interval (15s at 4 RPM).
    """
    if rpm <= 0:
        return None
    return InMemoryRateLimiter(
        requests_per_second=rpm / 60,
        check_every_n_seconds=0.1,
    )


# One limiter shared by every model get_llm() builds. Google counts
# calls per project, not per node, so the pacing has to be shared too.
# Retries are NOT added here: the Gemini client already retries
# 429/5xx itself, up to 6 attempts with backoff (DEVLOG Issue #10).
RATE_LIMITER = build_rate_limiter(DEFAULT_RPM)


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Build a Gemini chat model.

    temperature is left unset by default: the 3.x flash models use
    fixed sampling and warn if you pass one. Pass it explicitly only
    when running against an older model that honours it.
    """
    kwargs: dict = {"model": model or DEFAULT_MODEL}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if RATE_LIMITER is not None:
        kwargs["rate_limiter"] = RATE_LIMITER

    return ChatGoogleGenerativeAI(**kwargs)
