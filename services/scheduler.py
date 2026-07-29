"""
Turns the raw maintenance schedule into a simple projected calendar, e.g.
"next 3 upcoming services from today's odometer reading", assuming an
average daily distance. Kept separate from maintenance.py so the due-item
logic and the forward-projection/calendar logic can evolve independently.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from services.maintenance import MAINTENANCE_SCHEDULE


@dataclass
class UpcomingService:
    name: str
    at_odometer_km: int
    estimated_date: date


def project_upcoming_services(
    current_odometer_km: int,
    avg_km_per_day: float = 25.0,
    horizon_count: int = 5,
) -> List[UpcomingService]:
    if avg_km_per_day <= 0:
        avg_km_per_day = 1.0

    upcoming = []
    for name, interval, _category in MAINTENANCE_SCHEDULE:
        next_due_km = ((current_odometer_km // interval) + 1) * interval
        km_away = next_due_km - current_odometer_km
        days_away = round(km_away / avg_km_per_day)
        upcoming.append(
            UpcomingService(
                name=name,
                at_odometer_km=next_due_km,
                estimated_date=date.today() + timedelta(days=days_away),
            )
        )

    upcoming.sort(key=lambda u: u.estimated_date)
    return upcoming[:horizon_count]
