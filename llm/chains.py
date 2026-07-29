"""
Orchestrates the full RAG pipeline: query rewrite -> hybrid retrieval ->
rerank -> LLM generation with citations, confidence, and follow-ups.
This is the main entry point used by both api.py and app.py.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.prompt import RAG_SYSTEM_PROMPT, FOLLOWUP_PROMPT
from config.settings import ANTHROPIC_API_KEY, TOP_K_RETRIEVE, TOP_K_FINAL
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from retrieval.query_rewriter import rewrite_query
from retrieval.citation import build_context_block, build_citations, estimate_confidence
from llm.memory import memory_store
from llm.llm import call_llm


def _detect_vehicle_key(query: str) -> Optional[str]:
    from config.settings import KNOWN_VEHICLES
    q = query.lower()
    for key, meta in KNOWN_VEHICLES.items():
        if key in q or any(alias in q for alias in meta.get("aliases", [])):
            return key
    return None


def _parse_confidence(answer: str, fallback: int) -> (str, int):
    match = re.search(r"CONFIDENCE:\s*(\d{1,3})", answer)
    if match:
        clean_answer = answer[: match.start()].strip()
        return clean_answer, min(100, int(match.group(1)))
    return answer.strip(), fallback


def answer_question(query: str, session_id: str = "default",
                     vehicle_key: Optional[str] = None) -> Dict:
    history = memory_store.get_history(session_id)

    # 1. Query rewriting (uses conversation memory for context)
    rewritten_query = rewrite_query(query, history)

    # 2. Auto-detect which manual/vehicle to search, if not specified
    detected_vehicle = vehicle_key or _detect_vehicle_key(query) or _detect_vehicle_key(rewritten_query)

    # 3. Hybrid retrieval (BM25 + vector)
    candidates = hybrid_search(rewritten_query, top_k=TOP_K_RETRIEVE, vehicle_key=detected_vehicle)

    # If nothing found for a specific vehicle, retry across all manuals
    if not candidates and detected_vehicle:
        candidates = hybrid_search(rewritten_query, top_k=TOP_K_RETRIEVE, vehicle_key=None)

    # 4. Cross-encoder rerank down to the final top-k
    top_chunks = rerank(rewritten_query, candidates, top_k=TOP_K_FINAL)

    context_block = build_context_block(top_chunks)
    citations = build_citations(top_chunks)
    heuristic_confidence = estimate_confidence(top_chunks)

    if not ANTHROPIC_API_KEY:
        answer = (
            "I found some relevant manual excerpts below, but no ANTHROPIC_API_KEY "
            "is configured, so I can't generate a natural-language answer yet. "
            "Add your key to .env to enable full responses."
        )
        confidence = heuristic_confidence if top_chunks else 0
    else:
        system_prompt = RAG_SYSTEM_PROMPT.format(context=context_block or "(no relevant context found)")
        try:
            raw_answer = call_llm(system=system_prompt, user_message=rewritten_query)
            answer, confidence = _parse_confidence(raw_answer, heuristic_confidence)
        except Exception as e:
            answer = f"Sorry, I couldn't generate an answer right now ({e})."
            confidence = 0

    memory_store.add_turn(session_id, query, answer)

    return {
        "query": query,
        "rewritten_query": rewritten_query,
        "vehicle_key": detected_vehicle,
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
    }


def suggest_followups(query: str, answer: str) -> List[str]:
    if not ANTHROPIC_API_KEY:
        return []
    try:
        raw = call_llm(system=None, user_message=FOLLOWUP_PROMPT.format(query=query, answer=answer),
                        max_tokens=150, temperature=0.4)
        lines = [re.sub(r"^\s*\d+[\).]?\s*", "", l).strip() for l in raw.splitlines() if l.strip()]
        return lines[:3]
    except Exception:
        return []
