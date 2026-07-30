"""Swarm Health state machine — aging by status stamp."""

from __future__ import annotations

from enum import Enum


class SwarmHealthState(str, Enum):
    ONLINE = "ONLINE"
    LIMITED = "LIMITED"
    LOST = "LOST"
    RECOVERED = "RECOVERED"


# Age thresholds (seconds) — locked for DMI v1 unit tests / practice
LIMITED_AFTER_S = 1.0
LOST_AFTER_S = 3.0


def health_to_factor(state: SwarmHealthState) -> float:
    if state == SwarmHealthState.ONLINE:
        return 1.0
    if state == SwarmHealthState.RECOVERED:
        return 0.85
    if state == SwarmHealthState.LIMITED:
        return 0.4
    return 0.0


def age_health(
    *,
    previous: SwarmHealthState,
    now_s: float,
    last_status_stamp_s: float | None,
    reported_ok: bool,
) -> SwarmHealthState:
    """Derive Swarm Health from freshness and a boolean capability flag.

    reported_ok=False while fresh → LIMITED.
    Age past LOST_AFTER_S → LOST.
    Fresh + ok after LOST/LIMITED → RECOVERED then next tick can be ONLINE if still ok.
    """
    if last_status_stamp_s is None:
        return SwarmHealthState.LOST
    age = now_s - last_status_stamp_s
    if age < 0.0:
        raise ValueError("status stamp is in the future relative to now_s")

    if age > LOST_AFTER_S:
        return SwarmHealthState.LOST
    if age > LIMITED_AFTER_S:
        return SwarmHealthState.LIMITED

    if not reported_ok:
        return SwarmHealthState.LIMITED

    if previous in (SwarmHealthState.LOST, SwarmHealthState.LIMITED, SwarmHealthState.RECOVERED):
        if previous == SwarmHealthState.RECOVERED:
            return SwarmHealthState.ONLINE
        return SwarmHealthState.RECOVERED
    return SwarmHealthState.ONLINE
