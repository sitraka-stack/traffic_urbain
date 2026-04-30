from __future__ import annotations
from typing import Dict
from core.models import Vehicle


def vehicle_count(vehicles: Dict[int, Vehicle]) -> int:
    return len(vehicles)


def avg_speed(vehicles: Dict[int, Vehicle]) -> float:
    if not vehicles:
        return 0.0
    return sum(v.v for v in vehicles.values()) / len(vehicles)