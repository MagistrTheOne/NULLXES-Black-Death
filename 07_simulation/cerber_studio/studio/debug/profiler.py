"""Engineering frame profiler. Log every 2s, never every frame."""

from __future__ import annotations

import logging
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field

from ..config.paths import log_dir
from ..sim.metrics import _percentile, _rss_mb, _vram_mb

log = logging.getLogger("cerber_studio.profiler")

SCOPES = (
    "update",
    "physics",
    "world",
    "activity",
    "atmosphere",
    "cerber",
    "ui",
)


@dataclass
class FrameSample:
    frame_ms: float = 0.0
    update_ms: float = 0.0
    physics_ms: float = 0.0
    world_ms: float = 0.0
    activity_ms: float = 0.0
    atmosphere_ms: float = 0.0
    cerber_ms: float = 0.0
    ui_ms: float = 0.0


@dataclass
class SceneSnap:
    nodes: int = 0
    geoms: int = 0
    triangles: int = 0
    draw_calls: int = 0
    sectors: int = 0
    props: int = 0
    entities: int = 0
    ram_mb: float = 0.0
    vram_mb: float = 0.0


def count_scene(root) -> tuple[int, int, int]:
    nodes = 0
    geoms = 0
    tris = 0
    stack = [root]
    while stack:
        np = stack.pop()
        nodes += 1
        try:
            stack.extend(np.getChildren())
        except Exception:
            continue
        try:
            node = np.node()
        except Exception:
            continue
        ngeom = getattr(node, "getNumGeoms", None)
        if ngeom is None:
            continue
        try:
            count = int(ngeom())
        except Exception:
            continue
        geoms += count
        for i in range(count):
            try:
                geom = node.getGeom(i)
                for j in range(geom.getNumPrimitives()):
                    prim = geom.getPrimitive(j)
                    nv = int(prim.getNumVertices())
                    tris += max(0, nv // 3)
            except Exception:
                continue
    return nodes, geoms, tris


def overlay_text(fps: float, sample: FrameSample, snap: SceneSnap, scope: str) -> str:
    return (
        f"F3 PERFORMANCE   scope {scope.upper()}\n"
        f"FPS          {fps:6.1f}\n"
        f"FRAME ms     {sample.frame_ms:6.2f}\n"
        f"UPDATE ms    {sample.update_ms:6.2f}\n"
        f"PHYSICS ms   {sample.physics_ms:6.2f}\n"
        f"WORLD ms     {sample.world_ms:6.2f}\n"
        f"ACTIVITY ms  {sample.activity_ms:6.2f}\n"
        f"ATMOS ms     {sample.atmosphere_ms:6.2f}\n"
        f"CERBER ms    {sample.cerber_ms:6.2f}\n"
        f"UI ms        {sample.ui_ms:6.2f}\n"
        f"DRAW CALLS   {snap.draw_calls}\n"
        f"SCENE NODES  {snap.nodes}\n"
        f"TRIANGLES    {snap.triangles}\n"
        f"SECTORS      {snap.sectors}\n"
        f"PROPS        {snap.props}\n"
        f"ENTITIES     {snap.entities}\n"
        f"RAM MB       {snap.ram_mb:7.1f}\n"
        f"VRAM MB      {snap.vram_mb:7.1f}"
    )


@dataclass
class FrameProfiler:
    enabled: bool = False
    samples: deque = field(default_factory=lambda: deque(maxlen=600))
    current: FrameSample = field(default_factory=FrameSample)
    snap: SceneSnap = field(default_factory=SceneSnap)
    fps: float = 0.0
    _frame_t: float = field(default_factory=time.perf_counter)
    _last_log: float = 0.0
    _last_snap: float = 0.0
    _acc: dict = field(default_factory=dict)

    def begin_frame(self) -> None:
        self._frame_t = time.perf_counter()
        self.current = FrameSample()
        self._acc = {k: 0.0 for k in SCOPES}

    @contextmanager
    def span(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self._acc[name] = self._acc.get(name, 0.0) + (time.perf_counter() - t0) * 1000.0

    def add_ms(self, name: str, ms: float) -> None:
        self._acc[name] = self._acc.get(name, 0.0) + float(ms)

    def end_frame(self, *, dt: float) -> FrameSample:
        sample = self.current
        sample.frame_ms = (time.perf_counter() - self._frame_t) * 1000.0
        sample.update_ms = self._acc.get("update", 0.0)
        sample.physics_ms = self._acc.get("physics", 0.0)
        sample.world_ms = self._acc.get("world", 0.0)
        sample.activity_ms = self._acc.get("activity", 0.0)
        sample.atmosphere_ms = self._acc.get("atmosphere", 0.0)
        sample.cerber_ms = self._acc.get("cerber", 0.0)
        sample.ui_ms = self._acc.get("ui", 0.0)
        self.samples.append(sample)
        self.fps = 1.0 / dt if dt > 1e-6 else 0.0
        now = time.perf_counter()
        if now - self._last_log >= 2.0:
            self._last_log = now
            self._emit_log()
        return sample

    def refresh_snap(self, root, *, sectors: int, props: int, entities: int, force: bool = False) -> SceneSnap:
        now = time.perf_counter()
        if not force and now - self._last_snap < 2.0:
            return self.snap
        self._last_snap = now
        nodes, geoms, tris = count_scene(root)
        self.snap = SceneSnap(
            nodes=nodes,
            geoms=geoms,
            triangles=tris,
            draw_calls=geoms,
            sectors=sectors,
            props=props,
            entities=entities,
            ram_mb=_rss_mb(),
            vram_mb=_vram_mb(),
        )
        return self.snap

    def percentiles(self) -> tuple[float, float, float, float]:
        values = [s.frame_ms for s in self.samples]
        if not values:
            return 0.0, 0.0, 0.0, 0.0
        return (
            _percentile(values, 50),
            _percentile(values, 95),
            _percentile(values, 99),
            max(values),
        )

    def overlay(self, scope: str) -> str:
        sample = self.samples[-1] if self.samples else FrameSample()
        p50, p95, p99, pmax = self.percentiles()
        body = overlay_text(self.fps, sample, self.snap, scope)
        return f"{body}\nP50/P95/P99/MAX  {p50:.1f}  {p95:.1f}  {p99:.1f}  {pmax:.1f}"

    def _emit_log(self) -> None:
        if not self.samples:
            return
        p50, p95, p99, pmax = self.percentiles()
        last = self.samples[-1]
        line = (
            f"fps={self.fps:.1f} frame={last.frame_ms:.2f} "
            f"p50={p50:.1f} p95={p95:.1f} p99={p99:.1f} max={pmax:.1f} "
            f"phys={last.physics_ms:.2f} world={last.world_ms:.2f} "
            f"act={last.activity_ms:.2f} nodes={self.snap.nodes} "
            f"sectors={self.snap.sectors} ram={self.snap.ram_mb:.0f}"
        )
        log.info("%s", line)
        try:
            path = log_dir() / "perf.log"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%H:%M:%S')} {line}\n")
        except Exception:
            pass
