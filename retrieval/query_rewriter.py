"""
Rewrites short/ambiguous user queries (e.g. "oil?" or "what if I ride daily?")
into a clear, self-contained search query using conversation history.
Falls back to the raw query if no LLM key is configured, so the app still
works without an API key.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.prompt import QUERY_REWRITE_PROMPT
from config.settings import ANTHROPIC_API_KEY


def _format_history(history: List[Tuple[str, str]], max_turns: int = 4) -> str:
    if not history:
        return "(none)"
    recent = history[-max_turns:]
    return "\n".join(f"User: {u}\nAssistant: {a}" for u, a in recent)


def rewrite_query(query: str, history: List[Tuple[str, str]]) -> str:
    if not ANTHROPIC_API_KEY:
        return query  # heuristic fallback: search verbatim

    try:
        from llm.llm import call_llm
        prompt = QUERY_REWRITE_PROMPT.format(history=_format_history(history), query=query)
        rewritten = call_llm(system=None, user_message=prompt, max_tokens=100, temperature=0.0)
        rewritten = rewritten.strip().strip('"')
        return rewritten if rewritten else query
    except Exception:
        return query
