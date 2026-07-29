"""
Loads PDF manuals from disk and extracts per-page text, guessing which
vehicle each manual belongs to so the bot can support multiple bikes.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from pypdf import PdfReader

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import KNOWN_VEHICLES, MANUALS_DIR


@dataclass
class PageText:
    manual_name: str
    vehicle_key: str
    page_number: int  # 1-indexed
    text: str


@dataclass
class LoadedManual:
    manual_name: str
    vehicle_key: str
    source_path: str
    pages: List[PageText] = field(default_factory=list)


def guess_vehicle_key(filename: str, sample_text: str) -> str:
    """Best-effort guess of which vehicle a manual belongs to, based on the
    filename and the first pages of text. Falls back to 'generic'."""
    haystack = f"{filename} {sample_text}".lower()
    for key, meta in KNOWN_VEHICLES.items():
        candidates = [key] + meta.get("aliases", [])
        for c in candidates:
            if c.lower() in haystack:
                return key
    # try to extract a model-looking token, e.g. "MTN155"
    match = re.search(r"\b([A-Z]{1,4}\d{2,4}[A-Z]?)\b", sample_text)
    if match:
        return match.group(1).lower()
    return "generic"


def load_pdf(path: Path) -> LoadedManual:
    reader = PdfReader(str(path))
    pages = []
    sample_text = ""
    for i, page in enumerate(reader.pages[:5]):
        sample_text += (page.extract_text() or "")
    vehicle_key = guess_vehicle_key(path.name, sample_text)

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = re.sub(r"[ \t]+", " ", text)
        pages.append(
            PageText(
                manual_name=path.stem,
                vehicle_key=vehicle_key,
                page_number=i + 1,
                text=text.strip(),
            )
        )
    return LoadedManual(
        manual_name=path.stem,
        vehicle_key=vehicle_key,
        source_path=str(path),
        pages=pages,
    )


def load_all_manuals(manuals_dir: Path = MANUALS_DIR) -> List[LoadedManual]:
    manuals = []
    for pdf_path in sorted(Path(manuals_dir).glob("*.pdf")):
        manuals.append(load_pdf(pdf_path))
    return manuals


if __name__ == "__main__":
    for m in load_all_manuals():
        print(f"{m.manual_name} -> vehicle_key={m.vehicle_key}, pages={len(m.pages)}")
