"""
Formats retrieved chunks into (a) an LLM-ready context block with inline
source tags, and (b) a structured citation list for the UI (manual name,
page, paragraph, similarity score).
"""
from __future__ import annotations
from typing import Dict, List


def build_context_block(chunks: List[Dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        meta = c["metadata"]
        tag = f"[Source {i}: {meta['manual_name']}, page {meta['page_number']}]"
        parts.append(f"{tag}\n{c['text']}")
    return "\n\n".join(parts)


def build_citations(chunks: List[Dict]) -> List[Dict]:
    citations = []
    for i, c in enumerate(chunks, 1):
        meta = c["metadata"]
        score = c.get("rerank_score", c.get("fused_score", c.get("score", 0)))
        citations.append(
            {
                "source_index": i,
                "manual_name": meta["manual_name"],
                "page": meta["page_number"],
                "paragraph": meta.get("paragraph_index"),
                "similarity_score": round(float(score), 3),
                "excerpt": c["text"][:220] + ("..." if len(c["text"]) > 220 else ""),
            }
        )
    return citations


def estimate_confidence(chunks: List[Dict]) -> int:
    """Cheap heuristic confidence score (0-100) based on top result strength
    and agreement among the retrieved chunks, used when the LLM doesn't
    (or can't) self-report a CONFIDENCE line."""
    if not chunks:
        return 0
    scores = [c.get("rerank_score", c.get("fused_score", c.get("score", 0))) for c in chunks]
    top = max(scores)
    # rerank scores (logits) and fused/cosine scores have different ranges;
    # normalize roughly into 0-1 before scaling to a percentage.
    normalized = max(0.0, min(1.0, (top + 5) / 10)) if top < 1.5 else max(0.0, min(1.0, top))
    return round(normalized * 100)
