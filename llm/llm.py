"""
Thin wrapper around the Anthropic Messages API. Centralizing the call here
means chains.py, query_rewriter.py, etc. don't need to know API details,
and swapping providers (e.g. to a local Llama model) only requires editing
this file.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE


def call_llm(
    system: Optional[str],
    user_message: str,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
    model: str = LLM_MODEL,
) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file to enable "
            "LLM-generated answers (see .env.example)."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": user_message}],
    )
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return "".join(block.text for block in response.content if block.type == "text")


def call_llm_stream(system: Optional[str], user_message: str, model: str = LLM_MODEL,
                     max_tokens: int = LLM_MAX_TOKENS, temperature: float = LLM_TEMPERATURE):
    """Generator yielding text deltas, for Streamlit's streaming chat UI."""
    if not ANTHROPIC_API_KEY:
        yield ("ANTHROPIC_API_KEY is not set. Add it to your .env file to enable "
               "LLM-generated answers (see .env.example).")
        return

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs = dict(model=model, max_tokens=max_tokens, temperature=temperature,
                  messages=[{"role": "user", "content": user_message}])
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text
