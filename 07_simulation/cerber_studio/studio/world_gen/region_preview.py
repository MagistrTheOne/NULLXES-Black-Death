"""Lightweight cinematic region preview. Not WorldStreamer / activity / physics."""

from __future__ import annotations

import math

from panda3d.core import NodePath, Vec3

from .biomes import BiomeField
from .geom import box
from .graph import generate_graph
from .terrain import attach_geomip, build_height_color
from .water import attach_water_plane

PREVIEW_SIZE = 768.0
PREVIEW_HF = 33


class RegionPreview:
    def __init__(self, render: NodePath) -> None:
        self.render = render
        self.root = render.attachNewNode("region_preview")
        self.root.hide()
        self.region_id = ""
        self.seed = 0
        self.center = (0.0, 0.0, 12.0)
        self._heading = 18.0

    def show(self) -> None:
        self.root.show()

    def hide(self) -> None:
        self.root.hide()

    def clear(self) -> None:
        self.root.removeNode()
        self.root = self.render.attachNewNode("region_preview")
        self.root.hide()

    def rebuild(self, seed: int, region_id: str, loader=None) -> None:
        self.clear()
        self.seed = int(seed)
        self.region_id = region_id or "forest"
        graph = generate_graph(self.seed, self.region_id)
        biomes = BiomeField(graph)
        sx, sy, gz, _yaw = graph.spawn()
        ox = sx - PREVIEW_SIZE * 0.5
        oy = sy - PREVIEW_SIZE * 0.5
        patch = self.root.attachNewNode("preview_patch")
        patch.setPos(ox, oy, 0)
        img, cmap, step = build_height_color(graph, biomes, ox, oy, PREVIEW_SIZE, PREVIEW_HF, lod="near")
        terrain = attach_geomip(patch, "preview_terrain", img, cmap, step, block=16, near=20.0, far=900.0)
        try:
            terrain.setBruteforce(True)
            terrain.generate()
        except Exception:
            pass
        profile = graph.profile
        if profile.water_enabled:
            attach_water_plane(
                self.root,
                origin=(sx, sy),
                size=PREVIEW_SIZE * 1.35,
                z=profile.water_level,
                color=profile.water_rgb,
            )
        self._scatter_preview(patch, graph, biomes, ox, oy)
        self._horizon_hills(graph, sx, sy, profile)
        self.center = (sx, sy, gz + 8.0)
        self.root.show()

    def camera_pose(self, dt: float) -> tuple[Vec3, Vec3]:
        self._heading = (self._heading + dt * 4.0) % 360.0
        h = math.radians(self._heading)
        cx, cy, cz = self.center
        dist = 280.0
        eye = Vec3(cx + math.sin(h) * dist, cy - math.cos(h) * dist, max(cz + 95.0, 48.0))
        look = Vec3(cx, cy + 18.0, max(6.0, cz - 4.0))
        return eye, look

    def _scatter_preview(self, parent: NodePath, graph, biomes: BiomeField, ox: float, oy: float) -> None:
        rock = box((0.42, 0.40, 0.38))
        tree = box((0.16, 0.24, 0.14))
        step = 90.0
        n = int(PREVIEW_SIZE / step)
        for iy in range(n):
            for ix in range(n):
                wx = ox + (ix + 0.4) * step
                wy = oy + (iy + 0.45) * step
                kind = biomes.kind(wx, wy)
                if kind in ("clear", "town", "industrial", "water"):
                    continue
                h = graph.sample_height(wx, wy)
                if kind == "forest" and (ix + iy) % 3 == 0:
                    node = parent.attachNewNode(tree)
                    node.setPos(wx - ox, wy - oy, h + 1.6)
                    node.setScale(1.4, 1.4, 3.2)
                elif kind in ("rock", "snow") and (ix + iy) % 4 == 0:
                    node = parent.attachNewNode(rock)
                    node.setPos(wx - ox, wy - oy, h + 0.5)
                    node.setScale(1.8, 1.3, 0.8)

    def _horizon_hills(self, graph, cx: float, cy: float, profile) -> None:
        mesh = box(tuple(min(1.0, c * 0.82 + 0.12) for c in profile.lowland_rgb))
        for i in range(24):
            ang = i / 24.0 * math.tau
            r = 900.0 + (i % 5) * 80.0
            x = cx + math.cos(ang) * r
            y = cy + math.sin(ang) * r
            h = graph.sample_height(x, y)
            n = self.root.attachNewNode(mesh)
            n.setPos(x, y, h * 0.45)
            n.setScale(70 + (i % 4) * 18, 55, 18 + (h * 0.12) + (i % 3) * 8)
