"""Event-driven publish filter — emit only on significant state change."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable


@dataclass
class EventFilter:
    """Tracks last published fingerprint per channel key."""

    _last: dict[str, Hashable] | None = None

    def __post_init__(self) -> None:
        if self._last is None:
            self._last = {}

    def should_publish(self, channel: str, fingerprint: Hashable) -> bool:
        assert self._last is not None
        prev = self._last.get(channel)
        if prev == fingerprint:
            return False
        self._last[channel] = fingerprint
        return True

    def reset(self, channel: str | None = None) -> None:
        assert self._last is not None
        if channel is None:
            self._last.clear()
        else:
            self._last.pop(channel, None)


def fingerprint_intent(intent_id: str, kind: str, sector_id: str, x: float, y: float, z: float) -> tuple:
    return (intent_id, kind, sector_id, round(x, 3), round(y, 3), round(z, 3))


def fingerprint_mode(mode: str) -> str:
    return mode


def fingerprint_health(agent_id: str, state: str) -> tuple[str, str]:
    return (agent_id, state)


def fingerprint_task(offer_id: str, kind: str) -> tuple[str, str]:
    return (offer_id, kind)


def fingerprint_fact(fact_id: str, confidence: float, stamp_s: float) -> tuple:
    return (fact_id, round(confidence, 3), round(stamp_s, 3))
