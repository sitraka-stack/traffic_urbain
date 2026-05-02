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
        # Random offset to avoid synchronized jams
        import random
        self.traffic_lights[nid].t = random.uniform(0, 20)
        return nid

    def recalculate_traffic_light_phases(self, node_id: int):
        tl = self.traffic_lights.get(node_id)
        if not tl: return
        
        incomings = self.incoming_roads(node_id)
        if not incomings:
            tl.phases = []
            return

        # Simple heuristic: group roads by opposite angles
        # Or just cycle them one by one for safety
        # Better: group into 2 phases if possible (axes)
        import math
        roads_with_angles = []
        for rid in incomings:
            r = self.roads[rid]
            # Angle of arrival at node
            roads_with_angles.append((rid, r.angle_rad(self)))
        
        if len(incomings) <= 2:
            # All incoming can be green at once if just 2 (often same axis)
            tl.phases = [incomings]
        else:
            # Group by axes (roughly 180 degrees apart)
            phase1 = []
            phase2 = []
            
            # Use the first road as reference for axis 1
            ref_rid, ref_angle = roads_with_angles[0]
            phase1.append(ref_rid)
            
            for rid, angle in roads_with_angles[1:]:
                # diff from ref
                diff = abs((angle - ref_angle + math.pi) % (2 * math.pi) - math.pi)
                if diff < math.pi / 4 or diff > 3 * math.pi / 4: # Same or opposite axis
                    phase1.append(rid)
                else:
                    phase2.append(rid)
            
            if phase2:
                tl.phases = [phase1, phase2]
            else:
                tl.phases = [phase1]

    def move_node(self, node_id: int, x: float, y: float) -> None:
        n = self.nodes[node_id]
        n.x = x
        n.y = y

    def add_directed_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1 ) -> int:
        rid = self._next_road_id
        self._next_road_id += 1
        self.roads[rid] = DirectedRoad(id=rid, a=a, b=b, speed_limit=speed_limit, lanes=lanes)
        self.recalculate_traffic_light_phases(b)
        return rid

    def add_bidirectional_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1) -> Tuple[int, int]:
        rid_ab = self.add_directed_road(a, b, speed_limit=speed_limit, lanes=lanes)
        rid_ba = self.add_directed_road(b, a, speed_limit=speed_limit, lanes=lanes)

        key = (min(a, b), max(a, b))
        self.paired_roads[key] = (rid_ab, rid_ba)
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

    def create_roundabout(self, x: float, y: float, radius: float = 60.0, num_nodes: int = 8) -> List[int]:
        import math
        nids = []
        for i in range(num_nodes):
            angle = 2 * math.pi * i / num_nodes
            nx = x + radius * math.cos(angle)
            ny = y + radius * math.sin(angle)
            nids.append(self.add_node(nx, ny))

        rids = []
        for i in range(num_nodes):
            a = nids[i]
            b = nids[(i + 1) % num_nodes]
            # One way road in the circle
            rid = self.add_directed_road(a, b, lanes=1)
            # Roundabout priority
            self.roads[rid].priority = 2
            rids.append(rid)
        return rids