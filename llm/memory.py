"""
Lightweight conversation memory. Keeps a rolling buffer of (user, assistant)
turns per session id, used to give the query rewriter and LLM context (e.g.
"When should I change engine oil?" -> "What if I ride daily?").
"""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Tuple

MAX_TURNS = 12


class ConversationMemory:
    def __init__(self):
        self._sessions: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        return self._sessions[session_id]

    def add_turn(self, session_id: str, user_message: str, assistant_message: str):
        history = self._sessions[session_id]
        history.append((user_message, assistant_message))
        if len(history) > MAX_TURNS:
            self._sessions[session_id] = history[-MAX_TURNS:]

    def clear(self, session_id: str):
        self._sessions[session_id] = []


# Single process-wide instance (fine for a demo app; swap for Redis/DB in prod)
memory_store = ConversationMemory()
