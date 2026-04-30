from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

from .models import Node, DirectedRoad
from .network import RoadNetwork
from .traffic_lights import TrafficLight


def save_network(net: RoadNetwork, path: str) -> None:
    p = Path(path)
    data = {
        "nodes": [{"id": n.id, "x": n.x, "y": n.y} for n in net.nodes.values()],
        "roads": [{"id": r.id, "a": r.a, "b": r.b, "speed_limit": r.speed_limit, "lanes": r.lanes} for r in net.roads.values()],
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_network(path: str) -> RoadNetwork:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    net = RoadNetwork()

    # recreate nodes with same IDs
    max_nid = 0
    for n in data.get("nodes", []):
        nid = int(n["id"])
        net.nodes[nid] = Node(id=nid, x=float(n["x"]), y=float(n["y"]))
        net.traffic_lights[nid] = TrafficLight(node_id=nid)
        max_nid = max(max_nid, nid)

    # recreate roads with same IDs
    max_rid = 0
    for r in data.get("roads", []):
        rid = int(r["id"])
        net.roads[rid] = DirectedRoad(
            id=rid,
            a=int(r["a"]),
            b=int(r["b"]),
            speed_limit=float(r.get("speed_limit", 13.9)),
            lanes=int(r.get("lanes", 1)),
        )
        max_rid = max(max_rid, rid)

    net._next_node_id = max_nid + 1
    net._next_road_id = max_rid + 1

    # reconstruct paired_roads: find bidirectional pairs (u->v and v->u)
    segment_roads: dict[tuple[int, int], list[int]] = defaultdict(list)
    for rid, r in net.roads.items():
        key = (min(r.a, r.b), max(r.a, r.b))
        segment_roads[key].append(rid)

    for key, rids in segment_roads.items():
        if len(rids) == 2:
            u, v = key
            rid_uv = next((rid for rid in rids if net.roads[rid].a == u), None)
            rid_vu = next((rid for rid in rids if net.roads[rid].a == v), None)
            if rid_uv is not None and rid_vu is not None:
                net.paired_roads[key] = (rid_uv, rid_vu)

    return net