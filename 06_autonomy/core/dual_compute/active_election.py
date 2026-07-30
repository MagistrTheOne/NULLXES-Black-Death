"""Active channel election for dual-compute A/B."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ElectionConfig:
    prefer: str = "A"
    sticky_after_failover: bool = True


@dataclass
class ElectionState:
    active: str
    failover_latched: bool = False


class ActiveElection:
    def __init__(self, cfg: ElectionConfig | None = None) -> None:
        self.cfg = cfg or ElectionConfig()
        self.state = ElectionState(active=self.cfg.prefer)

    def step(self, a_alive: bool, b_alive: bool) -> str:
        pref = self.cfg.prefer
        other = "B" if pref == "A" else "A"
        alive = {"A": a_alive, "B": b_alive}

        if alive[self.state.active]:
            return self.state.active

        # active dead → switch if peer alive
        if alive[other]:
            self.state.active = other
            self.state.failover_latched = True
            return self.state.active

        # both dead — keep last declared; L0 contingency owns the vehicle
        return self.state.active

    def maybe_restore(self, a_alive: bool, b_alive: bool) -> str:
        if self.cfg.sticky_after_failover and self.state.failover_latched:
            return self.state.active
        if a_alive and b_alive:
            self.state.active = self.cfg.prefer
            self.state.failover_latched = False
        return self.state.active
