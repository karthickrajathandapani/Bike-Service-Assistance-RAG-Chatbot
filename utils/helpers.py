"""Small shared helper functions used across the app."""
from __future__ import annotations
import uuid


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def truncate(text: str, max_len: int = 200) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def confidence_badge(confidence: int) -> str:
    if confidence >= 80:
        return "🟢 High"
    if confidence >= 50:
        return "🟡 Medium"
    return "🔴 Low"
