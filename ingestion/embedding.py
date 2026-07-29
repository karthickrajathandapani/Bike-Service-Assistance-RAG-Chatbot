"""
Wraps a sentence-transformers model so the rest of the app doesn't need to
know which embedding model is in use. Swap EMBEDDING_MODEL in
config/settings.py to try e.g. BAAI/bge-small-en-v1.5.
"""
from __future__ import annotations
import sys
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384))
    model = get_embedder()
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def embed_query(query: str) -> np.ndarray:
    return embed_texts([query])[0]
