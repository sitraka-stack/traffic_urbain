from __future__ import annotations
from dataclasses import dataclass, field
from math import atan2, sqrt
from typing import TYPE_CHECKING, List, Optional

LANE_WIDTH = 12.0  # pixels

if TYPE_CHECKING:
    from .network import RoadNetwork


@dataclass
class Node:
    id: int
    x: float
    y: float


@dataclass
class DirectedRoad:
    id: int
    a: int  # from node id
    b: int  # to node id
    name: str = ""
    speed_limit: float = 13.9  # m/s (~50 km/h)
    lanes: int = 1
    priority: int = 0  # 0: normal, 1: priority road, -1: yield/stop

    def length(self, net: "RoadNetwork") -> float:
        na = net.nodes[self.a]
        nb = net.nodes[self.b]
        dx = nb.x - na.x
        dy = nb.y - na.y
        return sqrt(dx * dx + dy * dy)

    def angle_rad(self, net: "RoadNetwork") -> float:
        na = net.nodes[self.a]
        nb = net.nodes[self.b]
        return atan2(nb.y - na.y, nb.x - na.x)


from enum import Enum, auto

class VehicleType(Enum):
    CAR = auto()
    TRUCK = auto()
    BUS = auto()
    MOTORCYCLE = auto()

@dataclass
class Vehicle:
    id: int
    road_id: int
    type: VehicleType = VehicleType.CAR
    s: float = 0.0  # position along road [0..length]
    v: float = 10.0  # m/s
    lane: int = 0
    spawn_time: float = 0.0
    color: str = "blue"
    
    # Navigation
    path: List[int] = field(default_factory=list) # List of road IDs
    target_node: Optional[int] = None
    
    # Physics properties (set based on type)
    length: float = 5.0
    max_accel: float = 1.5
    max_decel: float = 3.0
    v_target: float = 13.9 # default 50km/h
    
    def __post_init__(self):
        if self.type == VehicleType.TRUCK:
            self.length = 12.0
            self.max_accel = 0.8
            self.max_decel = 2.0
        elif self.type == VehicleType.BUS:
            self.length = 10.0
            self.max_accel = 1.0
            self.max_decel = 2.5
        elif self.type == VehicleType.MOTORCYCLE:
            self.length = 2.0
            self.max_accel = 2.5
            self.max_decel = 4.0
    