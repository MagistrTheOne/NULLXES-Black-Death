"""LOD streamer: NEAR/MID/FAR/HORIZON. Physics height from graph (NEAR+MID tiles)."""

from __future__ import annotations

import math
import time

from panda3d.core import NodePath

from ..config.paths import STUDIO_ROOT
from .biomes import BiomeField
from .geom import box
from .graph import WorldGraph, generate_graph
from .landmarks import build_airfield, build_landmarks, build_powerlines
from .roads import build_road_lines
from .scatter import scatter_sector
from .settlements import build_industrial, build_settlements
from .terrain import attach_geomip, build_height_color
from .water import attach_water_plane, build_rivers
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
        *,
        scatter_now: bool = False,
    ) -> None:
        self.sx = sx
        self.sy = sy
        self.size = size
        self.lod = lod
        self.graph = graph
        self.biomes = biomes
        self.packs = packs
        self.root = parent.attachNewNode(f"{lod}_{sx}_{sy}")
        ox = sx * size
        oy = sy * size
        self.origin = (ox, oy)
        self.root.setPos(ox, oy, 0)
        img, cmap, step = build_height_color(graph, biomes, ox, oy, size, hf, lod=lod)
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
        self._pending_density = None if density == "none" else density
        if scatter_now:
            self.commit_props()

    def commit_props(self) -> bool:
        if not self._pending_density:
            return False
        ox, oy = self.origin
        scatter_sector(
            self.props,
            self.graph,
            self.biomes,
            ox,
            oy,
            self.size,
            self.sx,
            self.sy,
            self.packs,
            self._pending_density,
        )
        try:
            self.props.flattenStrong()
        except Exception:
            pass
        self._pending_density = None
        return True

    def update_focal(self, x: float, y: float, z: float) -> None:
        self._fp.setPos(x - self.sx * self.size, y - self.sy * self.size, z)
        self.terrain.setFocalPoint(self._fp)
        self.terrain.update()

    def destroy(self) -> None:
        try:
            self.props.removeNode()
        except Exception:
            pass
        try:
            self.terrain = None
        except Exception:
            pass
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
        self._water: NodePath | None = None
        self._commit_q: list[Sector] = []
        self._last_cx = None
        self._last_cy = None
        self.active = False
        self.gen_ms = 0.0
        self.configure(seed, region_id)

    def configure(self, seed: int, region_id: str) -> None:
        self.seed = int(seed)
        self.region_id = region_id or "forest"
        t0 = time.perf_counter()
        self.graph = generate_graph(self.seed, self.region_id)
        self.gen_ms = (time.perf_counter() - t0) * 1000.0
        self.biomes = BiomeField(self.graph)
        self._clear_tiles()
        self._commit_q.clear()
        self._last_cx = None
        self._last_cy = None
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
        if self._water is not None:
            try:
                self._water.removeNode()
            except Exception:
                pass
            self._water = None
        if self.graph.profile.water_enabled:
            sx, sy, _, _ = self.graph.spawn()
            self._water = attach_water_plane(
                self.root,
                origin=(sx, sy),
                size=28000.0,
                z=self.graph.profile.water_level,
                color=self.graph.profile.water_rgb,
            )
        if self.night is not None:
            self.night.root.removeNode()
        self.night = NightLights(self.root, self.graph)

    def _rebuild_horizon(self) -> None:
        self._horizon.removeNode()
        self._horizon = self.root.attachNewNode("horizon")
        pal = self.graph.profile.haze_rgb or self.graph.profile.lowland_rgb
        col = (pal[0] * 0.55 + 0.18, pal[1] * 0.55 + 0.18, pal[2] * 0.55 + 0.22)
        mesh = box(col)
        segs = 36
        radius = 12500.0
        for i in range(segs):
            ang = i / segs * math.tau
            x = math.cos(ang) * radius
            y = math.sin(ang) * radius
            h = self.graph.sample_height(x, y)
            n = self._horizon.attachNewNode(mesh)
            n.setPos(x, y, max(6.0, h * 0.42))
            n.setH(math.degrees(ang) + 90.0)
            n.setScale(1100.0, 380.0, 22.0 + max(8.0, h * 0.16) + (i % 4) * 6.0)
            n.setLightOff(0)

    def set_active(self, on: bool) -> None:
        self.active = on
        if on:
            self.root.show()
            sx, sy, _, _ = self.spawn()
            self.ensure(sx, sy)
        else:
            self.root.hide()

    def _veg_density(self, lod_density: str) -> str:
        veg = (self.graph.profile.veg_density or "full").lower()
        if veg in ("none", "off"):
            return "none"
        if veg == "low":
            return "sparse" if lod_density == "full" else "none"
        if veg == "sparse":
            return "sparse" if lod_density == "full" else "none"
        return lod_density

    def ensure(self, x: float, y: float) -> None:
        self._sync_ring(self.near, x, y, NEAR_M, NEAR_R, NEAR_HF, self._veg_density("full"), "near")
        self._sync_ring(self.mid, x, y, MID_M, MID_R, MID_HF, self._veg_density("sparse"), "mid", skip_inner=1)
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
        cx = int(math.floor(x / size))
        cy = int(math.floor(y / size))
        for key in needed:
            if key not in bag:
                scatter_now = lod == "near" and key == (cx, cy)
                sec = Sector(
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
                    scatter_now=scatter_now,
                )
                bag[key] = sec
                if not scatter_now and density != "none":
                    self._commit_q.append(sec)

    def update(self, x: float, y: float, z: float) -> None:
        if not self.active:
            return
        cx = int(math.floor(x / NEAR_M))
        cy = int(math.floor(y / NEAR_M))
        if self._last_cx != cx or self._last_cy != cy:
            self.ensure(x, y)
            self._last_cx = cx
            self._last_cy = cy
        if self._commit_q:
            self._commit_q.pop(0).commit_props()
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

    def stats(self) -> dict:
        props = 0
        for bag in (self.near, self.mid, self.far):
            for sec in bag.values():
                props += max(0, sec.props.getNumChildren())
        return {
            "sectors": len(self.near) + len(self.mid) + len(self.far),
            "near": len(self.near),
            "mid": len(self.mid),
            "far": len(self.far),
            "props": props,
            "gen_ms": self.gen_ms,
        }

    def spawn(self) -> tuple[float, float, float, float]:
        return self.graph.spawn()
