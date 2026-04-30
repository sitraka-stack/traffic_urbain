from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from .traffic_lights import TrafficLight
from .models import Node, DirectedRoad


@dataclass
class RoadNetwork:
    nodes: Dict[int, Node] = field(default_factory=dict)
    roads: Dict[int, DirectedRoad] = field(default_factory=dict)
    traffic_lights: Dict[int, TrafficLight] = field(default_factory=dict)
    # dans RoadNetwork dataclass
    paired_roads: Dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)

    _next_node_id: int = 1
    _next_road_id: int = 1

    def add_node(self, x: float, y: float) -> int:
        nid = self._next_node_id
        self._next_node_id += 1
        self.nodes[nid] = Node(id=nid, x=x, y=y)
        self.traffic_lights[nid] = TrafficLight(node_id=nid)
        return nid

    def move_node(self, node_id: int, x: float, y: float) -> None:
        n = self.nodes[node_id]
        n.x = x
        n.y = y

    def add_directed_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1 ) -> int:
        rid = self._next_road_id
        self._next_road_id += 1
        self.roads[rid] = DirectedRoad(id=rid, a=a, b=b, speed_limit=speed_limit, lanes=lanes)
        return rid

    def add_bidirectional_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1) -> Tuple[int, int]:
        rid_ab = self.add_directed_road(a, b, speed_limit=speed_limit, lanes=lanes)
        rid_ba = self.add_directed_road(b, a, speed_limit=speed_limit, lanes=lanes)

        # Store deterministically: key=(u,v) where u=min, v=max
        # paired_roads[(u,v)] = (rid_uv, rid_vu)
        u, v = min(a, b), max(a, b)
        key = (u, v)
        if a <= b:
            rid_uv, rid_vu = rid_ab, rid_ba  # rid_ab goes a->b = u->v
        else:
            rid_uv, rid_vu = rid_ba, rid_ab  # rid_ba goes b->a = u->v (since a>b means b<a=u)
        self.paired_roads[key] = (rid_uv, rid_vu)
        return rid_ab, rid_ba
    def outgoing_roads(self, node_id: int) -> List[int]:
        return [rid for rid, r in self.roads.items() if r.a == node_id]

    def incoming_roads(self, node_id: int) -> List[int]:
        return [rid for rid, r in self.roads.items() if r.b == node_id]

    def connected_roads(self, node_id: int) -> List[int]:
        # useful for refreshing road geometry when dragging a node
        out_ = self.outgoing_roads(node_id)
        inc_ = self.incoming_roads(node_id)
        # keep order deterministic
        return sorted(set(out_ + inc_))