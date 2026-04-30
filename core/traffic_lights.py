from __future__ import annotations
from dataclasses import dataclass

@dataclass
class TrafficLight:
    node_id: int
    t: float = 0.0
    green: float = 6.0
    red: float = 6.0

    def step(self, dt: float) -> None:
        self.t += dt

    def is_green(self) -> bool:
        cycle = self.green + self.red
        if cycle <= 1e-9:
            return True
        x = self.t % cycle
        return x < self.green