from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPolygonItem

from core.network import RoadNetwork


NODE_R = 8.0


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node_id: int, x: float, y: float):
        super().__init__(-NODE_R, -NODE_R, 2 * NODE_R, 2 * NODE_R)
        self.node_id = node_id
        self.setPos(QPointF(x, y))

        self.setBrush(QBrush(Qt.GlobalColor.white))
        self.setPen(QPen(Qt.GlobalColor.black, 2))

        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged:
            scene = self.scene()
            if scene is not None and hasattr(scene, "on_node_item_moved"):
                scene.on_node_item_moved(self.node_id, self.pos())
        return super().itemChange(change, value)


class RoadItem(QGraphicsPathItem):
    def __init__(self, road_id: int):
        super().__init__()
        self.road_id = road_id
        self.setZValue(-10)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)

    def refresh_from_network(self, net: RoadNetwork):
        from PySide6.QtGui import QPainterPath
        import math

        r = net.roads[self.road_id]
        a = net.nodes[r.a]
        b = net.nodes[r.b]

        ax, ay = a.x, a.y
        bx, by = b.x, b.y

        # Segment physique (u,v)
        u, v = (r.a, r.b) if r.a < r.b else (r.b, r.a)
        key = (u, v)
        rid_uv, rid_vu = net.paired_roads.get(key, (None, None))

        # Si c'est la voie "avant" (u->v) => gauche ; sinon => droite
        is_forward = (self.road_id == rid_uv)

        # Direction canonique u -> v (pour une normale stable)
        nu = net.nodes[u]
        nv = net.nodes[v]
        dx = nv.x - nu.x
        dy = nv.y - nu.y
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return

        # normale "gauche" de u->v
        nx = -dy / L
        ny = dx / L

        offset = 8.0
        sign = 1.0 if is_forward else -1.0

        ax2 = ax + nx * offset * sign
        ay2 = ay + ny * offset * sign
        bx2 = bx + nx * offset * sign
        by2 = by + ny * offset * sign

        path = QPainterPath(QPointF(ax2, ay2))
        path.lineTo(QPointF(bx2, by2))
        self.setPath(path)

        # une voie = trait fin ; tu peux épaissir si tu veux
        self.setPen(QPen(Qt.GlobalColor.darkGray, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        
class VehicleItem(QGraphicsPolygonItem):
    def __init__(self, vehicle_id: int):
        super().__init__()
        self.vehicle_id = vehicle_id

        # A small arrow/triangle pointing to +X in local coordinates.
        poly = QPolygonF([QPointF(0, 0), QPointF(-10, -5), QPointF(-10, 5)])
        self.setPolygon(poly)

        self.setBrush(QBrush(Qt.GlobalColor.blue))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setZValue(10)

        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)

    def set_pose(self, x: float, y: float, angle_deg: float):
        self.setPos(QPointF(x, y))
        self.setRotation(angle_deg)

class TrafficLightItem(QGraphicsEllipseItem):
    def __init__(self, node_id: int):
        r = 4.0
        super().__init__(-r, -r, 2*r, 2*r)
        self.node_id = node_id
        self.setZValue(20)
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setBrush(QBrush(Qt.GlobalColor.red))

    def set_state(self, green: bool):
        self.setBrush(QBrush(Qt.GlobalColor.green if green else Qt.GlobalColor.red))