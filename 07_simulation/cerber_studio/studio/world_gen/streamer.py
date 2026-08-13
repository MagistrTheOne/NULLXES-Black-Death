"""LOD streamer: NEAR/MID/FAR/HORIZON. Physics height from graph (NEAR+MID tiles)."""

from __future__ import annotations

import math

from panda3d.core import NodePath

from ..config.paths import STUDIO_ROOT
from .biomes import BiomeField
from .geom import box, cone
from .graph import WorldGraph, generate_graph
from .landmarks import build_airfield, build_landmarks, build_powerlines
from .roads import build_road_lines
from .scatter import scatter_sector
from .settlements import build_industrial, build_settlements
from .terrain import attach_geomip, build_height_color
from .water import build_rivers
from .lights import NightLights
from .weather import AtmosphereState

NEAR_M = 1536.0
MID_M = 4096.0
FAR_M = 16384.0
NEAR_HF = 65
MID_HF = 33
FAR_HF = 17
NEAR_R = 1
MID_R = 2
FAR_R = 2
PHYS_RADIUS = 8000.0


class Sector:
    def __init__(
        self,
        sx: int,
        sy: int,
        size: float,
        hf: int,
        parent: NodePath,
        graph: WorldGraph,
        biomes: BiomeField,
        packs: dict,
        density: str,
        lod: str,
    ) -> None:
        self.sx = sx
        self.sy = sy
        self.size = size
        self.root = parent.attachNewNode(f"{lod}_{sx}_{sy}")
        ox = sx * size
        oy = sy * size
        self.root.setPos(ox, oy, 0)
        img, cmap, step = build_height_color(graph, biomes, ox, oy, size, hf)
        block = 16 if lod == "near" else 8 if lod == "mid" else 4
        self.terrain = attach_geomip(
            self.root,
            f"t_{lod}_{sx}_{sy}",
            img,
            cmap,
            step,
            block=block,
            near=90.0 if lod == "near" else 400.0,
            far=320.0 if lod == "near" else 1800.0,
        )
        self._fp = self.root.attachNewNode("focal")
        self.props = self.root.attachNewNode("props")
        if density != "none":
            scatter_sector(self.props, graph, biomes, ox, oy, size, sx, sy, packs, density)

    def update_focal(self, x: float, y: float, z: float) -> None:
        self._fp.setPos(x - self.sx * self.size, y - self.sy * self.size, z)
        self.terrain.setFocalPoint(self._fp)
        self.terrain.update()

    def destroy(self) -> None:
        self.root.removeNode()


