from __future__ import annotations
from dataclasses import dataclass
from math import atan2, sqrt
from typing import TYPE_CHECKING

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


@dataclass
class Vehicle:
    id: int
    road_id: int
    s: float = 0.0  # position along road [0..length]
    v: float = 10.0  # m/s
    lane: int = 0
    spawn_time: float = 0.0
    