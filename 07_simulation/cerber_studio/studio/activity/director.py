"""Activity Director — graph semantics in, cheap trajectories out. No per-car AI."""

from __future__ import annotations

import math
from dataclasses import dataclass

from panda3d.core import NodePath

from ..world_gen.geom import box, cone
from ..world_gen.graph import WorldGraph

ACTIVE_M = 500.0
SIMPLE_M = 3000.0
KINEMATIC_M = 15000.0


def _lod(dist: float) -> str:
    if dist <= ACTIVE_M:
        return "active"
    if dist <= SIMPLE_M:
        return "simplified"
    if dist <= KINEMATIC_M:
        return "kinematic"
    return "abstract"


def _along(path: list[tuple[float, float]], s: float) -> tuple[float, float, float]:
    if not path:
        return 0.0, 0.0, 0.0
    if len(path) < 2:
        return path[0][0], path[0][1], 0.0
    total = 0.0
    segs: list[float] = []
    for i in range(len(path) - 1):
        d = math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        segs.append(d)
        total += d
    if total < 1.0:
        return path[0][0], path[0][1], 0.0
    d = (s % total + total) % total
    acc = 0.0
    for i, length in enumerate(segs):
        if acc + length >= d:
            t = (d - acc) / max(0.01, length)
            x0, y0 = path[i]
            x1, y1 = path[i + 1]
            yaw = math.degrees(math.atan2(x1 - x0, y1 - y0))
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, yaw
        acc += length
    return path[-1][0], path[-1][1], 0.0


@dataclass
class Actor:
    kind: str
    path: list[tuple[float, float]]
    speed: float
    s: float = 0.0
    z_off: float = 0.6
    scale: tuple[float, float, float] = (1.2, 2.4, 0.7)
    color: tuple[float, float, float] = (0.18, 0.18, 0.2)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    lod: str = "abstract"
    node: NodePath | None = None
    uid: str = ""


