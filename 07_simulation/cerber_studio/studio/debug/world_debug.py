"""F2 world debug: sector bounds, LOD rings, roads, POI, activity LOD."""

from __future__ import annotations

from panda3d.core import NodePath

from ..world_gen.geom import box, polyline_strips
from ..world_gen.streamer import FAR_M, MID_M, NEAR_M


class WorldDebugOverlay:
    def __init__(self, parent: NodePath) -> None:
        self.root = parent.attachNewNode("world_debug")
        self.root.hide()
        self._on = False

    @property
    def enabled(self) -> bool:
        return self._on

    def set_enabled(self, on: bool) -> None:
        self._on = bool(on)
        if self._on:
            self.root.show()
        else:
            self.root.hide()

    def toggle(self) -> bool:
        self.set_enabled(not self._on)
        return self._on

    def rebuild(self, streamer) -> None:
        self.root.removeNode()
        parent = streamer.root.getParent()
        self.root = parent.attachNewNode("world_debug")
        graph = streamer.graph

        def hfn(x, y):
            return graph.sample_height(x, y) + 1.2

        polyline_strips(self.root, graph.roads[0] if graph.roads else [], width=4.0, height_fn=hfn, color=(0.85, 0.75, 0.20), z_off=0.4)
        for road in graph.roads[1:6]:
            polyline_strips(self.root, road, width=3.0, height_fn=hfn, color=(0.70, 0.62, 0.18), z_off=0.35)
        for poi in graph.settlements + graph.industrial + graph.airfields + graph.landmarks:
            mark = self.root.attachNewNode(box((0.9, 0.2, 0.15)))
            mark.setPos(poi.x, poi.y, poi.elev + 18.0)
            mark.setScale(4.0, 4.0, 18.0)
        self._ring_boxes(streamer.near, (0.2, 0.85, 0.35), 2.0)
        self._ring_boxes(streamer.mid, (0.25, 0.55, 0.9), 6.0)
        self._ring_boxes(streamer.far, (0.7, 0.35, 0.2), 18.0)
        if not self._on:
            self.root.hide()

    def _ring_boxes(self, bag: dict, color: tuple[float, float, float], thick: float) -> None:
        mesh = box(color)
        for sec in bag.values():
            n = self.root.attachNewNode(mesh)
            n.setPos(sec.sx * sec.size + sec.size * 0.5, sec.sy * sec.size + sec.size * 0.5, thick)
            n.setScale(sec.size * 0.5, sec.size * 0.5, thick)
            n.setRenderModeWireframe()
            n.setLightOff(1)

    def sizes(self) -> tuple[float, float, float]:
        return NEAR_M, MID_M, FAR_M
