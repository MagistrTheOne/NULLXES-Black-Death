"""Cross-channel heartbeat for dual-compute A/B."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Heartbeat:
    channel_id: str
    seq: int
    stamp_s: float
    healthy: bool


class HeartbeatMonitor:
    def __init__(self, peer_id: str, timeout_s: float = 0.15) -> None:
        self.peer_id = peer_id
        self.timeout_s = timeout_s
        self._last: Heartbeat | None = None

    def update(self, hb: Heartbeat) -> None:
        if hb.channel_id != self.peer_id:
            return
        self._last = hb

    def peer_alive(self, now_s: float | None = None) -> bool:
        now = time.time() if now_s is None else now_s
        if self._last is None:
            return False
        return self._last.healthy and (now - self._last.stamp_s) <= self.timeout_s


def make_heartbeat(channel_id: str, seq: int, healthy: bool = True) -> Heartbeat:
    return Heartbeat(channel_id=channel_id, seq=seq, stamp_s=time.time(), healthy=healthy)
