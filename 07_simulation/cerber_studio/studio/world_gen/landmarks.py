"""Airfield + landmark meshes from WorldGraph."""

from __future__ import annotations

from panda3d.core import NodePath

from .geom import box
from .graph import WorldGraph


def build_airfield(parent: NodePath, graph: WorldGraph) -> None:
    strip_g = box((0.22, 0.22, 0.23))
    edge_g = box((0.85, 0.85, 0.82))
    for af in graph.airfields:
        half_l = float(af.extra.get("length", 320.0)) * 0.5
        half_w = float(af.extra.get("width", 24.0)) * 0.5
        h = af.elev + 0.08
        strip = parent.attachNewNode(strip_g)
        strip.setPos(af.x, af.y, h)
        strip.setH(af.yaw)
        strip.setScale(half_w, half_l, 0.08)
        for side in (-1.0, 1.0):
            e = parent.attachNewNode(edge_g)
            e.setPos(af.x + side * (half_w - 0.4), af.y, h)
            e.setH(af.yaw)
            e.setScale(0.25, half_l, 0.09)


def build_landmarks(parent: NodePath, graph: WorldGraph) -> None:
    for lm in graph.landmarks:
        h = graph.sample_height(lm.x, lm.y)
        if lm.kind == "tower":
            t = parent.attachNewNode(box((0.32, 0.32, 0.30)))
            hh = float(lm.extra.get("h", 28.0))
            t.setPos(lm.x, lm.y, lm.elev + hh)
            t.setScale(0.8, 0.8, hh)
        elif lm.kind == "hangar":
            g = parent.attachNewNode(box((0.36, 0.35, 0.33)))
            sx = float(lm.extra.get("sx", 10.0))
            sy = float(lm.extra.get("sy", 16.0))
            sz = float(lm.extra.get("sz", 5.0))
            g.setPos(lm.x, lm.y, lm.elev + sz)
            g.setScale(sx, sy, sz)
        elif lm.kind == "dam":
            w = parent.attachNewNode(box((0.28, 0.30, 0.32)))
            w.setPos(lm.x, lm.y, h + 14)
            w.setScale(80.0, 8.0, 14.0)
        elif lm.kind == "bridge":
            b = parent.attachNewNode(box((0.22, 0.22, 0.24)))
            b.setPos(lm.x, lm.y, h + 8)
            b.setScale(6.0, 70.0, 2.2)
        elif lm.kind == "city":
            for k in range(8):
                t = parent.attachNewNode(box((0.38, 0.36, 0.34)))
                t.setPos(lm.x + (k % 4) * 18 - 27, lm.y + (k // 4) * 16 - 8, h + 8 + k)
                t.setScale(6.0, 6.0, 8.0 + k * 1.4)
        elif lm.kind == "port":
            p = parent.attachNewNode(box((0.30, 0.32, 0.34)))
            p.setPos(lm.x, lm.y, h + 4)
            p.setScale(22.0, 40.0, 4.0)
        elif lm.kind == "radar":
            r = parent.attachNewNode(box((0.55, 0.55, 0.52)))
            r.setPos(lm.x, lm.y, h + 18)
            r.setScale(1.2, 1.2, 18.0)
        elif lm.kind == "quarry":
            q = parent.attachNewNode(box((0.42, 0.36, 0.28)))
            q.setPos(lm.x, lm.y, h + 3)
            q.setScale(40.0, 28.0, 3.0)
        elif lm.kind == "power_plant":
            a = parent.attachNewNode(box((0.34, 0.32, 0.30)))
            a.setPos(lm.x, lm.y, h + 10)
            a.setScale(18.0, 12.0, 10.0)
            c = parent.attachNewNode(box((0.45, 0.28, 0.18)))
            c.setPos(lm.x + 16, lm.y, h + 16)
            c.setScale(4.0, 4.0, 16.0)
        elif lm.kind == "mountain":
            m = parent.attachNewNode(box((0.36, 0.38, 0.40)))
            m.setPos(lm.x, lm.y, h + 90)
            m.setScale(120.0, 90.0, 90.0)
        elif lm.kind == "offshore":
            o = parent.attachNewNode(box((0.40, 0.42, 0.44)))
            o.setPos(lm.x, lm.y, h + 12)
            o.setScale(14.0, 18.0, 12.0)


def build_powerlines(parent: NodePath, graph: WorldGraph) -> None:
    pole = box((0.18, 0.18, 0.16))
    for line in graph.powerlines:
        for i, (x, y) in enumerate(line):
            if i % 2:
                continue
            h = graph.sample_height(x, y)
            p = parent.attachNewNode(pole)
            p.setPos(x, y, h + 7.0)
            p.setScale(0.18, 0.18, 7.0)
