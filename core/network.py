from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from .traffic_lights import TrafficLight
from .models import Node, DirectedRoad, Building


@dataclass
class RoadNetwork:
    nodes: Dict[int, Node] = field(default_factory=dict)
    roads: Dict[int, DirectedRoad] = field(default_factory=dict)
    buildings: Dict[int, Building] = field(default_factory=dict)
    traffic_lights: Dict[int, TrafficLight] = field(default_factory=dict)
    # dans RoadNetwork dataclass
    paired_roads: Dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)

    _next_node_id: int = 1
    _next_road_id: int = 1
    _next_building_id: int = 1

    # ... keep STREET_NAMES ...

    def add_building(self, x: float, y: float, w: float, h: float, angle: float, color: str = "") -> int:
        bid = self._next_building_id
        self._next_building_id += 1
        if not color:
            import random
            color = random.choice(["#dfe6e9", "#f7f1e3", "#f19066", "#f8a5c2", "#cf6a87"])
        self.buildings[bid] = Building(id=bid, x=x, y=y, width=w, height=h, angle=angle, color=color)
        return bid

    STREET_NAMES = [
        "Avenue de Paris", "Rue de la Paix", "Boulevard Saint-Germain", 
        "Rue de Rivoli", "Avenue des Champs-Élysées", "Rue Lafayette",
        "Boulevard Haussmann", "Rue de Rennes", "Avenue Foch",
        "Rue de Vaugirard", "Boulevard de Sébastopol", "Avenue Victor Hugo",
        "Rue de Châteaudun", "Boulevard Malesherbes", "Rue de Rome"
    ]

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

    def add_directed_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1, name: str = "" ) -> int:
        rid = self._next_road_id
        self._next_road_id += 1
        
        if not name:
            import random
            name = random.choice(self.STREET_NAMES)
            
        self.roads[rid] = DirectedRoad(id=rid, a=a, b=b, name=name, speed_limit=speed_limit, lanes=lanes)
        self.recalculate_traffic_light_phases(b)
        
        # Procedural buildings along the road
        self._generate_buildings_along_road(rid)
        
        return rid

    def _generate_buildings_along_road(self, road_id: int):
        import random
        import math
        road = self.roads[road_id]
        na, nb = self.nodes[road.a], self.nodes[road.b]
        
        L = road.length(self)
        if L < 30: return
        
        angle = road.angle_rad(self)
        nx, ny = -math.sin(angle), math.cos(angle) # Normal vector
        
        # Add buildings on both sides
        num_houses = int(L / 25)
        for i in range(num_houses):
            dist = i * 25 + 12
            # Base position on road
            bx = na.x + math.cos(angle) * dist
            by = na.y + math.sin(angle) * dist
            
            # Offset to side (outside lanes)
            from .models import LANE_WIDTH
            side_offset = (road.lanes * LANE_WIDTH) + random.uniform(15, 25)
            
            # Left side
            if random.random() < 0.7:
                self.add_building(bx + nx * side_offset, by + ny * side_offset, 
                                 random.uniform(15, 25), random.uniform(15, 25), 
                                 math.degrees(angle))
            
            # Right side
            if random.random() < 0.7:
                self.add_building(bx - nx * side_offset, by - ny * side_offset, 
                                 random.uniform(15, 25), random.uniform(15, 25), 
                                 math.degrees(angle))

    def add_bidirectional_road(self, a: int, b: int, speed_limit: float = 13.9, lanes: int = 1) -> Tuple[int, int]:
        import random
        name = random.choice(self.STREET_NAMES)
        
        rid_ab = self.add_directed_road(a, b, speed_limit=speed_limit, lanes=lanes, name=name)
        rid_ba = self.add_directed_road(b, a, speed_limit=speed_limit, lanes=lanes, name=name)

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
            rid = self.add_directed_road(a, b, lanes=2, name="Rond-point")
            # Roundabout priority
            self.roads[rid].priority = 2
            rids.append(rid)
        return rids

    def shortest_path(self, start_node: int, end_node: int) -> List[int]:
        """
        Dijkstra's algorithm to find the shortest path between two nodes.
        Returns a list of road IDs.
        """
        import heapq

        distances = {nid: float('inf') for nid in self.nodes}
        distances[start_node] = 0
        pq = [(0, start_node)]
        previous_road = {} # node_id -> road_id to get there
        previous_node = {} # node_id -> node_id to get there

        while pq:
            d, u = heapq.heappop(pq)
            if d > distances[u]:
                continue
            if u == end_node:
                break

            for rid in self.outgoing_roads(u):
                road = self.roads[rid]
                v = road.b
                weight = road.length(self)
                if distances[u] + weight < distances[v]:
                    distances[v] = distances[u] + weight
                    previous_road[v] = rid
                    previous_node[v] = u
                    heapq.heappush(pq, (distances[v], v))

        if end_node not in previous_node:
            return []

        path = []
        curr = end_node
        while curr != start_node:
            rid = previous_road[curr]
            path.append(rid)
            curr = previous_node[curr]

        return path[::-1]