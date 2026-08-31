"""
Single place where the LLM is configured.

Every agent node (planner, researcher, critic) asks for its model
here instead of constructing one itself. When the model name changes
or a node needs different settings, this is the only file to touch.
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI

# Gemini 1.5 and 2.0 were retired on the free API; the deprecation
# response points at the 3.x flash line. See DEVLOG.md (2026-08-31).
DEFAULT_MODEL = os.getenv("DEEPDIVE_MODEL", "gemini-3.6-flash")


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

    return ChatGoogleGenerativeAI(**kwargs)
