"""Own-ship GNSS integrity under jam/spoof. Detect only — no emitter, no jam cookbook."""

from __future__ import annotations

from dataclasses import dataclass

from soft_bus.messages import GnssFix

# Alpha V_dive ≈ 43 m/s; jump beyond this + margin is spoof-class, not flight.
_MAX_SPEED_MPS = 80.0
_HDOP_JAM = 8.0
_STALE_S = 5.0


@dataclass(frozen=True)
class GnssIntegrity:
    ok: bool
    reason: str
    hdop: float
    jump_m: float
    stamp_s: float


class GnssIntegrityMonitor:
    def __init__(self) -> None:
        self._prev: GnssFix | None = None

    def update(self, fix: GnssFix) -> GnssIntegrity:
        prev = self._prev
        self._prev = fix
        return assess_gnss_integrity(prev, fix)


def assess_gnss_integrity(prev: GnssFix | None, cur: GnssFix) -> GnssIntegrity:
    hdop = float(cur.hdop)
    stamp = float(cur.stamp_s)
    if not cur.fix_ok:
        return GnssIntegrity(False, "jam_loss", hdop, 0.0, stamp)
    if hdop >= _HDOP_JAM:
        return GnssIntegrity(False, "hdop_high", hdop, 0.0, stamp)
    if prev is None:
        return GnssIntegrity(True, "ok", hdop, 0.0, stamp)
    dt = stamp - float(prev.stamp_s)
    if dt < 0.0:
        return GnssIntegrity(False, "stale", hdop, 0.0, stamp)
    if dt > _STALE_S and not prev.fix_ok:
        return GnssIntegrity(False, "stale", hdop, 0.0, stamp)
    dx = float(cur.x) - float(prev.x)
    dy = float(cur.y) - float(prev.y)
    dz = float(cur.z) - float(prev.z)
    jump = (dx * dx + dy * dy + dz * dz) ** 0.5
    if dt > 1e-3:
        speed = jump / dt
        if speed > _MAX_SPEED_MPS:
            return GnssIntegrity(False, "spoof_jump", hdop, jump, stamp)
    elif jump > _MAX_SPEED_MPS * 0.2:
        return GnssIntegrity(False, "spoof_jump", hdop, jump, stamp)
    return GnssIntegrity(True, "ok", hdop, jump, stamp)
