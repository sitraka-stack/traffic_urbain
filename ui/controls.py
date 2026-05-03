from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
    QGroupBox, QRadioButton, QFileDialog, QScrollArea, QSpinBox
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
    manual_spawn_requested = Signal(int)    # count
    monte_carlo_requested = Signal()
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

        # Monte Carlo
        mc_box = QGroupBox("Analyse Prédictive (Monte Carlo)")
        mc_l = QVBoxLayout(mc_box)
        self.mc_btn = QPushButton("Lancer 10 simulations (60s)")
        self.mc_btn.clicked.connect(self.monte_carlo_requested.emit)
        self.mc_results = QLabel("Résultats Monte Carlo : N/A")
        self.mc_results.setWordWrap(True)
        self.mc_results.setStyleSheet("font-size: 10px; color: #34495e; background: #dfe6e9; padding: 5px; border-radius: 3px;")
        mc_l.addWidget(self.mc_btn)
        mc_l.addWidget(self.mc_results)
        layout.addWidget(mc_box)

        # simulation parameters
        sim_box = QGroupBox("Génération de Véhicules")
        sim_l = QVBoxLayout(sim_box)

        auto_box = QGroupBox("Mode Automatique")
        auto_l = QVBoxLayout(auto_box)
        self.spawn_label = QLabel("Taux: 0.4 veh/s")
        self.spawn_slider = QSlider(Qt.Orientation.Horizontal)
        self.spawn_slider.setRange(0, 50)
        self.spawn_slider.setValue(4)
        self.spawn_slider.valueChanged.connect(self._on_spawn)
        auto_l.addWidget(self.spawn_label)
        auto_l.addWidget(self.spawn_slider)
        sim_l.addWidget(auto_box)

        manual_box = QGroupBox("Mode Manuel")
        manual_l = QVBoxLayout(manual_box)
        row_man = QHBoxLayout()
        self.spawn_count = QSpinBox()
        self.spawn_count.setRange(1, 100)
        self.spawn_count.setValue(5)
        self.spawn_btn = QPushButton("Ajouter")
        self.spawn_btn.clicked.connect(lambda: self.manual_spawn_requested.emit(self.spawn_count.value()))
        row_man.addWidget(self.spawn_count)
        row_man.addWidget(self.spawn_btn)
        manual_l.addLayout(row_man)
        sim_l.addWidget(manual_box)
        layout.addWidget(sim_box)

        speed_box = QGroupBox("Vitesse Simulation")
        speed_l = QVBoxLayout(speed_box)
        self.speed_label = QLabel("Vitesse: 1.0x")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self._on_speed)
        speed_l.addWidget(self.speed_label)
        speed_l.addWidget(self.speed_slider)
        layout.addWidget(speed_box)

        tl_box = QGroupBox("Feux de circulation (secondes)")
        tl_l = QVBoxLayout(tl_box)
        self.green_label = QLabel("Vert: 6.0 s")
        self.green_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_slider.setRange(1, 300)
        self.green_slider.setValue(60)
        self.green_slider.valueChanged.connect(self._on_green)
        self.red_label = QLabel("Rouge: 6.0 s")
        self.red_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_slider.setRange(1, 300)
        self.red_slider.setValue(60)
        self.red_slider.valueChanged.connect(self._on_red)
        tl_l.addWidget(self.green_label)
        tl_l.addWidget(self.green_slider)
        tl_l.addWidget(self.red_label)
        tl_l.addWidget(self.red_slider)
        layout.addWidget(tl_box)

        mode_box = QGroupBox("Mode édition")
        mode_l = QVBoxLayout(mode_box)
        self.rb_select = QRadioButton("Sélection")
        self.rb_add_node = QRadioButton("Ajouter intersection")
        self.rb_add_road = QRadioButton("Ajouter route (A puis B)")
        self.rb_add_roundabout = QRadioButton("Ajouter rond-point")
        self.rb_add_building = QRadioButton("Ajouter bâtiment")
        self.rb_select.setChecked(True)

        self.rb_select.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.SELECT))
        self.rb_add_node.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_NODE))
        self.rb_add_road.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_ROAD))
        self.rb_add_roundabout.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_ROUNDABOUT))
        self.rb_add_building.toggled.connect(lambda checked: checked and self.mode_changed.emit(EditMode.ADD_BUILDING))

        mode_l.addWidget(self.rb_select)
        mode_l.addWidget(self.rb_add_node)
        mode_l.addWidget(self.rb_add_road)
        mode_l.addWidget(self.rb_add_roundabout)
        mode_l.addWidget(self.rb_add_building)
        layout.addWidget(mode_box)

        io_row = QHBoxLayout()
        self.btn_save = QPushButton("Save JSON")
        self.btn_load = QPushButton("Load JSON")
        self.btn_save.clicked.connect(self._save)
        self.btn_load.clicked.connect(self._load)
        io_row.addWidget(self.btn_save)
        io_row.addWidget(self.btn_load)
        layout.addLayout(io_row)

        # stats
        stats_box = QGroupBox("Analyse en Temps Réel")
        stats_l = QVBoxLayout(stats_box)
        self.lbl_nb = QLabel("Véhicules: 0")
        self.lbl_avg = QLabel("Vitesse moyenne: 0.0 m/s")
        self.lbl_waiting = QLabel("En attente: 0")
        self.lbl_queue = QLabel("File d'attente max: 0")
        self.lbl_markov = QLabel("État Markov: Fluide")
        self.lbl_finished = QLabel("Sorties: 0")
        self.lbl_time = QLabel("Trajet moyen: 0.0s")
        self.lbl_congestion = QLabel("État: Fluide")
        
        stats_l.addWidget(self.lbl_nb)
        stats_l.addWidget(self.lbl_avg)
        stats_l.addWidget(self.lbl_waiting)
        stats_l.addWidget(self.lbl_queue)
        stats_l.addWidget(self.lbl_markov)
        stats_l.addWidget(self.lbl_finished)
        stats_l.addWidget(self.lbl_time)
        stats_l.addWidget(self.lbl_congestion)
        layout.addWidget(stats_box)

        # AI Assistant Section
        advisor_box = QGroupBox("Assistant IA (Conseils)")
        advisor_l = QVBoxLayout(advisor_box)
        self.lbl_advice = QLabel("En attente de données...")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setStyleSheet("color: #2c3e50; font-style: italic; background: #fdf9d2; padding: 8px; border-radius: 5px; border: 1px solid #f1c40f;")
        advisor_l.addWidget(self.lbl_advice)
        layout.addWidget(advisor_box)

        layout.addStretch(1)

    def _on_green(self, v: int):
        seconds = v / 10.0
        self.green_label.setText(f"Vert: {seconds:.1f} s")
        self.traffic_green_changed.emit(seconds)

    def _on_red(self, v: int):
        seconds = v / 10.0
        self.red_label.setText(f"Rouge: {seconds:.1f} s")
        self.traffic_red_changed.emit(seconds)

    def set_stats(self, metrics: dict, max_queue: int = 0, markov_state: str = "N/A"):
        self.lbl_nb.setText(f"Véhicules: {metrics['count']}")
        self.lbl_avg.setText(f"Vitesse moyenne: {metrics['avg_speed']:.2f} m/s")
        self.lbl_waiting.setText(f"En attente: {metrics['waiting_count']}")
        self.lbl_queue.setText(f"File d'attente max: {max_queue}")
        self.lbl_markov.setText(f"État Markov: {markov_state}")
        self.lbl_finished.setText(f"Sorties: {metrics['total_finished']}")
        self.lbl_time.setText(f"Trajet moyen: {metrics['avg_travel_time']:.1f}s")
        self.lbl_congestion.setText(f"État global: {metrics['congestion_level']}")
        
        color = "green"
        if metrics['congestion_level'] == "Modéré": color = "orange"
        elif metrics['congestion_level'] == "Dense": color = "red"
        elif metrics['congestion_level'] == "Bouchon": color = "darkred"
        self.lbl_congestion.setStyleSheet(f"color: {color}; font-weight: bold;")

        # --- AI ADVISOR LOGIC ---
        advice = "<b>SITUATION NORMALE :</b> Le trafic est fluide. Le réseau peut absorber plus de véhicules."
        
        if metrics['count'] > 0:
            if markov_state == "JAM":
                advice = "<b>CRITIQUE :</b> Des bouchons persistants sont détectés (Chaîne de Markov). Augmentez d'urgence le temps de feu vert sur les axes rouges."
            elif max_queue > 8:
                advice = f"<b>ALERTE :</b> File d'attente de {max_queue} véhicules détectée. L'intersection est saturée. Envisagez de réduire le taux d'apparition automatique."
            elif metrics['congestion_level'] == "Dense":
                advice = "<b>AVERTISSEMENT :</b> Densité élevée. Lancez une <i>Analyse Monte Carlo</i> pour prédire si le réseau va saturez dans les 60 prochaines secondes."
            elif metrics['avg_speed'] < 5.0:
                advice = "<b>OPTIMISATION :</b> Vitesse moyenne basse. Vos routes sont peut-être trop courtes ou vos feux trop longs."

        self.lbl_advice.setText(advice)

    def set_monte_carlo_results(self, res: dict):
        text = (f"<b>Résultats Analyse (10 scénarios) :</b><br/>"
                f"- Capacité système: {res['avg_finished']:.1f} veh/min<br/>"
                f"- Stabilité vitesse: {res['avg_speed']:.2f} m/s<br/>"
                f"- Risque attente: {res['avg_travel_time']:.1f}s")
        self.mc_results.setText(text)
        
        # Immediate IA update based on MC
        if res['avg_finished'] < 5.0 and self.playing:
            self.lbl_advice.setText("<b>RÉSULTAT MONTE CARLO :</b> Le débit est trop faible. Votre configuration actuelle risque de paralyser le réseau à long terme.")

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
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", "network.json", "JSON (*.json)")
        if path: self.save_requested.emit(path)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger", "", "JSON (*.json)")
        if path: self.load_requested.emit(path)
