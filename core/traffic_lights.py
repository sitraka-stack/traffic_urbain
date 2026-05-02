from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TrafficLight:
    node_id: int
    t: float = 0.0
    green_duration: float = 8.0
    yellow_duration: float = 2.0
    all_red_duration: float = 1.0

    # phases[i] = list of incoming road IDs that are green together
    phases: List[List[int]] = field(default_factory=list)
    current_phase_index: int = 0
    
    adaptive: bool = True
    phase_timer: float = 0.0
    min_green: float = 5.0
    max_green: float = 20.0

    def step(self, dt: float, road_counts: Dict[int, int] = None) -> None:
        if not self.phases:
            return
            
        self.t += dt
        
        if not self.adaptive:
            return

        # Adaptive logic: stay in current phase if cars are waiting, 
        # but respect min/max limits
        self.phase_timer += dt
        
        # Calculate demand for current phase vs others
        current_roads = self.phases[self.current_phase_index]
        current_demand = sum(road_counts.get(rid, 0) for rid in current_roads) if road_counts else 0
        
        other_demand = 0
        if road_counts:
            for i, p in enumerate(self.phases):
                if i != self.current_phase_index:
                    other_demand += sum(road_counts.get(rid, 0) for rid in p)

        # Switch condition
        should_switch = False
        if self.phase_timer > self.max_green:
            should_switch = True
        elif self.phase_timer > self.min_green and other_demand > current_demand + 2:
            should_switch = True
        elif self.phase_timer > self.min_green and current_demand == 0 and other_demand > 0:
            should_switch = True

        if should_switch:
            self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)
            self.phase_timer = 0.0
            # Reset t to start of new phase visually
            phase_total = self.green_duration + self.yellow_duration + self.all_red_duration
            self.t = self.current_phase_index * phase_total

    def get_cycle_duration(self) -> float:
        num_phases = len(self.phases)
        if num_phases == 0: return 1.0
        # Each phase has: Green + Yellow + All-Red
        return num_phases * (self.green_duration + self.yellow_duration + self.all_red_duration)

    def is_green(self, road_id: int) -> bool:
        if not self.phases:
            return True

        cycle = self.get_cycle_duration()
        time_in_cycle = self.t % cycle

        phase_time = self.green_duration + self.yellow_duration + self.all_red_duration
        current_phase_idx = int(time_in_cycle // phase_time)

        if current_phase_idx >= len(self.phases):
            return False # Safety

        # Is this road in the active phase?
        if road_id not in self.phases[current_phase_idx]:
            return False

        # Only green during the first 'green_duration' of the phase
        time_in_phase = time_in_cycle % phase_time
        return time_in_phase < self.green_duration

    def is_yellow(self, road_id: int) -> bool:
        if not self.phases:
            return False

        cycle = self.get_cycle_duration()
        time_in_cycle = self.t % cycle

        phase_time = self.green_duration + self.yellow_duration + self.all_red_duration
        current_phase_idx = int(time_in_cycle // phase_time)

        if road_id not in self.phases[current_phase_idx]:
            return False

        time_in_phase = time_in_cycle % phase_time
        return self.green_duration <= time_in_phase < (self.green_duration + self.yellow_duration)