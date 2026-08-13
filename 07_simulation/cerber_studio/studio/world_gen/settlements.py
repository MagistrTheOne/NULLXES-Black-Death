"""Settlements and industrial halls from WorldGraph POI."""

from __future__ import annotations

from panda3d.core import NodePath

from .geom import box
from .graph import WorldGraph, sector_seed


def build_settlements(parent: NodePath, graph: WorldGraph, packs: dict) -> None:
    house = packs.get("building")
    geom = box((0.42, 0.41, 0.38))
    for poi in graph.settlements:
        n = int(poi.extra.get("buildings", 6))
        rng = sector_seed(graph.seed, graph.region_id, int(poi.x), int(poi.y))
        for k in range(n):
            ox = ((k * 37 + rng) % 70) - 35.0
            oy = ((k * 53 + rng // 3) % 70) - 35.0
            h = graph.sample_height(poi.x + ox, poi.y + oy)
            if house is not None:
                node = house.copyTo(parent)
                node.setPos(poi.x + ox, poi.y + oy, h)
                node.setScale(2.4 + (k % 3) * 0.4)
            else:
                b = parent.attachNewNode(geom)
                b.setPos(poi.x + ox, poi.y + oy, h + 2.1)
                b.setScale(3.2 + (k % 2), 2.4, 2.0 + (k % 3) * 0.4)


def build_industrial(parent: NodePath, graph: WorldGraph) -> None:
    hall = box((0.36, 0.34, 0.30))
    tank = box((0.45, 0.28, 0.18))
    for poi in graph.industrial:
        h = poi.elev
        a = parent.attachNewNode(hall)
        a.setPos(poi.x, poi.y, h + 4.0)
        a.setScale(14.0, 8.0, 4.0)
        b = parent.attachNewNode(hall)
        b.setPos(poi.x + 22.0, poi.y - 6.0, h + 3.2)
        b.setScale(10.0, 6.0, 3.2)
        t = parent.attachNewNode(tank)
        t.setPos(poi.x - 16.0, poi.y + 8.0, h + 5.0)
        t.setScale(3.0, 3.0, 5.0)
