from __future__ import annotations
import time
from collections import defaultdict

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout

from core.engine import SimulationEngine
from core.metrics import vehicle_count, avg_speed
from core.network import RoadNetwork
from core.io import save_network, load_network

from ui.controls import Controls
from ui.scene import MapScene, EditMode
from ui.view import MapView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trafi_routier - Simulation de trafic (PySide6)")

        self.net = RoadNetwork()
        self.engine = SimulationEngine(self.net)

        self.scene = MapScene(self.net)
        self.view = MapView(self.scene)
        self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.view.setFocus()
        self.controls = Controls()
        self.scene.engine = self.engine

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.controls, 0)
        self.setCentralWidget(root)

        # wire controls
        self.controls.play_toggled.connect(self._on_play)
        self.controls.speed_changed.connect(self._on_speed)
        self.controls.mode_changed.connect(self._on_mode)
        self.controls.save_requested.connect(self._on_save)
        self.controls.load_requested.connect(self._on_load)

        self._playing = True
        self._speed_factor = 1.0
        self._last_time = time.perf_counter()

        self.timer = QTimer(self)
        self.timer.setInterval(16)  # ~60 FPS
        self.timer.timeout.connect(self._tick)
        self.timer.start()

        # nicer view default
        self.view.setMinimumSize(900, 600)
        
        self.statusBar().showMessage("Prêt")
        
        self.controls.traffic_green_changed.connect(self._set_all_green)
        self.controls.traffic_red_changed.connect(self._set_all_red)
        self.controls.spawn_rate_changed.connect(self._on_spawn_rate)
        self.controls.manual_spawn_requested.connect(self._on_manual_spawn)
        self.controls.monte_carlo_requested.connect(self._on_monte_carlo)
        self.controls.clear_requested.connect(self._on_clear)
        self._tl_green = 6.0
        self._tl_red = 6.0
        

    def _on_play(self, playing: bool):
        self._playing = playing
        self._last_time = time.perf_counter()

    def _on_speed(self, factor: float):
        self._speed_factor = factor

    def _on_spawn_rate(self, rate: float):
        self.engine.spawn_rate = rate

    def _on_manual_spawn(self, count: int):
        self.engine.spawn_multiple(count)

    def _on_monte_carlo(self):
        self.statusBar().showMessage("Calcul Monte Carlo en cours...")
        res = self.engine.run_monte_carlo(num_iterations=10, duration=60.0)
        self.controls.set_monte_carlo_results(res)
        self.statusBar().showMessage("Monte Carlo terminé", 5000)

    def _on_clear(self):
        from core.network import RoadNetwork
        from core.engine import SimulationEngine
        self.net = RoadNetwork()
        self.engine = SimulationEngine(self.net)
        self.scene.net = self.net
        self.scene.engine = self.engine
        self.scene.rebuild_from_network()
        self.scene.sync_vehicles({})

    def _on_mode(self, mode: EditMode):
        self.scene.set_mode(mode)

    def _on_save(self, path: str):
        save_network(self.net, path)

    def _on_load(self, path: str):
        self.net = load_network(path)
        self.engine = SimulationEngine(self.net)  # reset engine with new network

        self.scene.net = self.net
        self.scene.engine = self.engine  # <-- AJOUT IMPORTANT
        self.scene.rebuild_from_network()
        self.scene.sync_traffic_lights()
    def _tick(self):
        now = time.perf_counter()
        dt_real = now - self._last_time
        self._last_time = now

        if self._playing:
            dt = dt_real * self._speed_factor
            # avoid huge dt if window was paused
            dt = min(dt, 0.1)
            self.engine.step(dt)
            

        # sync vehicles
        poses = {vid: self.engine.vehicle_world_pose(v) for vid, v in self.engine.vehicles.items()}
        self.scene.sync_vehicles(poses)
        self.scene.sync_traffic_lights()

        # stats
        metrics = self.engine.get_advanced_metrics()
        
        # New: Get max queue and dominant markov state
        max_q = 0
        state_counts = defaultdict(int)
        for r in self.net.roads.values():
            max_q = max(max_q, r.queue_length)
            state_counts[r.current_state] += 1
        
        dominant_state = "Fluide"
        if state_counts:
            # Get the state name from the Enum
            from core.models import RoadState
            dom_enum = max(state_counts, key=state_counts.get)
            dominant_state = dom_enum.name
            
        self.controls.set_stats(metrics, max_queue=max_q, markov_state=dominant_state)

        # Analysis: Heatmap
        self._update_heatmap()
        
        # Status bar info
        status = f"Temps sim: {self.engine.current_time:.1f}s | Véhicules: {len(self.engine.vehicles)} | "
        status += "EN PAUSE" if not self._playing else f"Vitesse: {self._speed_factor:.1f}x"
        self.statusBar().showMessage(status)

    def _update_heatmap(self):
        # Calculate avg speed per road
        road_speeds = defaultdict(list)
        for v in self.engine.vehicles.values():
            road_speeds[v.road_id].append(v.v)
        
        for rid, item in self.scene.road_items.items():
            road = self.net.roads.get(rid)
            if not road: continue
            
            speeds = road_speeds.get(rid, [])
            if not speeds:
                # No cars = Fluid
                color = QColor("darkGray")
            else:
                avg_v = sum(speeds) / len(speeds)
                ratio = avg_v / road.speed_limit
                
                # Lerp between Red (0) and Green (1)
                if ratio < 0.3: color = QColor("red")
                elif ratio < 0.7: color = QColor("orange")
                else: color = QColor("darkGray")
            
            pen = item.pen()
            pen.setColor(color)
            item.setPen(pen)
        
        
    def _set_all_green(self, seconds: float):
        self._tl_green = float(seconds)
        for tl in self.net.traffic_lights.values():
            tl.green = self._tl_green

    def _set_all_red(self, seconds: float):
        self._tl_red = float(seconds)
        for tl in self.net.traffic_lights.values():
            tl.red = self._tl_red