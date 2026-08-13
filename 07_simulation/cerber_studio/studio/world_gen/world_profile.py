"""Region YAML profiles for BLACKBOX World V2."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import yaml

from ..config.paths import STUDIO_ROOT

PROFILES_DIR = STUDIO_ROOT / "worlds" / "profiles"


@dataclass
class WorldProfile:
    id: str
    name: str
    seed_salt: int = 0
    base_height: float = 18.0
    mountain_gain: float = 90.0
    hill_gain: float = 22.0
    ridge_gain: float = 12.0
    continent_scale: float = 18000.0
    mountain_scale: float = 4200.0
    ridge_scale: float = 1400.0
    forest_weight: float = 0.55
    rock_weight: float = 0.2
    grass_weight: float = 0.25
    river_threshold: float = 18.0
    river_count_bias: float = 1.0
    settlement_count: int = 4
    airfield_count: int = 1
    road_width: float = 6.0
    fog_density: float = 0.00042
    sky_preset: str = "clear"
    prop_vegetation: str = "vegetation"
    prop_rocks: str = "rocks"
    prop_buildings: str = "buildings"

    @classmethod
    def from_dict(cls, data: dict) -> WorldProfile:
        known = {f.name for f in fields(cls)}
        raw = {k: v for k, v in data.items() if k in known}
        return cls(**raw)


def load_profile(ident: str) -> WorldProfile:
    key = (ident or "forest").lower()
    path = PROFILES_DIR / f"{key}.yaml"
    if not path.is_file():
        path = PROFILES_DIR / "forest.yaml"
    if not path.is_file():
        return WorldProfile(id="forest", name="NORTHERN FOREST")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "id" not in data:
        data["id"] = key
    if "name" not in data:
        data["name"] = key.replace("_", " ").upper()
    return WorldProfile.from_dict(data)


def list_profiles() -> list[WorldProfile]:
    if not PROFILES_DIR.is_dir():
        return [WorldProfile(id="forest", name="NORTHERN FOREST")]
    out: list[WorldProfile] = []
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        out.append(load_profile(path.stem))
    return out or [WorldProfile(id="forest", name="NORTHERN FOREST")]
