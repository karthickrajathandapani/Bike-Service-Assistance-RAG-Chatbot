"""
Thin wrapper around ChromaDB (persistent, local) for storing/retrieving
manual chunks by embedding similarity.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import CHROMA_DIR
from ingestion.chunking import Chunk
from ingestion.embedding import embed_texts, embed_query

COLLECTION_NAME = "bike_manuals"


def _get_client():
    import chromadb
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection():
    client = _get_client()
    return client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def reset_collection():
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def index_chunks(chunks: List[Chunk], batch_size: int = 64, reset: bool = False):
    collection = reset_collection() if reset else get_collection()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = embed_texts([c.text for c in batch])
        collection.add(
            ids=[c.id for c in batch],
            embeddings=[e.tolist() for e in embeddings],
            documents=[c.text for c in batch],
            metadatas=[
                {
                    "manual_name": c.manual_name,
                    "vehicle_key": c.vehicle_key,
                    "page_number": c.page_number,
                    "paragraph_index": c.paragraph_index,
                }
                for c in batch
            ],
        )
    return collection.count()


def vector_search(query: str, top_k: int = 20, vehicle_key: Optional[str] = None) -> List[Dict]:
    collection = get_collection()
    query_emb = embed_query(query).tolist()
    where = {"vehicle_key": vehicle_key} if vehicle_key else None
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        where=where,
    )
    out = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    for id_, doc, meta, dist in zip(ids, docs, metas, dists):
        similarity = 1 - dist  # cosine distance -> similarity
        out.append({"id": id_, "text": doc, "metadata": meta, "score": similarity})
    return out


def get_all_documents(vehicle_key: Optional[str] = None) -> List[Dict]:
    """Fetch the full corpus (used to build the BM25 index)."""
    collection = get_collection()
    where = {"vehicle_key": vehicle_key} if vehicle_key else None
    results = collection.get(where=where, include=["documents", "metadatas"])
    out = []
    for id_, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        out.append({"id": id_, "text": doc, "metadata": meta})
    return out
