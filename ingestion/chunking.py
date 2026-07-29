"""
Splits page text into overlapping chunks suitable for embedding, while
keeping track of which manual/page/paragraph each chunk came from (needed
for source citations later).
"""
from __future__ import annotations
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP
from ingestion.loader import LoadedManual


@dataclass
class Chunk:
    id: str
    manual_name: str
    vehicle_key: str
    page_number: int
    paragraph_index: int
    text: str


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple recursive-ish splitter: try paragraph boundaries first, then
    fall back to hard character windows for long paragraphs."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    paragraphs = re.split(r"\n{2,}|(?<=[.!?])\s{2,}", text)
    chunks, current = [], ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current} {para}".strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_size:
                # hard split long paragraph with overlap
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunks.append(para[start:end])
                    start = end - overlap
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def chunk_manual(manual: LoadedManual, chunk_size: int = CHUNK_SIZE,
                  overlap: int = CHUNK_OVERLAP) -> List[Chunk]:
    chunks: List[Chunk] = []
    for page in manual.pages:
        if not page.text.strip():
            continue
        pieces = _split_text(page.text, chunk_size, overlap)
        for para_idx, piece in enumerate(pieces):
            if len(piece.strip()) < 20:
                continue  # skip near-empty noise chunks
            chunk_id = f"{manual.vehicle_key}_p{page.page_number}_c{para_idx}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    manual_name=manual.manual_name,
                    vehicle_key=manual.vehicle_key,
                    page_number=page.page_number,
                    paragraph_index=para_idx,
                    text=piece.strip(),
                )
            )
    return chunks


def chunk_manuals(manuals: List[LoadedManual]) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for manual in manuals:
        all_chunks.extend(chunk_manual(manual))
    return all_chunks


if __name__ == "__main__":
    from ingestion.loader import load_all_manuals
    manuals = load_all_manuals()
    chunks = chunk_manuals(manuals)
    print(f"Total chunks: {len(chunks)}")
    if chunks:
        print(chunks[0])
