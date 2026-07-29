"""
FastAPI backend for the Bike Service Assistant.

Run with:  uvicorn api:app --reload --port 8000
"""
from __future__ import annotations
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import APP_NAME, MANUALS_DIR
from ingestion.loader import load_all_manuals, load_pdf
from ingestion.chunking import chunk_manuals, chunk_manual
from ingestion.vector_store import index_chunks
from llm.chains import answer_question, suggest_followups
from services.maintenance import get_due_items
from services.diagnosis import diagnose
from services.recommendation import get_recommendations
from services.scheduler import project_upcoming_services
from utils.logger import get_logger, log_interaction, read_analytics
from utils.pdf_export import export_maintenance_report, export_diagnosis_report, export_service_checklist

logger = get_logger("api")
app = FastAPI(title=APP_NAME)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    vehicle_key: Optional[str] = None


class MaintenanceRequest(BaseModel):
    odometer_km: int
    last_service_km: Optional[int] = None
    avg_km_per_day: float = 25.0


class DiagnosisRequest(BaseModel):
    symptom: str
    vehicle_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Chat / RAG
# ---------------------------------------------------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    start = time.time()
    result = answer_question(req.query, session_id=req.session_id, vehicle_key=req.vehicle_key)
    result["followups"] = suggest_followups(req.query, result["answer"])
    log_interaction(
        req.session_id, req.query, time.time() - start, result.get("confidence"), result.get("vehicle_key")
    )
    return result


# ---------------------------------------------------------------------------
# Manual ingestion / upload
# ---------------------------------------------------------------------------
@app.post("/manuals/upload")
def upload_manual(file: UploadFile = File(...)):
    dest = Path(MANUALS_DIR) / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    manual = load_pdf(dest)
    chunks = chunk_manual(manual)
    count = index_chunks(chunks, reset=False)
    return {
        "filename": file.filename,
        "vehicle_key": manual.vehicle_key,
        "pages": len(manual.pages),
        "chunks_indexed": len(chunks),
        "collection_size": count,
    }


@app.post("/manuals/reindex")
def reindex_all():
    manuals = load_all_manuals()
    chunks = chunk_manuals(manuals)
    count = index_chunks(chunks, reset=True)
    return {"manuals": [m.manual_name for m in manuals], "total_chunks": len(chunks), "collection_size": count}


# ---------------------------------------------------------------------------
# Maintenance / diagnosis / recommendations
# ---------------------------------------------------------------------------
@app.post("/maintenance/due")
def maintenance_due(req: MaintenanceRequest):
    items = get_due_items(req.odometer_km, req.last_service_km)
    return {"items": [i.__dict__ for i in items]}


@app.post("/maintenance/upcoming")
def maintenance_upcoming(req: MaintenanceRequest):
    items = project_upcoming_services(req.odometer_km, req.avg_km_per_day)
    return {"upcoming": [{"name": i.name, "at_odometer_km": i.at_odometer_km,
                           "estimated_date": i.estimated_date.isoformat()} for i in items]}


@app.post("/diagnose")
def diagnose_fault(req: DiagnosisRequest):
    return diagnose(req.symptom, vehicle_key=req.vehicle_key)


@app.get("/recommendations")
def recommendations(vehicle_key: Optional[str] = None):
    return get_recommendations(vehicle_key)


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------
@app.post("/export/maintenance")
def export_maintenance(req: MaintenanceRequest):
    items = get_due_items(req.odometer_km, req.last_service_km)
    path = export_maintenance_report(req.odometer_km, items)
    return FileResponse(path, filename=path.name)


@app.post("/export/diagnosis")
def export_diagnosis(req: DiagnosisRequest):
    result = diagnose(req.symptom, vehicle_key=req.vehicle_key)
    path = export_diagnosis_report(req.symptom, result["answer"])
    return FileResponse(path, filename=path.name)


@app.post("/export/checklist")
def export_checklist(req: MaintenanceRequest):
    items = get_due_items(req.odometer_km, req.last_service_km)
    path = export_service_checklist(items)
    return FileResponse(path, filename=path.name)


# ---------------------------------------------------------------------------
# Analytics (for the admin dashboard)
# ---------------------------------------------------------------------------
@app.get("/analytics")
def analytics():
    return {"records": read_analytics()}


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}
