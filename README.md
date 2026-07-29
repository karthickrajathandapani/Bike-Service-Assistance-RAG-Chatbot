# 🏍️ Bike Service Assistant — RAG Chatbot

A retrieval-augmented generation (RAG) assistant for motorcycle owner's
manuals: ask natural-language questions and get answers grounded in the
actual manual, with page-level citations, a confidence score, service
recommendations, and fault diagnosis.

Comes pre-loaded with the Yamaha MT-15 (MTN155) owner's manual as a sample.

## What's implemented

| Feature | Status |
|---|---|
| PDF ingestion + chunking | ✅ |
| Multi-manual / multi-bike support (auto vehicle detection) | ✅ |
| Hybrid retrieval (BM25 + vector, ChromaDB) | ✅ |
| Cross-encoder reranking | ✅ |
| Query rewriting using conversation history | ✅ |
| Conversation memory | ✅ |
| Source citations (manual, page, similarity score) | ✅ |
| Confidence score (LLM self-reported + heuristic fallback) | ✅ |
| Service recommendation (by odometer reading) | ✅ |
| Fault diagnosis (symptom → likely causes + fixes) | ✅ |
| Parts/consumables recommendation | ✅ |
| PDF export (maintenance report / diagnosis report / checklist) | ✅ |
| Streamlit UI (chat, sidebar, history, suggested questions) | ✅ |
| FastAPI backend | ✅ |
| Admin analytics (most-asked Qs, retrieval time, confidence dist.) | ✅ |
| Upload new manuals from the UI | ✅ |
| Voice assistant (Whisper STT / TTS) | 🚧 not implemented — see below |
| OCR for photographed manual pages | 🚧 not implemented — see below |
| Image understanding (dashboard warning lights) | 🚧 not implemented — see below |

The three 🚧 items are genuinely separate subsystems (audio I/O, OCR,
vision) rather than RAG-pipeline work, so they were left as clearly-marked
extension points rather than half-built. Notes on how to add each are in
"Extending" below.

## Quick start

```bash
cd bike-service-assistant-rag-chatbot
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
# (the app also runs without a key, in retrieval-only mode)

# 1. Ingest the sample manual(s) in data/manuals/ into the vector store
python -m ingestion.vector_store  # or trigger via the script below
python - <<'EOF'
from ingestion.loader import load_all_manuals
from ingestion.chunking import chunk_manuals
from ingestion.vector_store import index_chunks
manuals = load_all_manuals()
chunks = chunk_manuals(manuals)
index_chunks(chunks, reset=True)
print(f"Indexed {len(chunks)} chunks from {len(manuals)} manual(s)")
EOF

# 2. Run the backend (optional — the Streamlit app can also call the
#    Python modules directly without the API running)
uvicorn api:app --reload --port 8000

# 3. Run the UI
streamlit run app.py
```

## Architecture

```
User
  │
Streamlit Frontend (app.py)  ──or──  FastAPI Backend (api.py)
  │
Query Rewriter (retrieval/query_rewriter.py)
  │
Hybrid Retriever — BM25 + Vector (retrieval/hybrid_retriever.py)
  │
Cross-Encoder Reranker (retrieval/reranker.py)
  │
Top Relevant Context Chunks + Citations (retrieval/citation.py)
  │
Conversation Memory (llm/memory.py)
  │
Claude (llm/llm.py)
  │
Answer + Citations + Confidence + Follow-ups
```

## Configuration

All tunables live in `config/settings.py` and can be overridden via `.env`
(see `.env.example`): embedding model, reranker model, chunk size/overlap,
retrieval weights, top-k values, and the LLM model/temperature.

## Extending

- **Multi-manual support**: drop any new PDF into `data/manuals/` (or use
  the "Upload Manual" page) — the vehicle is auto-detected from filename +
  content via `config.settings.KNOWN_VEHICLES` plus a regex fallback.
- **Better embeddings**: change `EMBEDDING_MODEL` to e.g.
  `BAAI/bge-small-en-v1.5` in `.env`.
- **Production vector DB**: swap `ingestion/vector_store.py`'s Chroma calls
  for a Pinecone client — the rest of the retrieval pipeline is agnostic to
  the backing store.
- **Voice assistant**: add a `services/voice.py` that pipes mic input
  through a Whisper client into `llm.chains.answer_question`, then a TTS
  call on the answer text; wire a "🎙️ Speak" button into `app.py`.
- **OCR**: add `ingestion/ocr_loader.py` using `pytesseract` on
  page images (e.g. via `pdf2image`) for scanned/photographed pages, then
  feed the extracted text into the existing `chunking.py`.
- **Image understanding (dashboard lights)**: add a
  `services/image_diagnosis.py` that sends an uploaded photo + a prompt to
  a vision-capable Claude call (`llm/llm.py` already wraps the Anthropic
  client, so this just needs an `image` content block).

## Project layout

```
bike-service-assistant-rag-chatbot/
├── app.py                # Streamlit UI
├── api.py                # FastAPI backend
├── requirements.txt
├── .env.example
├── config/                # settings + prompt templates
├── data/manuals/           # PDF manuals (sample: Yamaha MT-15)
├── ingestion/              # load → chunk → embed → vector store
├── retrieval/              # hybrid search → rerank → rewrite → citations
├── llm/                    # LLM client, RAG chain orchestration, memory
├── services/               # maintenance, diagnosis, recommendations, scheduler
├── utils/                  # logging/analytics, helpers, PDF export
└── database/chroma_db/     # persisted vector store (generated)
```
