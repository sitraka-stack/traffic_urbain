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
        from core.models import LANE_WIDTH
        import math

        r = net.roads[self.road_id]
        a = net.nodes[r.a]
        b = net.nodes[r.b]

        ax, ay = a.x, a.y
        bx, by = b.x, b.y

        dx = bx - ax
        dy = by - ay
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return

        # Normale droite (conduite à droite)
        nx = dy / L
        ny = -dx / L

        # On décale le milieu du tracé de la moitié de sa largeur vers la droite
        offset = (r.lanes * LANE_WIDTH) / 2.0

        ax2 = ax + nx * offset
        ay2 = ay + ny * offset
        bx2 = bx + nx * offset
        by2 = by + ny * offset

        path = QPainterPath(QPointF(ax2, ay2))
        path.lineTo(QPointF(bx2, by2))
        self.setPath(path)

        self.setPen(QPen(Qt.GlobalColor.darkGray, r.lanes * LANE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        
        
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

    def set_state(self, green: bool, yellow: bool = False):
        if green:
            self.setBrush(QBrush(Qt.GlobalColor.green))
        elif yellow:
            self.setBrush(QBrush(Qt.GlobalColor.yellow))
        else:
            self.setBrush(QBrush(Qt.GlobalColor.red))