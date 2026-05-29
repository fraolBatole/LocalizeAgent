"""LLM factory for LangGraph agents."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    model = (
        os.getenv("MODEL")
        or os.getenv("OPENAI_MODEL_NAME")
        or "gpt-4o-mini"
    )
    return ChatOpenAI(model=model, temperature=0)