class WorldStreamer:
    def __init__(self, render: NodePath, seed: int = 1947, region_id: str = "forest") -> None:
        self.render = render
        self.root = render.attachNewNode("world_stream")
        self.packs: dict[str, NodePath | None] = {"tree": None, "rock": None, "building": None}
        self.atmosphere = AtmosphereState()
        self.near: dict[tuple[int, int], Sector] = {}
        self.mid: dict[tuple[int, int], Sector] = {}
        self.far: dict[tuple[int, int], Sector] = {}
        self._infra = self.root.attachNewNode("graph_vis")
        self._horizon = self.root.attachNewNode("horizon")
        self.night: NightLights | None = None
        self.active = False
        self.configure(seed, region_id)

    def configure(self, seed: int, region_id: str) -> None:
        self.seed = int(seed)
        self.region_id = region_id or "forest"
        self.graph = generate_graph(self.seed, self.region_id)
        self.biomes = BiomeField(self.graph)
        self._clear_tiles()
        self._rebuild_graph_vis()
        self._rebuild_horizon()

    def load_packs(self, loader) -> None:
        from .env_packs import scan_packs

        root = STUDIO_ROOT / "assets" / "world"
        mapping = (("tree", "vegetation"), ("rock", "rocks"), ("building", "buildings"))
        for key, sub in mapping:
            folder = root / sub
            if not folder.is_dir():
                continue
            files = sorted(folder.glob("*.glb")) + sorted(folder.glob("*.gltf"))
            if not files:
                continue
            try:
                node = loader.loadModel(str(files[0]))
                node.setLightOff(0)
                self.packs[key] = node
            except Exception:
                self.packs[key] = None
        for pack in scan_packs():
            for prop in pack.props:
                path = pack.resolve(prop)
                if path is None:
                    continue
                cat = pack.category
                slot = "tree" if cat == "vegetation" else "building" if cat in ("civilian", "industrial", "airfield") else "rock"
                if self.packs.get(slot) is not None:
                    continue
                try:
                    node = loader.loadModel(str(path))
                    node.setLightOff(0)
                    self.packs[slot] = node
                except Exception:
                    continue

    def _clear_tiles(self) -> None:
        for bag in (self.near, self.mid, self.far):
            for sec in list(bag.values()):
                sec.destroy()
            bag.clear()

    def _rebuild_graph_vis(self) -> None:
        self._infra.removeNode()
        self._infra = self.root.attachNewNode("graph_vis")
        build_airfield(self._infra, self.graph)
        build_landmarks(self._infra, self.graph)
        build_powerlines(self._infra, self.graph)
        build_road_lines(self._infra, self.graph, "near")
        build_rivers(self._infra, self.graph, "near")
        build_settlements(self._infra, self.graph, self.packs)
        build_industrial(self._infra, self.graph)
        if self.night is not None:
            self.night.root.removeNode()
        self.night = NightLights(self.root, self.graph)

    def _rebuild_horizon(self) -> None:
        self._horizon.removeNode()
        self._horizon = self.root.attachNewNode("horizon")
        mesh = cone((0.34, 0.36, 0.38))
        rock = box((0.32, 0.33, 0.34))
        for i in range(16):
            ang = i / 16.0 * math.tau
            r = 42000.0 + (i % 3) * 4000.0
            x = math.cos(ang) * r
            y = math.sin(ang) * r
            h = self.graph.sample_height(x * 0.4, y * 0.4)
            n = self._horizon.attachNewNode(mesh)
            n.setPos(x, y, h + 80.0)
            n.setScale(2800 + (i % 4) * 400, 2800, 420 + (i % 5) * 80)
            b = self._horizon.attachNewNode(rock)
            b.setPos(math.cos(ang + 0.2) * (r - 6000), math.sin(ang + 0.2) * (r - 6000), h + 40)
            b.setScale(1800, 1400, 220)

    def set_active(self, on: bool) -> None:
        self.active = on
        if on:
            self.root.show()
            sx, sy, _, _ = self.spawn()
            self.ensure(sx, sy)
        else:
            self.root.hide()

    def ensure(self, x: float, y: float) -> None:
        self._sync_ring(self.near, x, y, NEAR_M, NEAR_R, NEAR_HF, "full", "near")
        self._sync_ring(self.mid, x, y, MID_M, MID_R, MID_HF, "sparse", "mid", skip_inner=1)
        self._sync_ring(self.far, x, y, FAR_M, FAR_R, FAR_HF, "none", "far", skip_inner=1)

    def _sync_ring(
        self,
        bag: dict[tuple[int, int], Sector],
        x: float,
        y: float,
        size: float,
        ring: int,
        hf: int,
        density: str,
        lod: str,
        skip_inner: int = 0,
    ) -> None:
        cx = int(math.floor(x / size))
        cy = int(math.floor(y / size))
        needed: set[tuple[int, int]] = set()
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if skip_inner and abs(dx) <= skip_inner and abs(dy) <= skip_inner:
                    continue
                needed.add((cx + dx, cy + dy))
        for key in list(bag):
            if key not in needed:
                bag.pop(key).destroy()
        for key in needed:
            if key not in bag:
                bag[key] = Sector(
                    key[0],
                    key[1],
                    size,
                    hf,
                    self.root,
                    self.graph,
                    self.biomes,
                    self.packs,
                    density,
                    lod,
                )

    def update(self, x: float, y: float, z: float) -> None:
        if not self.active:
            return
        self.ensure(x, y)
        for sec in self.near.values():
            sec.update_focal(x, y, z)
        if self.night is not None:
            self.night.apply(self.atmosphere)

    def ground_z(self, x: float, y: float) -> float:
        dx = x - (self.graph.airfields[0].x if self.graph.airfields else 0.0)
        dy = y - (self.graph.airfields[0].y if self.graph.airfields else 0.0)
        dist = math.hypot(dx, dy)
        if dist > PHYS_RADIUS:
            return self.graph.sample_height(x, y)
        return self.graph.sample_height(x, y)

    def spawn(self) -> tuple[float, float, float, float]:
        return self.graph.spawn()
