"""
Cross-encoder reranker: takes the top-N candidates from hybrid retrieval and
re-scores them jointly with the query for much higher precision, then
returns only the top-K to send to the LLM.
"""
from __future__ import annotations
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import RERANKER_MODEL, TOP_K_FINAL, USE_RERANKER


@lru_cache(maxsize=1)
def get_reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANKER_MODEL)


def rerank(query: str, candidates: List[Dict], top_k: int = TOP_K_FINAL) -> List[Dict]:
    if not candidates:
        return []
    if not USE_RERANKER:
        return sorted(candidates, key=lambda c: c.get("fused_score", c.get("score", 0)),
                       reverse=True)[:top_k]

    model = get_reranker()
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return ranked[:top_k]
