from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from collections import defaultdict

from .models import Vehicle
from .network import RoadNetwork


@dataclass
class SimulationEngine:
    net: RoadNetwork
    vehicles: Dict[int, Vehicle] = field(default_factory=dict)

    _next_vehicle_id: int = 1
    spawn_rate: float = 0.4  # vehicles per second (simple MVP)
    rng: random.Random = field(default_factory=random.Random)
    
    current_time: float = 0.0
    total_finished: int = 0
    total_travel_time: float = 0.0

    def reset(self) -> None:
        self.vehicles.clear()
        self._next_vehicle_id = 1
        self.current_time = 0.0
        self.total_finished = 0
        self.total_travel_time = 0.0

    def _pick_random_road(self) -> Optional[int]:
        if not self.net.roads:
            return None
        
        # Un point d'entrée est une route dont le noeud de départ 'a' n'a aucune route entrante
        # OU une route marquée comme non-prioritaire (pour éviter les ronds-points)
        entry_roads = []
        for rid, r in self.net.roads.items():
            # Pas dans un rond-point
            if r.priority >= 2:
                continue
            
            # Pas de routes qui entrent dans le noeud de départ = vrai point d'entrée
            incomings_to_a = self.net.incoming_roads(r.a)
            if not incomings_to_a:
                entry_roads.append(rid)
        
        # Si aucun vrai point d'entrée n'est trouvé, on prend n'importe quelle route hors rond-point
        if not entry_roads:
            entry_roads = [rid for rid, r in self.net.roads.items() if r.priority < 2]
            
        if not entry_roads:
            return None
            
        return self.rng.choice(entry_roads)

    def get_advanced_metrics(self) -> Dict:
        if not self.vehicles:
            return {
                "count": 0,
                "avg_speed": 0.0,
                "waiting_count": 0,
                "congestion_level": "Fluide",
                "total_finished": self.total_finished,
                "avg_travel_time": self.total_travel_time / self.total_finished if self.total_finished > 0 else 0.0,
                "busiest_road": "Aucune"
            }
        
        speeds = [v.v for v in self.vehicles.values()]
        avg_v = sum(speeds) / len(speeds)
        
        # On considère qu'un véhicule attend s'il roule à moins de 0.5 m/s
        waiting = [v for v in self.vehicles.values() if v.v < 0.5]
        waiting_count = len(waiting)
        
        # Niveau de congestion
        ratio = waiting_count / len(self.vehicles)
        if ratio < 0.1: congestion = "Fluide"
        elif ratio < 0.3: congestion = "Modéré"
        elif ratio < 0.6: congestion = "Dense"
        else: congestion = "Bouchon"
        
        # Route la plus chargée
        counts = defaultdict(int)
        for v in self.vehicles.values():
            counts[v.road_id] += 1
        busiest_id = max(counts, key=counts.get) if counts else "Aucune"

        return {
            "count": len(self.vehicles),
            "avg_speed": avg_v,
            "waiting_count": waiting_count,
            "congestion_level": congestion,
            "total_finished": self.total_finished,
            "avg_travel_time": self.total_travel_time / self.total_finished if self.total_finished > 0 else 0.0,
            "busiest_road": f"ID {busiest_id}" if busiest_id != "Aucune" else "Aucune"
        }

    def _spawn_vehicle(self) -> None:
        road_id = self._pick_random_road()
        if road_id is None:
            return

        lanes = max(1, self.net.roads[road_id].lanes)
        lane = self.rng.randrange(lanes)

        # Space check: ensure no vehicle is in the way (first 10m)
        SAFE_SPAWN_DIST = 8.0
        for veh in self.vehicles.values():
            if veh.road_id == road_id and veh.lane == lane and veh.s < SAFE_SPAWN_DIST:
                return # Blocked, don't spawn magically on top of each other

        vid = self._next_vehicle_id
        self._next_vehicle_id += 1

        speed_limit = self.net.roads[road_id].speed_limit
        v = max(2.0, min(speed_limit, self.rng.uniform(6.0, speed_limit)))

        self.vehicles[vid] = Vehicle(id=vid, road_id=road_id, s=0.0, v=v, lane=lane, spawn_time=self.current_time)
    
    def step(self, dt: float) -> None:
        self.current_time += dt
        # 1. Count vehicles per road for adaptive traffic lights
        road_counts = defaultdict(int)
        for v in self.vehicles.values():
            road_counts[v.road_id] += 1

        # 2. Update traffic lights
        for tl in self.net.traffic_lights.values():
            tl.step(dt, road_counts)

        # 3. Spawn
        if dt > 0 and self.net.roads:
            p = min(1.0, self.spawn_rate * dt)
            if self.rng.random() < p:
                self._spawn_vehicle()

        # 4. Group vehicles
        by_road_lane = defaultdict(list)
        for veh in self.vehicles.values():
            by_road_lane[(veh.road_id, veh.lane)].append(veh)

        # IDM Parameters
        v0 = 13.9    # target speed (m/s)
        T = 1.5      # safe time headway (s)
        a_max = 1.5  # max acceleration (m/s^2)
        b_comf = 2.0 # comfortable braking (m/s^2)
        delta = 4    # acceleration exponent
        s0 = 4.0     # linear jam distance (m)

        def get_idm_accel(v, v_target, s_front, v_front):
            # Intelligent Driver Model
            alpha = (v / v_target)**delta if v_target > 0 else 1.0
            
            s_star = s0 + max(0.0, v * T + (v * (v - v_front)) / (2 * math.sqrt(a_max * b_comf)))
            
            accel = a_max * (1.0 - alpha - (s_star / s_front)**2)
            return accel

        # helper: for each (road,lane) find minimum s (closest to start)
        def lane_min_s(road_id: int, lane: int) -> float | None:
            vehs = by_road_lane.get((road_id, lane), [])
            if not vehs:
                return None
            return min(v.s for v in vehs)

        to_delete = []

        # 5. Physics Update (IDM)
        for (road_id, lane), vehs in list(by_road_lane.items()):
            road = self.net.roads.get(road_id)
            if road is None: continue

            L = road.length(self.net)
            vehs.sort(key=lambda v: v.s, reverse=True)

            for i, veh in enumerate(vehs):
                # Target speed is speed limit
                v_target = road.speed_limit
                
                # Default: no vehicle in front (very large distance)
                s_front = 1000.0
                v_front = veh.v

                if i > 0:
                    # Follower
                    leader = vehs[i-1]
                    s_front = leader.s - veh.s - 5.0 # 5m vehicle length
                else:
                    # Head vehicle - check traffic light or intersection
                    tl = self.net.traffic_lights.get(road.b)
                    is_red = False
                    if road.priority < 2 and tl is not None:
                        # Red OR Yellow triggers braking
                        is_red = not tl.is_green(road_id)
                    
                    if is_red:
                        s_front = L - veh.s
                        v_front = 0.0
                    else:
                        # Check intersection priority / yield
                        # If not safe, we simulate a virtual obstacle at the end
                        from .models import DirectedRoad
                        node_id = road.b
                        incomings = self.net.incoming_roads(node_id)
                        
                        # Simplified yield: if we are near end and it's not safe
                        if L - veh.s < 20.0:
                            # Use a simplified check: is there anyone closer than us on priority roads?
                            safe = True
                            for other_rid in incomings:
                                if other_rid == road_id: continue
                                other_road = self.net.roads[other_rid]
                                
                                # Priority check
                                has_prio = False
                                if other_road.priority > road.priority: has_prio = True
                                elif other_road.priority == road.priority:
                                    # Priority to the right
                                    diff = (other_road.angle_rad(self.net) - road.angle_rad(self.net) + math.pi) % (2 * math.pi) - math.pi
                                    if 0 < diff < math.pi * 0.9: has_prio = True
                                
                                if has_prio:
                                    # Anyone close?
                                    others = [v for v in self.vehicles.values() if v.road_id == other_rid]
                                    if others:
                                        dist = other_road.length(self.net) - max(v.s for v in others)
                                        if dist < 30.0:
                                            safe = False
                                            break
                            if not safe:
                                s_front = L - veh.s
                                v_front = 0.0

                # Calculate acceleration
                s_front = max(0.1, s_front)
                accel = get_idm_accel(veh.v, v_target, s_front, v_front)
                
                # Update velocity and position
                veh.v = max(0.0, veh.v + accel * dt)
                veh.s += veh.v * dt

                # Handle transition
                if veh.s >= L:
                    node_b = road.b
                    outs = self.net.outgoing_roads(node_b)
                    if not outs:
                        to_delete.append(veh.id)
                        continue

                    # Choose road
                    next_road_id = self.rng.choice(outs)
                    next_road = self.net.roads[next_road_id]
                    
                    # Choose lane
                    candidate_lanes = list(range(max(1, next_road.lanes)))
                    self.rng.shuffle(candidate_lanes)
                    chosen_lane = None
                    for ln in candidate_lanes:
                        min_s = lane_min_s(next_road_id, ln)
                        if min_s is None or min_s >= 10.0:
                            chosen_lane = ln
                            break
                    
                    if chosen_lane is not None:
                        veh.road_id = next_road_id
                        veh.lane = chosen_lane
                        veh.s = 0.0
                    else:
                        # Blocked: stay at end
                        veh.s = L - 0.1
                        veh.v = 0.0

        for vid in to_delete:
            veh = self.vehicles.pop(vid, None)
            if veh:
                self.total_finished += 1
                self.total_travel_time += (self.current_time - veh.spawn_time)
    def vehicle_world_pose(self, veh: Vehicle) -> Tuple[float, float, float]:
        """
        Returns (x, y, angle_degrees) in world coordinates for UI drawing.
        """
        from .models import LANE_WIDTH
        road = self.net.roads[veh.road_id]
        na = self.net.nodes[road.a]
        nb = self.net.nodes[road.b]
        L = road.length(self.net)
        t = 0.0 if L <= 1e-9 else max(0.0, min(1.0, veh.s / L))

        x = na.x + (nb.x - na.x) * t
        y = na.y + (nb.y - na.y) * t

        # Qt rotation is degrees, clockwise is positive visually depending on transform,
        # we keep a simple convention: angle from +x axis.
        dx = nb.x - na.x
        dy = nb.y - na.y
        L = math.hypot(dx, dy) or 1.0

        # Normale droite (conduite à droite)
        nx = dy / L
        ny = -dx / L

        # lane 0 = voie de droite
        offset = (veh.lane + 0.5) * LANE_WIDTH

        x += nx * offset
        y += ny * offset

        ang = math.degrees(road.angle_rad(self.net))
        return x, y, ang