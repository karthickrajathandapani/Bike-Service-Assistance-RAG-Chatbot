"""
Generates simple PDF reports (maintenance report, diagnosis report, service
checklist) using reportlab, so the user has something to download/print.
"""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import EXPORT_DIR
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _new_canvas(filename: str):
    path = EXPORT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    return c, width, height, path


def export_maintenance_report(odometer_km: int, items) -> Path:
    c, width, height, path = _new_canvas(f"maintenance_report_{date.today()}.pdf")
    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Maintenance Report")
    y -= 1 * cm
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Generated: {date.today()}    Odometer: {odometer_km} km")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Item")
    c.drawString(10 * cm, y, "Interval (km)")
    c.drawString(14 * cm, y, "Status")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    for item in items:
        status = "OVERDUE" if item.overdue_km > 0 else ("DUE SOON" if item.due else "OK")
        c.drawString(2 * cm, y, item.name)
        c.drawString(10 * cm, y, str(item.interval_km))
        c.drawString(14 * cm, y, status)
        y -= 0.55 * cm
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm

    c.save()
    return path


def export_diagnosis_report(symptom: str, answer: str) -> Path:
    c, width, height, path = _new_canvas(f"diagnosis_report_{date.today()}.pdf")
    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Diagnosis Report")
    y -= 1 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, f"Symptom: {symptom}")
    y -= 0.8 * cm
    c.setFont("Helvetica", 10)
    for line in _wrap_text(answer, 95):
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
    c.save()
    return path


def export_service_checklist(items) -> Path:
    c, width, height, path = _new_canvas(f"service_checklist_{date.today()}.pdf")
    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Service Checklist")
    y -= 1 * cm
    c.setFont("Helvetica", 11)
    for item in items:
        c.rect(2 * cm, y - 0.3 * cm, 0.4 * cm, 0.4 * cm)
        c.drawString(2.8 * cm, y, f"{item.name}  (every {item.interval_km} km)")
        y -= 0.7 * cm
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
    c.save()
    return path


def _wrap_text(text: str, width: int) -> List[str]:
    words = text.split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 <= width:
            current = f"{current} {w}".strip()
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines
