"""
Service recommendation engine: given an odometer reading (and optionally a
vehicle key), tells the rider which maintenance items are due/overdue.

Uses a generic interval table modeled on typical small-displacement
motorcycle service schedules (matching the intervals described in the
uploaded manual: ~1000 km / 2 month first service, then recurring items).
Distances are in km; the table is intentionally generic across bikes since
exact tables differ per model/manual.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

# (item, interval_km, category) — category used for icons/grouping in the UI
MAINTENANCE_SCHEDULE = [
    ("Engine oil & filter", 1000, "engine"),
    ("Air filter element", 1000, "engine"),
    ("Spark plug check/clean", 1000, "engine"),
    ("Drive chain slack & lubrication", 500, "drivetrain"),
    ("Brake fluid level & pad check", 1000, "brakes"),
    ("Tire pressure & tread check", 500, "tires"),
    ("Clutch lever free play", 1000, "controls"),
    ("Battery voltage check", 1000, "electrical"),
    ("Coolant level check", 1000, "engine"),
    ("Brake fluid replacement", 20000, "brakes"),  # ~ every 2 years per manual
    ("Wheel bearing check", 10000, "wheels"),
    ("Steering bearing check", 10000, "chassis"),
]


@dataclass
class MaintenanceItem:
    name: str
    interval_km: int
    category: str
    km_since_last: int
    due: bool
    overdue_km: int


def get_due_items(current_odometer_km: int, last_service_km: Optional[int] = None) -> List[MaintenanceItem]:
    """
    current_odometer_km: the bike's current total odometer reading.
    last_service_km: odometer reading at the last full service (defaults to
    the last multiple of 1000 km below current, if not provided).
    """
    if last_service_km is None:
        last_service_km = (current_odometer_km // 1000) * 1000

    km_since_service = current_odometer_km - last_service_km
    items = []
    for name, interval, category in MAINTENANCE_SCHEDULE:
        km_since_item = current_odometer_km % interval if interval else km_since_service
        due = km_since_item >= interval * 0.9  # flag as "due soon" at 90% of interval
        overdue = max(0, km_since_item - interval)
        items.append(
            MaintenanceItem(
                name=name,
                interval_km=interval,
                category=category,
                km_since_last=int(km_since_item),
                due=due,
                overdue_km=int(overdue),
            )
        )
    return sorted(items, key=lambda i: i.km_since_last / i.interval_km, reverse=True)


if __name__ == "__main__":
    for item in get_due_items(8500):
        flag = "OVERDUE" if item.overdue_km > 0 else ("DUE SOON" if item.due else "ok")
        print(f"{item.name:35s} every {item.interval_km:>5} km  -> {flag}")
