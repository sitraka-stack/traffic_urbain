from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
    QGroupBox, QRadioButton, QFileDialog
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

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # play/pause
        self.play_btn = QPushButton("Pause")
        self.playing = True
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)

        # speed slider
        speed_box = QGroupBox("Vitesse (x)")
        speed_l = QVBoxLayout(speed_box)
        self.speed_label = QLabel("1.0x")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)   # 0.1 .. 10.0
        self.speed_slider.setValue(10)       # 1.0
        self.speed_slider.valueChanged.connect(self._on_speed)
        speed_l.addWidget(self.speed_label)
        speed_l.addWidget(self.speed_slider)
        layout.addWidget(speed_box)

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
        self.rb_select.setChecked(True)

        self.rb_select.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.SELECT))
        self.rb_add_node.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_NODE))
        self.rb_add_road.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_ROAD))

        mode_l.addWidget(self.rb_select)
        mode_l.addWidget(self.rb_add_node)
        mode_l.addWidget(self.rb_add_road)
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
        stats_box = QGroupBox("Stats")
        stats_l = QVBoxLayout(stats_box)
        self.lbl_nb = QLabel("Véhicules: 0")
        self.lbl_avg = QLabel("Vitesse moyenne: 0.0 m/s")
        stats_l.addWidget(self.lbl_nb)
        stats_l.addWidget(self.lbl_avg)
        layout.addWidget(stats_box)

        layout.addStretch(1)

    def _on_green(self, v: int):
        seconds = v / 10.0
        self.green_label.setText(f"Vert: {seconds:.1f} s")
        self.traffic_green_changed.emit(seconds)

    def _on_red(self, v: int):
        seconds = v / 10.0
        self.red_label.setText(f"Rouge: {seconds:.1f} s")
        self.traffic_red_changed.emit(seconds)

    def set_stats(self, nb: int, avg_speed: float):
        self.lbl_nb.setText(f"Véhicules: {nb}")
        self.lbl_avg.setText(f"Vitesse moyenne: {avg_speed:.2f} m/s")

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_btn.setText("Pause" if self.playing else "Play")
        self.play_toggled.emit(self.playing)

    def _on_speed(self, v: int):
        factor = v / 10.0
        self.speed_label.setText(f"{factor:.1f}x")
        self.speed_changed.emit(factor)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder la carte", "network.json", "JSON (*.json)")
        if path:
            self.save_requested.emit(path)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger une carte", "", "JSON (*.json)")
        if path:
            self.load_requested.emit(path)