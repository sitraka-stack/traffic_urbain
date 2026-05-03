from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QRectF
from PySide6.QtGui import QBrush, QPen, QPolygonF, QColor, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPolygonItem, 
    QGraphicsTextItem, QGraphicsRectItem, QGraphicsItemGroup
)

from core.network import RoadNetwork


NODE_R = 6.0


class NodeItem(QGraphicsEllipseItem):
    def __init__(self, node_id: int, x: float, y: float):
        super().__init__(-NODE_R, -NODE_R, 2 * NODE_R, 2 * NODE_R)
        self.node_id = node_id
        self.setPos(QPointF(x, y))

        self.setBrush(QBrush(QColor(255, 255, 255, 150)))
        self.setPen(QPen(QColor(0, 0, 0, 100), 1))

        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(5)

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
        
        self.label = QGraphicsTextItem(self)
        self.label.setDefaultTextColor(QColor("white"))
        font = self.label.font()
        font.setPointSize(7)
        font.setBold(True)
        self.label.setFont(font)
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label.setZValue(1)

        # For dashed lines
        self.lane_markings = QGraphicsPathItem(self)
        self.lane_markings.setZValue(0.1)

    def refresh_from_network(self, net: RoadNetwork):
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

        nx = dy / L
        ny = -dx / L

        offset = (r.lanes * LANE_WIDTH) / 2.0
        ax2 = ax + nx * offset
        ay2 = ay + ny * offset
        bx2 = bx + nx * offset
        by2 = by + ny * offset

        path = QPainterPath(QPointF(ax2, ay2))
        path.lineTo(QPointF(bx2, by2))
        self.setPath(path)

        # Asphalt color
        asphalt = QColor("#2c3e50")
        self.setPen(QPen(asphalt, r.lanes * LANE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        
        # Lane markings (dashed white lines between lanes)
        if r.lanes > 1:
            marking_path = QPainterPath()
            for i in range(1, r.lanes):
                l_offset = i * LANE_WIDTH
                # adjust offset because road center is shifted
                total_offset = l_offset - (r.lanes * LANE_WIDTH) / 2.0
                
                lax = ax2 - nx * l_offset
                lay = ay2 - ny * l_offset
                lbx = bx2 - nx * l_offset
                lby = by2 - ny * l_offset
                
                marking_path.moveTo(lax, lay)
                marking_path.lineTo(lbx, lby)
            
            self.lane_markings.setPath(marking_path)
            pen = QPen(QColor(255, 255, 255, 100), 1, Qt.PenStyle.DashLine)
            self.lane_markings.setPen(pen)
        else:
            self.lane_markings.setPath(QPainterPath())

        # Label update
        self.label.setPlainText(r.name)
        cx = (ax2 + bx2) / 2.0
        cy = (ay2 + by2) / 2.0
        
        angle = math.degrees(math.atan2(dy, dx))
        if 90 < angle <= 270 or -270 < angle <= -90:
            angle += 180
            
        self.label.setRotation(0)
        rect = self.label.boundingRect()
        self.label.setTransformOriginPoint(rect.width() / 2, rect.height() / 2)
        self.label.setPos(cx - rect.width() / 2, cy - rect.height() / 2)
        self.label.setRotation(angle)
        self.label.setVisible(L > rect.width() * 1.5)
        
        
class VehicleItem(QGraphicsItemGroup):
    def __init__(self, vehicle_id: int, color: str = "blue", length: float = 16.0):
        super().__init__()
        self.vehicle_id = vehicle_id
        
        # Scaling length from meters to pixels (roughly 1m = 3.2px if 5m = 16px)
        # Actually our current fixed car was 16px for 5m. So 1m = 3.2px.
        px_length = length * 3.2
        width = 8.0 # fixed for now
        
        # Car body
        self.body = QGraphicsRectItem(-px_length/2, -width/2, px_length, width)
        self.body.setBrush(QBrush(QColor(color)))
        self.body.setPen(QPen(Qt.GlobalColor.black, 1))
        self.addToGroup(self.body)

        # Windshield (scaled)
        ws_w = px_length * 0.2
        ws_h = width * 0.75
        self.windshield = QGraphicsRectItem(px_length * 0.1, -ws_h/2, ws_w, ws_h)
        self.windshield.setBrush(QBrush(QColor(200, 230, 255, 200)))
        self.windshield.setPen(Qt.PenStyle.NoPen)
        self.addToGroup(self.windshield)

        # Lights
        l_r = 2.0
        self.left_light = QGraphicsEllipseItem(px_length/2 - l_r, -width/2 + 1, l_r, l_r)
        self.left_light.setBrush(QBrush(Qt.GlobalColor.yellow))
        self.left_light.setPen(Qt.PenStyle.NoPen)
        self.addToGroup(self.left_light)

        self.right_light = QGraphicsEllipseItem(px_length/2 - l_r, width/2 - 3, l_r, l_r)
        self.right_light.setBrush(QBrush(Qt.GlobalColor.yellow))
        self.right_light.setPen(Qt.PenStyle.NoPen)
        self.addToGroup(self.right_light)

        self.setZValue(10)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)

    def set_pose(self, x: float, y: float, angle_deg: float):
        self.setPos(QPointF(x, y))
        self.setRotation(angle_deg)


class TrafficLightItem(QGraphicsRectItem):
    def __init__(self, node_id: int):
        # A small vertical box
        super().__init__(-3, -9, 6, 18)
        self.node_id = node_id
        self.setZValue(20)
        self.setBrush(QBrush(QColor("#2c3e50")))
        self.setPen(QPen(Qt.GlobalColor.black, 1))

        # Three lights
        self.red_light = QGraphicsEllipseItem(-2, -7, 4, 4, self)
        self.yellow_light = QGraphicsEllipseItem(-2, -2, 4, 4, self)
        self.green_light = QGraphicsEllipseItem(-2, 3, 4, 4, self)
        
        for l in [self.red_light, self.yellow_light, self.green_light]:
            l.setPen(Qt.PenStyle.NoPen)
            l.setBrush(QBrush(QColor(50, 50, 50))) # off

    def set_state(self, green: bool, yellow: bool = False):
        # Reset
        self.red_light.setBrush(QBrush(QColor(50, 50, 50)))
        self.yellow_light.setBrush(QBrush(QColor(50, 50, 50)))
        self.green_light.setBrush(QBrush(QColor(50, 50, 50)))

        if green:
            self.green_light.setBrush(QBrush(Qt.GlobalColor.green))
        elif yellow:
            self.yellow_light.setBrush(QBrush(Qt.GlobalColor.yellow))
        else:
            self.red_light.setBrush(QBrush(Qt.GlobalColor.red))
