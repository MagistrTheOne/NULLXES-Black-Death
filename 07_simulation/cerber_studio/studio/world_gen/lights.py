"""Night emissives: runway, settlements, aircraft nav. No RenderPipeline."""

from __future__ import annotations

from panda3d.core import NodePath, Vec4

from .geom import box
from .graph import WorldGraph
from .weather import AtmosphereState


class NightLights:
    def __init__(self, parent: NodePath, graph: WorldGraph) -> None:
        self.root = parent.attachNewNode("night_lights")
        self.root.setLightOff(1)
        self._build(graph)

    def rebuild(self, graph: WorldGraph) -> None:
        parent = self.root.getParent()
        self.root.removeNode()
        self.root = parent.attachNewNode("night_lights")
        self.root.setLightOff(1)
        self._build(graph)

    def _build(self, graph: WorldGraph) -> None:
        lamp = box((1.0, 0.92, 0.55))
        blue = box((0.35, 0.55, 1.0))
        amber = box((1.0, 0.55, 0.12))
        window = box((1.0, 0.82, 0.45))
        for af in graph.airfields:
            half_l = float(af.extra.get("length", 320.0)) * 0.5
            half_w = float(af.extra.get("width", 24.0)) * 0.5
            n = 18
            for i in range(n):
                t = i / max(1, n - 1)
                y = af.y + (t - 0.5) * half_l * 2.0
                for side in (-1.0, 1.0):
                    npath = self.root.attachNewNode(lamp)
                    npath.setPos(af.x + side * (half_w + 0.6), y, af.elev + 0.35)
                    npath.setScale(0.12, 0.12, 0.18)
                    npath.setColorScale(Vec4(1.4, 1.2, 0.6, 1))
            thr = self.root.attachNewNode(blue)
            thr.setPos(af.x, af.y + half_l, af.elev + 0.4)
            thr.setScale(0.35, 0.35, 0.25)
        for poi in graph.settlements:
            for k in range(int(poi.extra.get("buildings", 6))):
                ox = ((k * 37) % 70) - 35.0
                oy = ((k * 53) % 70) - 35.0
                w = self.root.attachNewNode(window)
                w.setPos(poi.x + ox, poi.y + oy, poi.elev + 3.4)
                w.setScale(1.1, 0.12, 0.7)
                w.setColorScale(Vec4(1.6, 1.2, 0.5, 1))
        for poi in graph.industrial:
            stack = self.root.attachNewNode(amber)
            stack.setPos(poi.x, poi.y, poi.elev + 9.0)
            stack.setScale(0.4, 0.4, 0.4)
            stack.setColorScale(Vec4(2.0, 0.7, 0.15, 1))

    def apply(self, atmos: AtmosphereState) -> None:
        on = atmos.lights_on
        if on:
            self.root.show()
            self.root.setColorScale(Vec4(1, 1, 1, 0.35 + 0.65 * atmos.night_factor))
        else:
            self.root.hide()
