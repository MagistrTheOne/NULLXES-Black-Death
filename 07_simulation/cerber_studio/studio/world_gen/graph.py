"""WorldGraph: valley → river → road → settlement → industrial → airfield, then cache."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from panda3d.core import PerlinNoise2

from ..config.paths import user_dir
from .world_profile import WorldProfile, load_profile

CACHE_VER = 5
EXTENT_M = 80000.0
GRID_N = 81
CELL_M = EXTENT_M / (GRID_N - 1)
HALF = EXTENT_M * 0.5


def sector_seed(world_seed: int, region_id: str, sx: int, sy: int) -> int:
    raw = f"{world_seed}|{region_id}|{sx}|{sy}".encode("utf-8")
    return int(hashlib.blake2s(raw, digest_size=8).hexdigest(), 16) & 0x7FFFFFFF


def cache_dir(world_seed: int, region_id: str) -> Path:
    path = user_dir() / "world_cache" / f"{world_seed}_{region_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Poi:
    kind: str
    x: float
    y: float
    yaw: float = 0.0
    elev: float = 4.0
    extra: dict = field(default_factory=dict)


@dataclass
class WorldGraph:
    seed: int
    region_id: str
    profile: WorldProfile
    height: list[list[float]]
    rivers: list[list[tuple[float, float]]]
    roads: list[list[tuple[float, float]]]
    powerlines: list[list[tuple[float, float]]]
    settlements: list[Poi]
    industrial: list[Poi]
    airfields: list[Poi]
    landmarks: list[Poi]

    def xy_of(self, i: int, j: int) -> tuple[float, float]:
        return -HALF + i * CELL_M, -HALF + j * CELL_M

    def ij_of(self, x: float, y: float) -> tuple[int, int]:
        i = int(round((x + HALF) / CELL_M))
        j = int(round((y + HALF) / CELL_M))
        return max(0, min(GRID_N - 1, i)), max(0, min(GRID_N - 1, j))

    def cell_h(self, i: int, j: int) -> float:
        return self.height[j][i]

    def sample_height(self, x: float, y: float) -> float:
        gx = (x + HALF) / CELL_M
        gy = (y + HALF) / CELL_M
        i0 = int(math.floor(gx))
        j0 = int(math.floor(gy))
        i1 = min(GRID_N - 1, i0 + 1)
        j1 = min(GRID_N - 1, j0 + 1)
        i0 = max(0, min(GRID_N - 1, i0))
        j0 = max(0, min(GRID_N - 1, j0))
        tx = gx - i0
        ty = gy - j0
        h00 = self.height[j0][i0]
        h10 = self.height[j0][i1]
        h01 = self.height[j1][i0]
        h11 = self.height[j1][i1]
        return (h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty

    def slope(self, x: float, y: float) -> float:
        d = 24.0
        return abs(self.sample_height(x + d, y) - self.sample_height(x - d, y)) + abs(
            self.sample_height(x, y + d) - self.sample_height(x, y - d)
        )

    def near_polyline(self, x: float, y: float, lines: list[list[tuple[float, float]]], rad: float) -> bool:
        r2 = rad * rad
        for line in lines:
            for px, py in line:
                dx, dy = px - x, py - y
                if dx * dx + dy * dy <= r2:
                    return True
        return False

    def river_mask(self, x: float, y: float, rad: float = 38.0) -> bool:
        return self.near_polyline(x, y, self.rivers, rad)

    def road_mask(self, x: float, y: float, rad: float = 14.0) -> bool:
        return self.near_polyline(x, y, self.roads, rad)

    def airfield_mask(self, x: float, y: float) -> bool:
        for af in self.airfields:
            half_l = float(af.extra.get("length", 320.0)) * 0.5
            half_w = float(af.extra.get("width", 24.0)) * 0.5 + 8.0
            yaw = math.radians(af.yaw)
            dx, dy = x - af.x, y - af.y
            lx = dx * math.cos(-yaw) - dy * math.sin(-yaw)
            ly = dx * math.sin(-yaw) + dy * math.cos(-yaw)
            if abs(lx) <= half_w and abs(ly) <= half_l + 12.0:
                return True
        return False

    def settlement_mask(self, x: float, y: float, rad: float = 90.0) -> bool:
        r2 = rad * rad
        for p in self.settlements:
            if (p.x - x) ** 2 + (p.y - y) ** 2 <= r2:
                return True
        return False

    def industrial_mask(self, x: float, y: float, rad: float = 70.0) -> bool:
        r2 = rad * rad
        for p in self.industrial:
            if (p.x - x) ** 2 + (p.y - y) ** 2 <= r2:
                return True
        return False

    def spawn(self) -> tuple[float, float, float, float]:
        if self.airfields:
            af = self.airfields[0]
            yaw = af.yaw
            fx = af.x + math.sin(math.radians(yaw)) * 12.0
            fy = af.y + math.cos(math.radians(yaw)) * 12.0
            return fx, fy, af.elev, yaw
        return 0.0, 12.0, self.sample_height(0.0, 12.0), 0.0

    def to_json(self) -> dict:
        def line(pts):
            return [[float(a), float(b)] for a, b in pts]

        def poi(p: Poi) -> dict:
            return {"kind": p.kind, "x": p.x, "y": p.y, "yaw": p.yaw, "elev": p.elev, "extra": p.extra}

        return {
            "ver": CACHE_VER,
            "seed": self.seed,
            "region_id": self.region_id,
            "height": self.height,
            "rivers": [line(r) for r in self.rivers],
            "roads": [line(r) for r in self.roads],
            "powerlines": [line(r) for r in self.powerlines],
            "settlements": [poi(p) for p in self.settlements],
            "industrial": [poi(p) for p in self.industrial],
            "airfields": [poi(p) for p in self.airfields],
            "landmarks": [poi(p) for p in self.landmarks],
        }

    @classmethod
    def from_json(cls, data: dict, profile: WorldProfile) -> WorldGraph:
        def line(raw):
            return [(float(p[0]), float(p[1])) for p in raw]

        def poi(raw) -> Poi:
            return Poi(
                kind=str(raw.get("kind", "poi")),
                x=float(raw["x"]),
                y=float(raw["y"]),
                yaw=float(raw.get("yaw", 0.0)),
                elev=float(raw.get("elev", 4.0)),
                extra=dict(raw.get("extra") or {}),
            )

        return cls(
            seed=int(data["seed"]),
            region_id=str(data["region_id"]),
            profile=profile,
            height=data["height"],
            rivers=[line(r) for r in data.get("rivers") or []],
            roads=[line(r) for r in data.get("roads") or []],
            powerlines=[line(r) for r in data.get("powerlines") or []],
            settlements=[poi(p) for p in data.get("settlements") or []],
            industrial=[poi(p) for p in data.get("industrial") or []],
            airfields=[poi(p) for p in data.get("airfields") or []],
            landmarks=[poi(p) for p in data.get("landmarks") or []],
        )


class _Noise:
    def __init__(self, seed: int, profile: WorldProfile) -> None:
        s = seed + profile.seed_salt
        self.c = PerlinNoise2(s * 0.001 + 0.11, s * 0.002 + 0.17)
        self.c.setScale(profile.continent_scale)
        self.m = PerlinNoise2(s * 0.003 + 1.4, s * 0.001 + 2.8)
        self.m.setScale(profile.mountain_scale)
        self.r = PerlinNoise2(s * 0.007 + 3.1, s * 0.004 + 0.6)
        self.r.setScale(profile.ridge_scale)
        self.v = PerlinNoise2(s * 0.01 + 8.0, s * 0.009 + 4.2)
        self.v.setScale(90)

    def raw(self, x: float, y: float, profile: WorldProfile) -> float:
        h = profile.base_height
        h += profile.mountain_gain * (self.c.noise(x, y) * 0.5 + 0.5) ** 1.35
        h += profile.hill_gain * self.m.noise(x, y)
        h += profile.ridge_gain * self.r.noise(x, y)
        return h


def _blur(height: list[list[float]]) -> list[list[float]]:
    n = GRID_N
    out = [[0.0] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            s = 0.0
            c = 0
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < n:
                        s += height[nj][ni]
                        c += 1
            out[j][i] = s / max(1, c)
    return out


def _flow_rivers(height: list[list[float]], threshold: float) -> list[list[tuple[float, float]]]:
    n = GRID_N
    flow_h = _blur(_blur(height))
    down = [[(i, j) for i in range(n)] for j in range(n)]
    acc = [[0 for _ in range(n)] for _ in range(n)]
    neigh = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1))
    for j in range(n):
        for i in range(n):
            best = flow_h[j][i]
            bi, bj = i, j
            for di, dj in neigh:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n and flow_h[nj][ni] < best:
                    best = flow_h[nj][ni]
                    bi, bj = ni, nj
            down[j][i] = (bi, bj)
    order = sorted(((flow_h[j][i], i, j) for j in range(n) for i in range(n)), reverse=True)
    for _, i, j in order:
        acc[j][i] += 1
        ni, nj = down[j][i]
        if (ni, nj) != (i, j):
            acc[nj][ni] += acc[j][i]
    rivers: list[list[tuple[float, float]]] = []
    seen: set[tuple[int, int]] = set()
    floor = max(6, int(max(8.0, float(threshold))))
    channel = [[acc[j][i] >= floor for i in range(n)] for j in range(n)]
    heads: list[tuple[int, int, int]] = []
    for j in range(n):
        for i in range(n):
            if not channel[j][i]:
                continue
            fed = False
            for di, dj in neigh:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n and channel[nj][ni] and down[nj][ni] == (i, j):
                    fed = True
                    break
            if not fed:
                heads.append((acc[j][i], i, j))
    heads.sort(reverse=True)
    for _, si, sj in heads[:16]:
        if (si, sj) in seen:
            continue
        path: list[tuple[float, float]] = []
        i, j = si, sj
        for _ in range(n * 2):
            x = -HALF + i * CELL_M
            y = -HALF + j * CELL_M
            path.append((x, y))
            seen.add((i, j))
            ni, nj = down[j][i]
            if (ni, nj) == (i, j):
                break
            i, j = ni, nj
        if len(path) >= 5:
            rivers.append(path)
        if len(rivers) >= 8:
            break
    return rivers


def _astar(height: list[list[float]], a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    import heapq

    n = GRID_N
    sx, sy = a
    gx, gy = b
    open_h: list[tuple[float, int, int]] = [(0.0, sx, sy)]
    came: dict[tuple[int, int], tuple[int, int] | None] = {(sx, sy): None}
    gscore = {(sx, sy): 0.0}
    while open_h:
        _, i, j = heapq.heappop(open_h)
        if (i, j) == (gx, gy):
            break
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ni, nj = i + di, j + dj
            if not (0 <= ni < n and 0 <= nj < n):
                continue
            climb = abs(height[nj][ni] - height[j][i])
            ng = gscore[(i, j)] + 1.0 + climb * 0.18
            if ng < gscore.get((ni, nj), 1e18):
                gscore[(ni, nj)] = ng
                came[(ni, nj)] = (i, j)
                heur = abs(ni - gx) + abs(nj - gy)
                heapq.heappush(open_h, (ng + heur, ni, nj))
    if (gx, gy) not in came:
        return [a, b]
    path = [(gx, gy)]
    cur: tuple[int, int] | None = (gx, gy)
    while cur is not None:
        cur = came[cur]
        if cur is not None:
            path.append(cur)
    path.reverse()
    return path


def _pts_from_cells(cells: list[tuple[int, int]]) -> list[tuple[float, float]]:
    return [(-HALF + i * CELL_M, -HALF + j * CELL_M) for i, j in cells]


def generate_graph(seed: int, region_id: str) -> WorldGraph:
    profile = load_profile(region_id)
    cache = cache_dir(seed, profile.id) / "graph.json"
    if cache.is_file():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if int(data.get("seed", -1)) == seed and data.get("region_id") == profile.id and int(data.get("ver", 0)) == CACHE_VER:
                return WorldGraph.from_json(data, profile)
        except Exception:
            pass
    noise = _Noise(seed, profile)
    height = [[0.0] * GRID_N for _ in range(GRID_N)]
    for j in range(GRID_N):
        for i in range(GRID_N):
            x = -HALF + i * CELL_M
            y = -HALF + j * CELL_M
            height[j][i] = max(1.5, noise.raw(x, y, profile))
    rivers = _flow_rivers(height, profile.river_threshold * profile.river_count_bias)
    for river in rivers:
        for x, y in river:
            i = int(round((x + HALF) / CELL_M))
            j = int(round((y + HALF) / CELL_M))
            if 0 <= i < GRID_N and 0 <= j < GRID_N:
                height[j][i] = min(height[j][i], 6.5)
                for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < GRID_N and 0 <= nj < GRID_N:
                        height[nj][ni] = min(height[nj][ni], height[j][i] + 3.5)

    ci, cj = GRID_N // 2, GRID_N // 2
    best = 1e9
    ai, aj = ci, cj
    if rivers:
        mid = rivers[0][len(rivers[0]) // 2]
        ri = int(round((mid[0] + HALF) / CELL_M))
        rj = int(round((mid[1] + HALF) / CELL_M))
        ai = max(3, min(GRID_N - 4, ri + 2))
        aj = max(3, min(GRID_N - 4, rj))
    else:
        for j in range(cj - 8, cj + 9):
            for i in range(ci - 8, ci + 9):
                if not (2 <= i < GRID_N - 2 and 2 <= j < GRID_N - 2):
                    continue
                sl = abs(height[j][i + 1] - height[j][i - 1]) + abs(height[j + 1][i] - height[j - 1][i])
                score = sl + abs(height[j][i] - 8.0) * 0.08
                if score < best:
                    best = score
                    ai, aj = i, j
    elev = 4.2
    for dj in range(-1, 2):
        for di in range(-2, 3):
            ni, nj = ai + di, aj + dj
            if 0 <= ni < GRID_N and 0 <= nj < GRID_N:
                height[nj][ni] = elev
    ax, ay = -HALF + ai * CELL_M, -HALF + aj * CELL_M
    airfield = Poi(
        kind="airfield",
        x=ax,
        y=ay,
        yaw=0.0,
        elev=elev,
        extra={"length": 320.0, "width": 24.0},
    )

    settle_cells: list[tuple[int, int]] = []
    used: set[tuple[int, int]] = {(ai, aj)}
    for river in rivers:
        if len(settle_cells) >= profile.settlement_count:
            break
        mid = river[len(river) // 2]
        i = int(round((mid[0] + HALF) / CELL_M))
        j = int(round((mid[1] + HALF) / CELL_M))
        if (i, j) in used or abs(i - ai) + abs(j - aj) < 2:
            continue
        used.add((i, j))
        settle_cells.append((i, j))
    while len(settle_cells) < profile.settlement_count:
        k = len(settle_cells) + 3
        i = max(4, min(GRID_N - 5, ai + ((k * 11) % 18) - 9))
        j = max(4, min(GRID_N - 5, aj + ((k * 17) % 16) - 8))
        if (i, j) not in used:
            used.add((i, j))
            settle_cells.append((i, j))

    settlements = []
    for i, j in settle_cells:
        x, y = -HALF + i * CELL_M, -HALF + j * CELL_M
        settlements.append(Poi(kind="settlement", x=x, y=y, elev=height[j][i], extra={"buildings": 7}))

    ix, iy = settle_cells[0][0] + 3, settle_cells[0][1] - 2
    ix = max(2, min(GRID_N - 3, ix))
    iy = max(2, min(GRID_N - 3, iy))
    industrial = [
        Poi(
            kind="industrial",
            x=-HALF + ix * CELL_M,
            y=-HALF + iy * CELL_M,
            elev=height[iy][ix],
            extra={"halls": 3},
        )
    ]

    roads: list[list[tuple[float, float]]] = []
    for cell in settle_cells:
        roads.append(_pts_from_cells(_astar(height, (ai, aj), cell)))
    roads.append(_pts_from_cells(_astar(height, settle_cells[0], (ix, iy))))
    powerlines = [_pts_from_cells(_astar(height, settle_cells[0], (ix, iy)))]
    landmarks = [
        Poi(kind="tower", x=ax - 48.0, y=ay + 28.0, elev=elev, extra={"h": 28.0, "discover": False}),
        Poi(kind="hangar", x=ax - 42.0, y=ay - 18.0, elev=elev, extra={"sx": 10.0, "sy": 16.0, "sz": 5.0, "discover": False}),
        Poi(kind="airfield", x=ax, y=ay, elev=elev, extra={"title": "AIRFIELD-01", "discover": True}),
    ]
    specs = (
        ("dam", 8, -6, "NORTHERN DAM"),
        ("bridge", -5, 7, "VALLEY BRIDGE"),
        ("city", 10, 4, "CITY"),
        ("port", -9, -3, "COASTAL PORT"),
        ("radar", 6, 11, "RADAR STATION"),
        ("quarry", -11, 8, "QUARRY"),
        ("power_plant", 4, -10, "POWER PLANT"),
        ("mountain", 12, -8, "MOUNTAIN PASS"),
        ("offshore", -14, -6, "OFFSHORE PLATFORM"),
    )
    for kind, di, dj, title in specs:
        li = max(3, min(GRID_N - 4, ai + di))
        lj = max(3, min(GRID_N - 4, aj + dj))
        lx, ly = -HALF + li * CELL_M, -HALF + lj * CELL_M
        landmarks.append(
            Poi(kind=kind, x=lx, y=ly, elev=height[lj][li], extra={"title": title, "discover": True})
        )
    graph = WorldGraph(
        seed=seed,
        region_id=profile.id,
        profile=profile,
        height=height,
        rivers=rivers,
        roads=roads,
        powerlines=powerlines,
        settlements=settlements,
        industrial=industrial,
        airfields=[airfield],
        landmarks=landmarks,
    )
    cache.write_text(json.dumps(graph.to_json()), encoding="utf-8")
    return graph
