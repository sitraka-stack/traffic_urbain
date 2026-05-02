from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
    QGroupBox, QRadioButton, QFileDialog, QScrollArea
)

from ui.scene import EditMode


class Controls(QWidget):
    play_toggled = Signal(bool)
    speed_changed = Signal(float)
    mode_changed = Signal(object)
    save_requested = Signal(str)
    load_requested = Signal(str)

    traffic_green_changed = Signal(float)  # seconds
    traffic_red_changed = Signal(float)    # seconds
    spawn_rate_changed = Signal(float)     # veh/s
    clear_requested = Signal()

    def __init__(self):
        super().__init__()
        
        # Scroll Area Setup
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll.setWidget(self.scroll_content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll)
        
        layout = QVBoxLayout(self.scroll_content)

        # play/pause/clear
        row0 = QHBoxLayout()
        self.play_btn = QPushButton("Pause")
        self.playing = True
        self.play_btn.clicked.connect(self._toggle_play)
        self.clear_btn = QPushButton("Effacer tout")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        row0.addWidget(self.play_btn)
        row0.addWidget(self.clear_btn)
        layout.addLayout(row0)

        # simulation parameters
        sim_box = QGroupBox("Paramètres Simulation")
        sim_l = QVBoxLayout(sim_box)

        # speed slider
        self.speed_label = QLabel("Vitesse: 1.0x")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)   # 0.1 .. 10.0
        self.speed_slider.setValue(10)       # 1.0
        self.speed_slider.valueChanged.connect(self._on_speed)
        sim_l.addWidget(self.speed_label)
        sim_l.addWidget(self.speed_slider)

        # spawn rate
        self.spawn_label = QLabel("Apparition: 0.4 veh/s")
        self.spawn_slider = QSlider(Qt.Orientation.Horizontal)
        self.spawn_slider.setRange(0, 20)    # 0.0 .. 2.0
        self.spawn_slider.setValue(4)        # 0.4
        self.spawn_slider.valueChanged.connect(self._on_spawn)
        sim_l.addWidget(self.spawn_label)
        sim_l.addWidget(self.spawn_slider)

        layout.addWidget(sim_box)

        # traffic lights controls (0.1s .. 30.0s)
        tl_box = QGroupBox("Feux de circulation (secondes)")
        tl_l = QVBoxLayout(tl_box)

        self.green_label = QLabel("Vert: 6.0 s")
        self.green_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_slider.setRange(1, 300)   # 0.1 .. 30.0
        self.green_slider.setValue(60)       # 6.0
        self.green_slider.valueChanged.connect(self._on_green)

        self.red_label = QLabel("Rouge: 6.0 s")
        self.red_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_slider.setRange(1, 300)     # 0.1 .. 30.0
        self.red_slider.setValue(60)         # 6.0
        self.red_slider.valueChanged.connect(self._on_red)

        tl_l.addWidget(self.green_label)
        tl_l.addWidget(self.green_slider)
        tl_l.addWidget(self.red_label)
        tl_l.addWidget(self.red_slider)
        layout.addWidget(tl_box)

        # edit modes
        mode_box = QGroupBox("Mode édition")
        mode_l = QVBoxLayout(mode_box)
        self.rb_select = QRadioButton("Sélection")
        self.rb_add_node = QRadioButton("Ajouter intersection")
        self.rb_add_road = QRadioButton("Ajouter route (A puis B)")
        self.rb_add_roundabout = QRadioButton("Ajouter rond-point")
        self.rb_select.setChecked(True)

        self.rb_select.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.SELECT))
        self.rb_add_node.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_NODE))
        self.rb_add_road.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_ROAD))
        self.rb_add_roundabout.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_ROUNDABOUT))

        mode_l.addWidget(self.rb_select)
        mode_l.addWidget(self.rb_add_node)
        mode_l.addWidget(self.rb_add_road)
        mode_l.addWidget(self.rb_add_roundabout)
        layout.addWidget(mode_box)

        # save/load
        io_row = QHBoxLayout()
        self.btn_save = QPushButton("Save JSON")
        self.btn_load = QPushButton("Load JSON")
        self.btn_save.clicked.connect(self._save)
        self.btn_load.clicked.connect(self._load)
        io_row.addWidget(self.btn_save)
        io_row.addWidget(self.btn_load)
        layout.addLayout(io_row)

        # stats
        stats_box = QGroupBox("Tableau de bord")
        stats_l = QVBoxLayout(stats_box)
        self.lbl_nb = QLabel("Véhicules: 0")
        self.lbl_avg = QLabel("Vitesse moyenne: 0.0 m/s")
        self.lbl_waiting = QLabel("En attente: 0")
        self.lbl_finished = QLabel("Sorties: 0")
        self.lbl_time = QLabel("Trajet moyen: 0.0s")
        self.lbl_busiest = QLabel("Route chargée: Aucune")
        self.lbl_congestion = QLabel("État: Fluide")
        
        stats_l.addWidget(self.lbl_nb)
        stats_l.addWidget(self.lbl_avg)
        stats_l.addWidget(self.lbl_waiting)
        stats_l.addWidget(self.lbl_finished)
        stats_l.addWidget(self.lbl_time)
        stats_l.addWidget(self.lbl_busiest)
        stats_l.addWidget(self.lbl_congestion)
        layout.addWidget(stats_box)

        # Legend
        legend_box = QGroupBox("Légende Heatmap")
        legend_l = QVBoxLayout(legend_box)
        
        def add_legend_item(color, text):
            row = QHBoxLayout()
            swatch = QLabel()
            swatch.setFixedSize(16, 16)
            swatch.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
            label = QLabel(text)
            row.addWidget(swatch)
            row.addWidget(label)
            row.addStretch()
            legend_l.addLayout(row)

        add_legend_item("red", "Congestion forte (<30% vitesse max)")
        add_legend_item("orange", "Trafic ralenti (30-70% vitesse max)")
        add_legend_item("darkGray", "Trafic fluide ou route vide")
        layout.addWidget(legend_box)

        # Info
        info_box = QGroupBox("Informations")
        info_l = QVBoxLayout(info_box)
        info_text = QLabel(
            "<b>Commandes:</b><br/>"
            "- Clic gauche: Sélectionner / Poser<br/>"
            "- Clic droit: Supprimer<br/>"
            "- Roulette: Zoom<br/>"
            "- Clic milieu: Pan"
        )
        info_text.setWordWrap(True)
        info_l.addWidget(info_text)
        layout.addWidget(info_box)

        layout.addStretch(1)

    def _on_green(self, v: int):
        seconds = v / 10.0
        self.green_label.setText(f"Vert: {seconds:.1f} s")
        self.traffic_green_changed.emit(seconds)

    def _on_red(self, v: int):
        seconds = v / 10.0
        self.red_label.setText(f"Rouge: {seconds:.1f} s")
        self.traffic_red_changed.emit(seconds)

    def set_stats(self, metrics: dict):
        self.lbl_nb.setText(f"Véhicules: {metrics['count']}")
        self.lbl_avg.setText(f"Vitesse moyenne: {metrics['avg_speed']:.2f} m/s")
        self.lbl_waiting.setText(f"En attente: {metrics['waiting_count']}")
        self.lbl_finished.setText(f"Sorties: {metrics['total_finished']}")
        self.lbl_time.setText(f"Trajet moyen: {metrics['avg_travel_time']:.1f}s")
        self.lbl_busiest.setText(f"Route chargée: {metrics['busiest_road']}")
        self.lbl_congestion.setText(f"État: {metrics['congestion_level']}")
        
        # Style pour la congestion
        color = "green"
        if metrics['congestion_level'] == "Modéré": color = "orange"
        elif metrics['congestion_level'] == "Dense": color = "red"
        elif metrics['congestion_level'] == "Bouchon": color = "darkred"
        self.lbl_congestion.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_btn.setText("Pause" if self.playing else "Play")
        self.play_toggled.emit(self.playing)

    def _on_speed(self, v: int):
        factor = v / 10.0
        self.speed_label.setText(f"Vitesse: {factor:.1f}x")
        self.speed_changed.emit(factor)

    def _on_spawn(self, v: int):
        rate = v / 10.0
        self.spawn_label.setText(f"Apparition: {rate:.1f} veh/s")
        self.spawn_rate_changed.emit(rate)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la carte", "network.json", "JSON (*.json)")
        if path:
            self.save_requested.emit(path)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger une carte", "", "JSON (*.json)")
        if path:
            self.load_requested.emit(path)