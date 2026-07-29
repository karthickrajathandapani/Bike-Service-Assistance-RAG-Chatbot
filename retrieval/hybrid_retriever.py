"""
Ensemble retriever: combines dense vector search with BM25 keyword search
for better recall than either alone (classic RAG improvement).
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import TOP_K_RETRIEVE, VECTOR_WEIGHT, BM25_WEIGHT
from ingestion.vector_store import vector_search, get_all_documents

_bm25_cache = {"key": None, "index": None, "docs": None}


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in text.split() if t.strip()]


def _build_bm25(vehicle_key: Optional[str]):
    from rank_bm25 import BM25Okapi

    docs = get_all_documents(vehicle_key=vehicle_key)
    corpus = [_tokenize(d["text"]) for d in docs]
    if not corpus:
        return None, []
    return BM25Okapi(corpus), docs


def _get_bm25(vehicle_key: Optional[str]):
    cache_key = vehicle_key or "__all__"
    if _bm25_cache["key"] != cache_key:
        index, docs = _build_bm25(vehicle_key)
        _bm25_cache.update({"key": cache_key, "index": index, "docs": docs})
    return _bm25_cache["index"], _bm25_cache["docs"]


def bm25_search(query: str, top_k: int, vehicle_key: Optional[str] = None) -> List[Dict]:
    bm25, docs = _get_bm25(vehicle_key)
    if bm25 is None:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:top_k]
    max_score = max((s for _, s in ranked), default=1) or 1
    return [
        {"id": d["id"], "text": d["text"], "metadata": d["metadata"], "score": s / max_score}
        for d, s in ranked
        if s > 0
    ]


def hybrid_search(
    query: str,
    top_k: int = TOP_K_RETRIEVE,
    vehicle_key: Optional[str] = None,
    vector_weight: float = VECTOR_WEIGHT,
    bm25_weight: float = BM25_WEIGHT,
) -> List[Dict]:
    """Reciprocal-weighted fusion of vector + BM25 results, deduplicated by chunk id."""
    vec_results = vector_search(query, top_k=top_k, vehicle_key=vehicle_key)
    bm_results = bm25_search(query, top_k=top_k, vehicle_key=vehicle_key)

    fused: Dict[str, Dict] = {}
    for r in vec_results:
        fused[r["id"]] = {**r, "fused_score": r["score"] * vector_weight}
    for r in bm_results:
        if r["id"] in fused:
            fused[r["id"]]["fused_score"] += r["score"] * bm25_weight
        else:
            fused[r["id"]] = {**r, "fused_score": r["score"] * bm25_weight}

    ranked = sorted(fused.values(), key=lambda x: x["fused_score"], reverse=True)
    return ranked[:top_k]
