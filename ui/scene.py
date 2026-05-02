from __future__ import annotations
from enum import Enum, auto
from typing import Dict, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QGraphicsScene

from core.network import RoadNetwork
from ui.graphics_items import NodeItem, RoadItem, VehicleItem, TrafficLightItem


class EditMode(Enum):
    SELECT = auto()
    ADD_NODE = auto()
    ADD_ROAD = auto()
    ADD_ROUNDABOUT = auto()


class MapScene(QGraphicsScene):
    def __init__(self, net: RoadNetwork):
        super().__init__()
        self.net = net

        # Optional: if set from MainWindow, we can clean vehicles on deleted roads.
        self.engine = None

        self.mode: EditMode = EditMode.SELECT
        self._pending_road_from: Optional[int] = None

        self.node_items: Dict[int, NodeItem] = {}
        self.road_items: Dict[int, RoadItem] = {}
        self.vehicle_items: Dict[int, VehicleItem] = {}
        self.traffic_light_items: Dict[int, TrafficLightItem] = {}

        self.setSceneRect(-2000, -2000, 4000, 4000)

    def set_mode(self, mode: EditMode) -> None:
        self.mode = mode
        self._pending_road_from = None

    def rebuild_from_network(self) -> None:
        self.clear()
        self.node_items.clear()
        self.road_items.clear()
        self.vehicle_items.clear()
        self.traffic_light_items.clear()

        for nid, n in self.net.nodes.items():
            self._add_node_item(nid, n.x, n.y)

        for rid in sorted(self.net.roads.keys()):
            self._add_road_item(rid)

    def _add_node_item(self, node_id: int, x: float, y: float) -> None:
        item = NodeItem(node_id, x, y)
        self.addItem(item)
        self.node_items[node_id] = item
        tl = TrafficLightItem(node_id)
        tl.setPos(QPointF(x + 10, y - 10))  # petit décalage visuel
        self.addItem(tl)
        self.traffic_light_items[node_id] = tl
        

    def _add_road_item(self, road_id: int) -> None:
        item = RoadItem(road_id)
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)  # important for Delete
        item.refresh_from_network(self.net)
        self.addItem(item)
        self.road_items[road_id] = item

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pos = event.scenePos()

        if self.mode == EditMode.ADD_NODE:
            nid = self.net.add_node(pos.x(), pos.y())
            self._add_node_item(nid, pos.x(), pos.y())
            return

        if self.mode == EditMode.ADD_ROAD:
            clicked = self.itemAt(pos, self.views()[0].transform()) if self.views() else None
            if isinstance(clicked, NodeItem):
                if self._pending_road_from is None:
                    self._pending_road_from = clicked.node_id
                else:
                    a = self._pending_road_from
                    b = clicked.node_id
                    if a != b:
                        rid_ab, rid_ba = self.net.add_bidirectional_road(a, b)
                        self._add_road_item(rid_ab)
                        self._add_road_item(rid_ba)
                    self._pending_road_from = None
                return

        if self.mode == EditMode.ADD_ROUNDABOUT:
            self.net.create_roundabout(pos.x(), pos.y())
            self.rebuild_from_network()
            return

        return super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            selected = self.selectedItems()
            if not selected:
                event.accept()
                return

            road_ids_to_remove = []
            node_ids_to_remove = []

            for it in selected:
                if isinstance(it, RoadItem):
                    road_ids_to_remove.append(it.road_id)
                elif isinstance(it, NodeItem):
                    node_ids_to_remove.append(it.node_id)

            # If nodes are deleted, remove all connected roads too.
            for nid in node_ids_to_remove:
                road_ids_to_remove.extend(self.net.connected_roads(nid))

            road_ids_to_remove = sorted(set(road_ids_to_remove))
            node_ids_to_remove = sorted(set(node_ids_to_remove))

            # Remove roads from core + UI
            for rid in road_ids_to_remove:
                self.net.roads.pop(rid, None)
                item = self.road_items.pop(rid, None)
                if item:
                    self.removeItem(item)

            # Remove nodes from core + UI
                        # Remove nodes from core + UI
            for nid in node_ids_to_remove:
                # core
                self.net.traffic_lights.pop(nid, None)
                self.net.nodes.pop(nid, None)

                # UI node
                item = self.node_items.pop(nid, None)
                if item:
                    self.removeItem(item)

                # UI traffic light
                tl_item = self.traffic_light_items.pop(nid, None)
                if tl_item:
                    self.removeItem(tl_item)

            # Optional: remove vehicles that are on deleted roads
            if self.engine is not None:
                removed = set(road_ids_to_remove)
                for vid in list(self.engine.vehicles.keys()):
                    if self.engine.vehicles[vid].road_id in removed:
                        self.engine.vehicles.pop(vid, None)

            event.accept()
            return

        super().keyPressEvent(event)

    def on_node_item_moved(self, node_id: int, new_pos: QPointF) -> None:
        # update core
        if node_id not in self.net.nodes:
            return

        self.net.move_node(node_id, new_pos.x(), new_pos.y())
        tl_item = self.traffic_light_items.get(node_id)
        if tl_item:
            tl_item.setPos(QPointF(new_pos.x() + 10, new_pos.y() - 10))

        # refresh connected roads
        for rid in self.net.connected_roads(node_id):
            item = self.road_items.get(rid)
            if item:
                item.refresh_from_network(self.net)

    def sync_vehicles(self, vehicle_poses: Dict[int, tuple[float, float, float]]):
        # create missing items
        for vid in vehicle_poses.keys():
            if vid not in self.vehicle_items:
                item = VehicleItem(vid)
                self.addItem(item)
                self.vehicle_items[vid] = item

        # remove deleted
        for vid in list(self.vehicle_items.keys()):
            if vid not in vehicle_poses:
                self.removeItem(self.vehicle_items[vid])
                del self.vehicle_items[vid]

        # update pose
        for vid, (x, y, ang) in vehicle_poses.items():
            self.vehicle_items[vid].set_pose(x, y, ang)
            
    def sync_traffic_lights(self):
        for nid, tl in self.net.traffic_lights.items():
            item = self.traffic_light_items.get(nid)
            if item:
                # Si au moins une route est verte, on affiche vert
                # Sinon si au moins une est orange, orange
                incomings = self.net.incoming_roads(nid)
                any_green = any(tl.is_green(rid) for rid in incomings)
                any_yellow = any(tl.is_yellow(rid) for rid in incomings)
                item.set_state(any_green, any_yellow)

