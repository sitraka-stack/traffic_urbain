from __future__ import annotations
import json
from pathlib import Path

from .network import RoadNetwork


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
        net.nodes[nid] = net.nodes.get(nid) or __import__("core.models", fromlist=["Node"]).Node(id=nid, x=float(n["x"]), y=float(n["y"]))
        max_nid = max(max_nid, nid)

    # recreate roads with same IDs
    max_rid = 0
    for r in data.get("roads", []):
        rid = int(r["id"])
        net.roads[rid] = __import__("core.models", fromlist=["DirectedRoad"]).DirectedRoad(
            id=rid,
            a=int(r["a"]),
            b=int(r["b"]),
            speed_limit=float(r.get("speed_limit", 13.9)),
            lanes=int(r.get("lanes", 1)),
        )
        max_rid = max(max_rid, rid)

    net._next_node_id = max_nid + 1
    net._next_road_id = max_rid + 1
    return net