"""Runtime metrics for the BLACKBOX stability gate. Not a game overlay."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field


def _rss_mb() -> float:
    try:
        import psutil

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        if os.name == "nt":
            return 0.0
        try:
            with open("/proc/self/statm", encoding="utf-8") as fh:
                pages = int(fh.read().split()[0])
            return pages * os.sysconf("SC_PAGE_SIZE") / (1024.0 * 1024.0)
        except Exception:
            return 0.0


def _vram_mb() -> float:
    try:
        import subprocess

        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=used_memory", "--format=csv,noheader,nounits"],
            timeout=1.5,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        vals = [float(x.strip()) for x in out.splitlines() if x.strip()]
        return float(sum(vals)) if vals else 0.0
    except Exception:
        return 0.0


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    i = max(0, min(len(ordered) - 1, int(math.ceil(p / 100.0 * len(ordered)) - 1)))
    return float(ordered[i])


@dataclass
class RuntimeMetrics:
    started: float = field(default_factory=time.perf_counter)
    frames: int = 0
    frame_ms: list[float] = field(default_factory=list)
    phys_steps: int = 0
    phys_misses: int = 0
    recorder_writes: int = 0
    recorder_expected: int = 0
    audio_underruns: int = 0
    cerber_latency_ms: list[float] = field(default_factory=list)
    world_gen_ms: float = 0.0
    rss_mb: list[float] = field(default_factory=list)
    rss_after_unload_mb: list[float] = field(default_factory=list)
    vram_mb: float = 0.0
    sectors_loaded: int = 0
    props_active: int = 0
    activity_lod: dict = field(default_factory=dict)
    discovered: list = field(default_factory=list)
    duplicate_activity: int = 0
    crashed: bool = False
    spiral: bool = False
    last_phase: str = ""
    _frame_t: float = field(default_factory=time.perf_counter)
    _last_sectors: int = 0

    def begin_frame(self) -> None:
        self._frame_t = time.perf_counter()

    def end_frame(self, dt_wall: float | None = None) -> None:
        ms = (dt_wall if dt_wall is not None else (time.perf_counter() - self._frame_t)) * 1000.0
        self.frames += 1
        if len(self.frame_ms) < 120000:
            self.frame_ms.append(ms)
        elif self.frames % 8 == 0:
            self.frame_ms.append(ms)
            if len(self.frame_ms) > 140000:
                self.frame_ms = self.frame_ms[-80000:]

    def sample_memory(self, *, sectors: int) -> None:
        rss = _rss_mb()
        self.rss_mb.append(rss)
        if sectors < self._last_sectors:
            self.rss_after_unload_mb.append(rss)
        self._last_sectors = sectors
        if self.frames % 120 == 0:
            self.vram_mb = _vram_mb()

    def summary(self, *, wall_s: float, sim_s: float) -> dict:
        fps = self.frames / max(1e-6, wall_s)
        rss = self.rss_mb
        growth = (rss[-1] - rss[0]) if len(rss) >= 2 else 0.0
        unload = self.rss_after_unload_mb
        return {
            "wall_s": wall_s,
            "sim_s": sim_s,
            "fps": fps,
            "frame_ms_p50": _percentile(self.frame_ms, 50),
            "frame_ms_p95": _percentile(self.frame_ms, 95),
            "frame_ms_p99": _percentile(self.frame_ms, 99),
            "physics_ticks": self.phys_steps,
            "physics_tick_misses": self.phys_misses,
            "cerber_latency_ms_p50": _percentile(self.cerber_latency_ms, 50),
            "cerber_latency_ms_p95": _percentile(self.cerber_latency_ms, 95),
            "loaded_sectors": self.sectors_loaded,
            "active_props": self.props_active,
            "activity_entities_by_lod": dict(self.activity_lod),
            "ram_mb": rss[-1] if rss else _rss_mb(),
            "ram_mb_start": rss[0] if rss else 0.0,
            "ram_mb_growth": growth,
            "ram_mb_after_unload": unload[-1] if unload else None,
            "vram_mb": self.vram_mb,
            "audio_underruns": self.audio_underruns,
            "recorder_writes": self.recorder_writes,
            "recorder_expected": self.recorder_expected,
            "recorder_queue_lag": max(0, self.recorder_expected - self.recorder_writes),
            "world_generation_ms": self.world_gen_ms,
            "discovered": list(self.discovered),
            "duplicate_activity": self.duplicate_activity,
            "crashed": self.crashed,
            "simulation_spiral": self.spiral,
            "last_phase": self.last_phase,
        }
