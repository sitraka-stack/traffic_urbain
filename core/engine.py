from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from collections import defaultdict

from .models import Vehicle, VehicleType, RoadState, DirectedRoad
from .network import RoadNetwork


@dataclass
class SimulationEngine:
    net: RoadNetwork
    vehicles: Dict[int, Vehicle] = field(default_factory=dict)

    _next_vehicle_id: int = 1
    spawn_rate: float = 0.4  # vehicles per second
    rng: random.Random = field(default_factory=random.Random)
    
    current_time: float = 0.0
    total_finished: int = 0
    total_travel_time: float = 0.0
    
    # Metrics tracking for Markov
    _last_markov_update: float = 0.0
    MARKOV_INTERVAL: float = 2.0 # Update states every 2 seconds

    # IDM Default Parameters
    T = 1.5      
    delta = 4    
    s0 = 4.0     

    def reset(self) -> None:
        self.vehicles.clear()
        self._next_vehicle_id = 1
        self.current_time = 0.0
        self.total_finished = 0
        self.total_travel_time = 0.0
        for road in self.net.roads.values():
            road.current_state = RoadState.FLUID
            road.state_history.clear()
            road.transition_counts.clear()
            road.total_wait_time = 0.0
            road.queue_length = 0

    def _pick_entry_road(self) -> Optional[int]:
        if not self.net.roads: return None
        entry_roads = []
        for rid, r in self.net.roads.items():
            if r.priority >= 2: continue
            incomings_to_a = self.net.incoming_roads(r.a)
            if not incomings_to_a: entry_roads.append(rid)
        if not entry_roads:
            entry_roads = [rid for rid, r in self.net.roads.items() if r.priority < 2]
        return self.rng.choice(entry_roads) if entry_roads else None

    def _pick_exit_node(self, start_node: int) -> Optional[int]:
        nodes = list(self.net.nodes.keys())
        if len(nodes) < 2: return None
        exits = [nid for nid in nodes if not self.net.outgoing_roads(nid) and nid != start_node]
        if exits: return self.rng.choice(exits)
        others = [nid for nid in nodes if nid != start_node]
        return self.rng.choice(others) if others else None

    def get_advanced_metrics(self) -> Dict:
        if not self.vehicles:
            return {
                "count": 0, "avg_speed": 0.0, "waiting_count": 0,
                "congestion_level": "Fluide", "total_finished": self.total_finished,
                "avg_travel_time": self.total_travel_time / self.total_finished if self.total_finished > 0 else 0.0,
                "busiest_road": "Aucune"
            }
        
        speeds = [v.v for v in self.vehicles.values()]
        avg_v = sum(speeds) / len(speeds)
        waiting_count = len([v for v in self.vehicles.values() if v.v < 0.5])
        
        ratio = waiting_count / len(self.vehicles)
        if ratio < 0.1: congestion = "Fluide"
        elif ratio < 0.3: congestion = "Modéré"
        elif ratio < 0.6: congestion = "Dense"
        else: congestion = "Bouchon"
        
        counts = defaultdict(int)
        for v in self.vehicles.values(): counts[v.road_id] += 1
        busiest_id = max(counts, key=counts.get) if counts else "Aucune"

        return {
            "count": len(self.vehicles), "avg_speed": avg_v, "waiting_count": waiting_count,
            "congestion_level": congestion, "total_finished": self.total_finished,
            "avg_travel_time": self.total_travel_time / self.total_finished if self.total_finished > 0 else 0.0,
            "busiest_road": f"ID {busiest_id}" if busiest_id != "Aucune" else "Aucune"
        }

    def _spawn_vehicle(self) -> None:
        road_id = self._pick_entry_road()
        if road_id is None: return
        road = self.net.roads[road_id]
        lanes = max(1, road.lanes)
        lane = self.rng.randrange(lanes)
        SAFE_SPAWN_DIST = 10.0
        for veh in self.vehicles.values():
            if veh.road_id == road_id and veh.lane == lane and veh.s < SAFE_SPAWN_DIST: return
        vid = self._next_vehicle_id
        self._next_vehicle_id += 1
        v_types = [VehicleType.CAR, VehicleType.TRUCK, VehicleType.BUS, VehicleType.MOTORCYCLE]
        weights = [70, 15, 5, 10]
        v_type = self.rng.choices(v_types, weights=weights, k=1)[0]
        exit_node = self._pick_exit_node(road.a)
        path = self.net.shortest_path(road.b, exit_node) if exit_node else []
        colors = ["#3498db", "#e74c3c", "#f1c40f", "#2ecc71", "#9b59b6", "#e67e22", "#1abc9c"]
        color = self.rng.choice(colors)
        v = max(2.0, min(road.speed_limit, self.rng.uniform(8.0, road.speed_limit)))
        veh = Vehicle(id=vid, road_id=road_id, type=v_type, s=0.0, v=v, lane=lane, 
                      spawn_time=self.current_time, color=color, path=path, target_node=exit_node)
        veh.v_target = road.speed_limit * self.rng.uniform(0.9, 1.1)
        self.vehicles[vid] = veh

    def spawn_multiple(self, count: int) -> None:
        for _ in range(count): self._spawn_vehicle()

    def get_idm_accel(self, veh: Vehicle, s_front: float, v_front: float) -> float:
        v = veh.v
        v_target = veh.v_target
        a_max = veh.max_accel
        b_comf = veh.max_decel
        alpha = (v / v_target)**self.delta if v_target > 0 else 1.0
        s_star = self.s0 + max(0.0, v * self.T + (v * (v - v_front)) / (2 * math.sqrt(a_max * b_comf)))
        accel = a_max * (1.0 - alpha - (s_star / s_front)**2)
        return accel

    def step(self, dt: float) -> None:
        if dt <= 0: return
        self.current_time += dt
        road_counts = defaultdict(int)
        for v in self.vehicles.values(): road_counts[v.road_id] += 1
        for tl in self.net.traffic_lights.values(): tl.step(dt, road_counts)
        if self.net.roads and self.rng.random() < self.spawn_rate * dt:
            self._spawn_vehicle()
        by_road_lane = defaultdict(list)
        for veh in self.vehicles.values():
            by_road_lane[(veh.road_id, veh.lane)].append(veh)
        for key in by_road_lane:
            by_road_lane[key].sort(key=lambda v: v.s, reverse=True)

        to_delete = []
        updates = {}
        for veh in list(self.vehicles.values()):
            road = self.net.roads.get(veh.road_id)
            if not road: continue
            L = road.length(self.net)
            vehs_in_lane = by_road_lane[(veh.road_id, veh.lane)]
            idx = vehs_in_lane.index(veh)
            s_front, v_front = 1000.0, veh.v
            is_at_intersection = False
            if idx > 0:
                leader = vehs_in_lane[idx-1]
                s_front = leader.s - veh.s - leader.length
            else:
                tl = self.net.traffic_lights.get(road.b)
                stop_for_tl = road.priority < 2 and tl and not tl.is_green(veh.road_id)
                if stop_for_tl:
                    s_front, v_front = L - veh.s, 0.0
                    is_at_intersection = True
                elif L - veh.s < 25.0 and not self._is_intersection_safe(veh, road):
                    s_front, v_front = L - veh.s, 0.0
                    is_at_intersection = True
            accel = self.get_idm_accel(veh, max(0.1, s_front), v_front)
            v_new = max(0.0, veh.v + accel * dt)
            s_new = veh.s + v_new * dt
            if v_new < 0.5 and is_at_intersection:
                road.total_wait_time += dt
            lane_new = veh.lane
            if road.lanes > 1 and self.rng.random() < 0.1:
                for target_lane in [veh.lane - 1, veh.lane + 1]:
                    if 0 <= target_lane < road.lanes:
                        if self._should_change_lane(veh, road, vehs_in_lane, by_road_lane[(road.id, target_lane)]):
                            lane_new = target_lane
                            break
            road_new = veh.road_id
            if s_new >= L:
                next_road_id = self._get_next_road(veh, road)
                if next_road_id:
                    road_new, s_new = next_road_id, s_new - L
                    next_road = self.net.roads[road_new]
                    if lane_new >= next_road.lanes: lane_new = next_road.lanes - 1
                else:
                    to_delete.append(veh.id)
                    continue
            updates[veh.id] = (v_new, s_new, road_new, lane_new)

        for vid, (vn, sn, rn, ln) in updates.items():
            v = self.vehicles[vid]
            v.v, v.s, v.road_id, v.lane = vn, sn, rn, ln
        for vid in to_delete:
            v = self.vehicles.pop(vid, None)
            if v:
                self.total_finished += 1
                self.total_travel_time += (self.current_time - v.spawn_time)
        
        # 6. Advanced Modeling Updates
        self._update_markov_and_queues(dt, road_counts)

    def _update_markov_and_queues(self, dt: float, road_counts: Dict[int, int]):
        # Update Queues every step
        for rid, road in self.net.roads.items():
            # Queue = vehicles at speed < 2m/s near the end of road
            queue = [v for v in self.vehicles.values() if v.road_id == rid and v.v < 2.0 and road.length(self.net) - v.s < 30.0]
            road.queue_length = len(queue)
            # Saturation = current count / theoretical capacity (simplified)
            capacity = (road.length(self.net) / 7.0) * road.lanes
            road.saturation_rate = road_counts.get(rid, 0) / max(1.0, capacity)

        # Update Markov every interval
        if self.current_time - self._last_markov_update >= self.MARKOV_INTERVAL:
            for rid, road in self.net.roads.items():
                avg_speed = 0.0
                vehs = [v for v in self.vehicles.values() if v.road_id == rid]
                if vehs:
                    avg_speed = sum(v.v for v in vehs) / len(vehs)
                
                # Determine new state
                new_state = RoadState.FLUID
                if avg_speed < road.speed_limit * 0.3: new_state = RoadState.JAM
                elif avg_speed < road.speed_limit * 0.7: new_state = RoadState.SLOW
                
                # Record transition
                old_state = road.current_state
                road.transition_counts[(old_state, new_state)] += 1
                road.current_state = new_state
                road.state_history.append(new_state)
                if len(road.state_history) > 100: road.state_history.pop(0)
            
            self._last_markov_update = self.current_time

    def get_markov_matrix(self, road_id: int) -> Dict[Tuple[RoadState, RoadState], float]:
        road = self.net.roads.get(road_id)
        if not road: return {}
        matrix = {}
        for s1 in RoadState:
            total = sum(road.transition_counts[(s1, s2)] for s2 in RoadState)
            for s2 in RoadState:
                count = road.transition_counts[(s1, s2)]
                matrix[(s1, s2)] = count / total if total > 0 else (1.0 if s1 == s2 else 0.0)
        return matrix

    def run_monte_carlo(self, num_iterations: int = 10, duration: float = 60.0) -> Dict:
        """
        Runs multiple simulation scenarios and returns aggregated statistics.
        """
        import copy
        results = []
        for i in range(num_iterations):
            # Deep copy to ensure no side effects on the main simulation
            net_copy = copy.deepcopy(self.net)
            engine = SimulationEngine(net_copy)
            engine.rng = random.Random(i + int(self.current_time))
            engine.spawn_rate = self.spawn_rate
            
            t = 0.0
            dt = 0.2 # Faster step for MC
            while t < duration:
                engine.step(dt)
                t += dt
            
            results.append(engine.get_advanced_metrics())
        
        # Aggregate
        avg_res = {
            "avg_count": sum(r["count"] for r in results) / num_iterations,
            "avg_speed": sum(r["avg_speed"] for r in results) / num_iterations,
            "avg_travel_time": sum(r["avg_travel_time"] for r in results) / num_iterations,
            "avg_finished": (sum(r["total_finished"] for r in results) / num_iterations) / (duration / 60.0),
        }
        return avg_res

    def _is_intersection_safe(self, veh: Vehicle, road: DirectedRoad) -> bool:
        node_id = road.b
        incomings = self.net.incoming_roads(node_id)
        for other_rid in incomings:
            if other_rid == road.id: continue
            other_road = self.net.roads[other_rid]
            has_prio = other_road.priority > road.priority
            if not has_prio and other_road.priority == road.priority:
                diff = (other_road.angle_rad(self.net) - road.angle_rad(self.net) + math.pi) % (2 * math.pi) - math.pi
                if 0 < diff < math.pi * 0.7: has_prio = True
            if has_prio:
                others = [v for v in self.vehicles.values() if v.road_id == other_rid]
                if others:
                    dist = other_road.length(self.net) - max(o.s for o in others)
                    if dist < 40.0: return False
        return True

    def _should_change_lane(self, veh: Vehicle, road: DirectedRoad, current_vehs: List[Vehicle], target_vehs: List[Vehicle]) -> bool:
        leader, follower = None, None
        for v in target_vehs:
            if v.s > veh.s: 
                if leader is None or v.s < leader.s: leader = v
            else:
                if follower is None or v.s > follower.s: follower = v
        if leader and leader.s - veh.s < veh.length + 2: return False
        if follower and veh.s - follower.s < follower.length + 2: return False
        leader_curr = next((v for v in current_vehs if v.s > veh.s), None)
        if not leader_curr: return False
        dist_curr = leader_curr.s - veh.s
        if dist_curr > 40.0: return False
        dist_target = (leader.s - veh.s) if leader else 1000.0
        return dist_target > dist_curr + 10.0

    def _get_next_road(self, veh: Vehicle, current_road: DirectedRoad) -> Optional[int]:
        if veh.path:
            next_rid = veh.path.pop(0)
            if next_rid in self.net.roads: return next_rid
        node_b = current_road.b
        outs = self.net.outgoing_roads(node_b)
        if not outs: return None
        filtered = [rid for rid in outs if self.net.roads[rid].b != current_road.a]
        return self.rng.choice(filtered if filtered else outs)

    def vehicle_world_pose(self, veh: Vehicle) -> Tuple[float, float, float]:
        from .models import LANE_WIDTH
        road = self.net.roads[veh.road_id]
        na, nb = self.net.nodes[road.a], self.net.nodes[road.b]
        L = road.length(self.net)
        t = max(0.0, min(1.0, veh.s / L)) if L > 1e-6 else 0.0
        x, y = na.x + (nb.x - na.x) * t, na.y + (nb.y - na.y) * t
        dx, dy = nb.x - na.x, nb.y - na.y
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = dy / dist, -dx / dist
        offset = (veh.lane + 0.5) * LANE_WIDTH
        x, y = x + nx * offset, y + ny * offset
        ang = math.degrees(road.angle_rad(self.net))
        return x, y, ang
