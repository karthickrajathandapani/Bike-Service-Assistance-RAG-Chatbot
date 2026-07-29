"""
Central configuration for the Bike Service Assistant RAG Chatbot.
All values can be overridden via environment variables (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Directories -------------------------------------------------------
MANUALS_DIR = BASE_DIR / "data" / "manuals"
CHROMA_DIR = BASE_DIR / "database" / "chroma_db"
EXPORT_DIR = BASE_DIR / "data" / "exports"
MANUALS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# --- Embeddings ----------------------------------------------------------
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Reranker ------------------------------------------------------------
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() == "true"

# --- Retrieval -------------------------------------------------------------
TOP_K_RETRIEVE = int(os.getenv("TOP_K_RETRIEVE", 20))   # candidates before rerank
TOP_K_FINAL = int(os.getenv("TOP_K_FINAL", 5))          # chunks sent to the LLM
VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", 0.6))  # ensemble weight (vector vs BM25)
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", 0.4))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 120))

# --- LLM -------------------------------------------------------------------
# Uses the Anthropic API by default. Set ANTHROPIC_API_KEY in your .env.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1024))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))

# --- App ---------------------------------------------------------------
APP_NAME = "Bike Service Assistant"
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_BASE_URL = os.getenv("API_BASE_URL", f"http://localhost:{API_PORT}")

# Multi-manual routing: maps a short "vehicle key" -> manual metadata.
# The ingestion pipeline auto-registers whatever it finds in data/manuals/,
# this dict is only used for nicer display names / aliases.
KNOWN_VEHICLES = {
    "mt15": {"display_name": "Yamaha MT-15", "aliases": ["mt-15", "mt 15", "mtn155"]},
    "r15": {"display_name": "Yamaha R15", "aliases": ["r-15", "r 15"]},
    "fz": {"display_name": "Yamaha FZ", "aliases": ["fz-s", "fz s"]},
}
