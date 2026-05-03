from __future__ import annotations
import json
from pathlib import Path

from .network import RoadNetwork


def save_network(net: RoadNetwork, path: str) -> None:
    p = Path(path)
    data = {
        "nodes": [{"id": n.id, "x": n.x, "y": n.y} for n in net.nodes.values()],
        "roads": [
            {
                "id": r.id, 
                "a": r.a, 
                "b": r.b, 
                "name": r.name,
                "speed_limit": r.speed_limit, 
                "lanes": r.lanes,
                "priority": r.priority
            } for r in net.roads.values()],
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_network(path: str) -> RoadNetwork:
    from .models import Node, DirectedRoad
    from .traffic_lights import TrafficLight
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
            name=r.get("name", ""),
            speed_limit=float(r.get("speed_limit", 13.9)),
            lanes=int(r.get("lanes", 1)),
            priority=int(r.get("priority", 0))
        )
        max_rid = max(max_rid, rid)

    # Recalculate phases for all nodes
    for nid in net.nodes:
        net.recalculate_traffic_light_phases(nid)

    net._next_node_id = max_nid + 1
    net._next_road_id = max_rid + 1
    return net