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

    def reset(self) -> None:
        self.vehicles.clear()
        self._next_vehicle_id = 1

    def _pick_random_road(self) -> Optional[int]:
        if not self.net.roads:
            return None
        return self.rng.choice(list(self.net.roads.keys()))

    def _spawn_vehicle(self) -> None:
        road_id = self._pick_random_road()
        if road_id is None:
            return

        vid = self._next_vehicle_id
        self._next_vehicle_id += 1

        speed_limit = self.net.roads[road_id].speed_limit
        v = max(2.0, min(speed_limit, self.rng.uniform(6.0, speed_limit)))

        self.vehicles[vid] = Vehicle(id=vid, road_id=road_id, s=0.0, v=v, lane=0)
    
    def step(self, dt: float) -> None:
        # update traffic lights
        for tl in self.net.traffic_lights.values():
            tl.step(dt)

        # spawn: simple Bernoulli approximation of Poisson
        if dt > 0 and self.net.roads:
            p = min(1.0, self.spawn_rate * dt)
            if self.rng.random() < p:
                self._spawn_vehicle()

        # group vehicles by road then by lane
        from collections import defaultdict
        by_road_lane = defaultdict(list)
        for veh in self.vehicles.values():
            by_road_lane[(veh.road_id, veh.lane)].append(veh)

        gap = 14.0          # min spacing on same lane (m)
        stop_distance = 14.0  # distance to stop for red light (m)
        entry_gap = 14.0    # min spacing from road start when entering (m)

        # helper: for each (road,lane) find minimum s (closest to start)
        def lane_min_s(road_id: int, lane: int) -> float | None:
            vehs = by_road_lane.get((road_id, lane), [])
            if not vehs:
                return None
            return min(v.s for v in vehs)

        to_delete = []

        # process each (road,lane) independently for car-following
        for (road_id, lane), vehs in list(by_road_lane.items()):
            road = self.net.roads.get(road_id)
            if road is None:
                continue

            L = road.length(self.net)

            # front to back
            vehs.sort(key=lambda v: v.s, reverse=True)

            # compute target positions
            s_target = {}

            # head vehicle: obey red light
            head = vehs[0]
            dist_to_end = L - head.s
            tl = self.net.traffic_lights.get(road.b)

            if tl is not None and (not tl.is_green()) and dist_to_end <= stop_distance:
                s_target[head.id] = max(0.0, L - 0.5)
            else:
                s_target[head.id] = head.s + head.v * dt

            leader_s = min(s_target[head.id], L)

            # followers: obey spacing
            for follower in vehs[1:]:
                desired = follower.s + follower.v * dt
                max_allowed = leader_s - gap
                s_target[follower.id] = min(desired, max_allowed)
                leader_s = s_target[follower.id]

            # apply targets + handle intersection transitions safely
            for veh in vehs:
                veh.s = s_target[veh.id]

                if veh.s >= L:
                    # attempt to move to an outgoing road
                    node_b = road.b
                    outs = self.net.outgoing_roads(node_b)
                    if not outs:
                        to_delete.append(veh.id)
                        continue

                    next_road_id = self.rng.choice(outs)
                    next_road = self.net.roads[next_road_id]

                    # choose a lane that is free at entry
                    candidate_lanes = list(range(max(1, next_road.lanes)))
                    self.rng.shuffle(candidate_lanes)

                    chosen_lane = None
                    for ln in candidate_lanes:
                        min_s = lane_min_s(next_road_id, ln)
                        if min_s is None or min_s >= entry_gap:
                            chosen_lane = ln
                            break

                    if chosen_lane is None:
                        # cannot enter: stay at end of current road (creates spillback congestion)
                        veh.s = max(0.0, L - 0.5)
                    else:
                        # enter next road
                        # update grouping maps to keep lane_min_s approx valid
                        by_road_lane[(veh.road_id, veh.lane)].remove(veh)
                        veh.road_id = next_road_id
                        veh.lane = chosen_lane
                        veh.s = 0.0
                        by_road_lane[(veh.road_id, veh.lane)].append(veh)

        for vid in to_delete:
            self.vehicles.pop(vid, None)
    def vehicle_world_pose(self, veh: Vehicle) -> Tuple[float, float, float]:
        """
        Returns (x, y, angle_degrees) in world coordinates for UI drawing.
        Vehicles on the forward road (u->v) are offset left; reverse (v->u) offset right.
        """
        road = self.net.roads[veh.road_id]
        na = self.net.nodes[road.a]
        nb = self.net.nodes[road.b]
        L = road.length(self.net)
        t = 0.0 if L <= 1e-9 else max(0.0, min(1.0, veh.s / L))

        x = na.x + (nb.x - na.x) * t
        y = na.y + (nb.y - na.y) * t

        # Use paired_roads convention to offset vehicle onto the correct visual lane
        u, v = min(road.a, road.b), max(road.a, road.b)
        key = (u, v)
        rid_uv, rid_vu = self.net.paired_roads.get(key, (None, None))

        if rid_uv is not None:
            # canonical direction u->v: compute left-hand normal
            nu = self.net.nodes[u]
            nv = self.net.nodes[v]
            cdx = nv.x - nu.x
            cdy = nv.y - nu.y
            cL = math.hypot(cdx, cdy) or 1.0
            nx = -cdy / cL  # left normal of u->v
            ny = cdx / cL

            offset = 8.0
            # forward (u->v) => left (+offset); reverse (v->u) => right (-offset)
            sign = 1.0 if veh.road_id == rid_uv else -1.0
            x += nx * offset * sign
            y += ny * offset * sign

        ang = math.degrees(road.angle_rad(self.net))
        return x, y, ang