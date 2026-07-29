"""
Shared logger config. Also records lightweight analytics (question text,
retrieval time, confidence) to a local JSONL file for the admin dashboard.
"""
from __future__ import annotations
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import BASE_DIR

LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_FILE = LOG_DIR / "analytics.jsonl"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_interaction(session_id: str, question: str, retrieval_time_s: float,
                     confidence: Optional[int], vehicle_key: Optional[str]):
    record = {
        "timestamp": time.time(),
        "session_id": session_id,
        "question": question,
        "retrieval_time_s": round(retrieval_time_s, 3),
        "confidence": confidence,
        "vehicle_key": vehicle_key,
    }
    with open(ANALYTICS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_analytics():
    if not ANALYTICS_FILE.exists():
        return []
    with open(ANALYTICS_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]
