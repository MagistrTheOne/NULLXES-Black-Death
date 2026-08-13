"""Sector edge heights must match in WORLD coordinates."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studio.world_gen.graph import generate_graph
from studio.world_gen.terrain import sector_world_xy


def assert_seams(seed: int = 1947, region: str = "forest", size: float = 1536.0, hf: int = 17) -> None:
    graph = generate_graph(seed, region)
    ox0, oy0 = 0.0, 0.0
    ox1, oy1 = size, 0.0
    for j in range(hf):
        xa, ya = sector_world_xy(ox0, oy0, size, hf, hf - 1, j)
        xb, yb = sector_world_xy(ox1, oy1, size, hf, 0, j)
        ha = graph.sample_height(xa, ya)
        hb = graph.sample_height(xb, yb)
        if abs(ha - hb) > 1e-6:
            raise AssertionError(f"east/west seam j={j} {ha} != {hb} xy=({xa},{ya}) vs ({xb},{yb})")
    ox2, oy2 = 0.0, size
    for i in range(hf):
        xa, ya = sector_world_xy(ox0, oy0, size, hf, i, hf - 1)
        xb, yb = sector_world_xy(ox2, oy2, size, hf, i, 0)
        ha = graph.sample_height(xa, ya)
        hb = graph.sample_height(xb, yb)
        if abs(ha - hb) > 1e-6:
            raise AssertionError(f"north/south seam i={i} {ha} != {hb}")


def main() -> None:
    for region in ("forest", "arctic", "coast", "desert"):
        assert_seams(1947, region)
        print(f"OK seams {region}")
    from studio.world_gen.world_profile import load_profile
    from studio.world_gen.biomes import BiomeField

    g = generate_graph(1947, "arctic")
    b = BiomeField(g)
    samples = [b.color(i * 80.0, i * 40.0) for i in range(-20, 20)]
    greens = [c for c in samples if c[1] > c[0] + 0.04 and c[1] > c[2]]
    if len(greens) > 4:
        raise AssertionError(f"arctic still green: {greens[:3]}")
    print("OK arctic palette not grass")
    p = load_profile("arctic")
    if p.material_id != "arctic":
        raise AssertionError(p.material_id)
    print("OK")


if __name__ == "__main__":
    main()
