"""Multi-rate clocks. CERBER never shares the render dt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateBudget:
    physics_hz: float = 100.0
    pilot_hz: float = 50.0
    camera_hz: float = 30.0
    cerber_hz: float = 15.0
    render_hz: float = 60.0
    hud_hz: float = 20.0
    log_hz: float = 20.0


class Accumulator:
    def __init__(self, hz: float) -> None:
        self.dt = 1.0 / float(hz)
        self.acc = 0.0

    def add(self, wall_dt: float) -> int:
        self.acc += float(max(0.0, wall_dt))
        n = 0
        # cap spiral if hitch
        while self.acc >= self.dt and n < 8:
            self.acc -= self.dt
            n += 1
        return n