class ActivityDirector:
    def __init__(self, parent: NodePath, graph: WorldGraph) -> None:
        self.graph = graph
        self.root = parent.attachNewNode("activity")
        self.actors: list[Actor] = []
        self._car = box((0.22, 0.22, 0.24))
        self._plane = cone((0.55, 0.55, 0.58))
        self._boat = box((0.16, 0.22, 0.28))
        self._bird = cone((0.12, 0.12, 0.12))
        self._train = box((0.28, 0.18, 0.16))
        self._dot = box((0.35, 0.35, 0.32))
        self._build(graph)
        self._stamp_ids()

    def rebuild(self, graph: WorldGraph, parent: NodePath) -> None:
        for a in self.actors:
            if a.node is not None:
                a.node.removeNode()
        self.actors.clear()
        self.root.removeNode()
        self.graph = graph
        self.root = parent.attachNewNode("activity")
        self._build(graph)
        self._stamp_ids()

    def _stamp_ids(self) -> None:
        seen: set[str] = set()
        for i, a in enumerate(self.actors):
            a.uid = f"{a.kind}_{i}"
            seen.add(a.uid)
        self.duplicate_ids = 0

    def clear(self) -> None:
        self.rebuild(self.graph, self.root.getParent())

    def attach(self, parent: NodePath) -> None:
        self.root = parent.attachNewNode("activity")

    def _build(self, graph: WorldGraph) -> None:
        roads = [r for r in graph.roads if len(r) >= 3]
        for i, road in enumerate(roads[:6]):
            n = 6 if i == 0 else 3
            if any(graph.settlement_mask(p[0], p[1], 120) for p in road):
                n += 3
            for k in range(n):
                self.actors.append(
                    Actor(
                        kind="vehicle",
                        path=road if k % 2 == 0 else list(reversed(road)),
                        speed=12.0 + (k % 5) * 1.4,
                        s=k * 90.0,
                        z_off=0.55,
                        scale=(1.1, 2.2, 0.65),
                        color=(0.2 + (k % 3) * 0.08, 0.18, 0.16),
                    )
                )
        for af in graph.airfields:
            circuit = self._circuit(af.x, af.y, 420.0, 9)
            for k in range(3):
                self.actors.append(
                    Actor(
                        kind="aircraft",
                        path=circuit,
                        speed=28.0 + k * 4.0,
                        s=k * 180.0,
                        z_off=70.0 + k * 18.0,
                        scale=(3.2, 5.5, 0.9),
                        color=(0.62, 0.62, 0.64),
                    )
                )
            taxi = [
                (af.x - 18.0, af.y - 40.0),
                (af.x - 18.0, af.y + 80.0),
                (af.x + 16.0, af.y + 80.0),
                (af.x + 16.0, af.y - 40.0),
            ]
            for k in range(3):
                self.actors.append(
                    Actor("airport", taxi, 4.5 + k, s=k * 40.0, z_off=0.5, scale=(1.4, 2.6, 0.8), color=(0.55, 0.45, 0.18))
                )
        for river in graph.rivers[:3]:
            if graph.region_id in ("desert", "arctic") and not river:
                continue
            for k in range(2):
                self.actors.append(
                    Actor("boat", river, 5.5, s=k * 220.0, z_off=0.4, scale=(1.6, 4.2, 0.7), color=(0.18, 0.22, 0.28))
                )
        if graph.powerlines:
            rail = graph.powerlines[0]
            self.actors.append(Actor("train", rail, 18.0, s=0.0, z_off=1.4, scale=(2.2, 8.0, 1.6), color=(0.32, 0.22, 0.16)))
            self.actors.append(Actor("train", list(reversed(rail)), 16.0, s=400.0, z_off=1.4, scale=(2.2, 8.0, 1.6), color=(0.28, 0.2, 0.14)))
        for poi in graph.settlements[:3]:
            flock = self._circuit(poi.x + 40.0, poi.y - 30.0, 55.0, 7)
            for k in range(3):
                self.actors.append(
                    Actor("bird", flock, 9.0, s=k * 25.0, z_off=18.0 + k * 3.0, scale=(0.35, 0.7, 0.12), color=(0.08, 0.08, 0.09))
                )

    def _circuit(self, cx: float, cy: float, r: float, n: int) -> list[tuple[float, float]]:
        pts = []
        for i in range(n):
            ang = i / n * math.tau
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.65))
        pts.append(pts[0])
        return pts

    def _geom(self, kind: str):
        return {
            "vehicle": self._car,
            "aircraft": self._plane,
            "boat": self._boat,
            "bird": self._bird,
            "train": self._train,
            "airport": self._car,
        }.get(kind, self._dot)

    def update(self, dt: float, ego_xy: tuple[float, float], height_fn) -> list[str]:
        events: list[str] = []
        ex, ey = ego_xy
        for a in self.actors:
            dist = math.hypot(a.x - ex, a.y - ey) if (a.x or a.y) else 1e9
            a.lod = _lod(dist)
            if a.lod == "abstract":
                a.s += a.speed * dt * 0.12
                x, y, yaw = _along(a.path, a.s)
                a.x, a.y, a.yaw = x, y, yaw
                if a.node is not None:
                    a.node.removeNode()
                    a.node = None
                continue
            step = dt if a.lod in ("active", "simplified") else dt * 0.35
            a.s += a.speed * step
            x, y, yaw = _along(a.path, a.s)
            z = height_fn(x, y) + a.z_off
            a.x, a.y, a.z, a.yaw = x, y, z, yaw
            if a.lod in ("active", "simplified"):
                if a.node is None:
                    mesh = self._geom(a.kind) if a.lod == "active" else self._dot
                    a.node = self.root.attachNewNode(mesh)
                    sx, sy, sz = a.scale if a.lod == "active" else (2.4, 2.4, 2.4)
                    a.node.setScale(sx, sy, sz)
                a.node.setPos(x, y, z)
                a.node.setH(yaw)
                a.node.show()
            elif a.node is not None:
                a.node.hide()
        return events

    def lod_counts(self) -> dict[str, int]:
        out = {"active": 0, "simplified": 0, "kinematic": 0, "abstract": 0}
        for a in self.actors:
            out[a.lod] = out.get(a.lod, 0) + 1
        return out

    def duplicate_count(self) -> int:
        ids = [a.uid for a in self.actors]
        return len(ids) - len(set(ids))

    def snapshot(self) -> list[dict]:
        out = []
        for a in self.actors:
            if a.lod == "abstract":
                continue
            out.append({"id": a.uid, "kind": a.kind, "x": a.x, "y": a.y, "z": a.z, "lod": a.lod})
        return out
