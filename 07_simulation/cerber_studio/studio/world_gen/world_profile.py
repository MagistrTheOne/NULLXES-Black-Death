"""Region YAML profiles for BLACKBOX World V3."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import yaml

from ..config.paths import STUDIO_ROOT

PROFILES_DIR = STUDIO_ROOT / "worlds" / "profiles"

_DEFAULT_LOWLAND = (0.22, 0.32, 0.16)
_DEFAULT_SLOPE = (0.38, 0.36, 0.32)
_DEFAULT_HIGHLAND = (0.42, 0.40, 0.36)
_DEFAULT_SNOW = (0.86, 0.88, 0.90)
_DEFAULT_WATER = (0.10, 0.22, 0.28)


def _rgb(raw, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return float(raw[0]), float(raw[1]), float(raw[2])
    return fallback


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
    micro_gain: float = 4.0
    micro_scale: float = 280.0
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
    material_id: str = "temperate"
    lowland_rgb: tuple[float, float, float] = _DEFAULT_LOWLAND
    slope_rgb: tuple[float, float, float] = _DEFAULT_SLOPE
    highland_rgb: tuple[float, float, float] = _DEFAULT_HIGHLAND
    snow_rgb: tuple[float, float, float] = _DEFAULT_SNOW
    water_rgb: tuple[float, float, float] = _DEFAULT_WATER
    snow_alt: float = 140.0
    haze_rgb: tuple[float, float, float] | None = None
    temperature_c: float = 16.0
    veg_density: str = "full"
    water_enabled: bool = False
    water_level: float = 4.0
    terrain_label: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> WorldProfile:
        raw = dict(data or {})
        terrain = raw.pop("terrain", None) or {}
        hp = terrain.get("height_profile") or {}
        mp = terrain.get("material_profile") or {}
        atmos = raw.pop("atmosphere", None) or {}
        veg = raw.pop("vegetation", None) or {}
        water = raw.pop("water", None) or {}
        raw.pop("landmarks", None)
        for src, src_key, dest in (
            (hp, "micro_gain", "micro_gain"),
            (hp, "micro_scale", "micro_scale"),
            (mp, "id", "material_id"),
            (mp, "snow_alt", "snow_alt"),
        ):
            if src_key in src:
                raw[dest] = src[src_key]
        if mp.get("lowland"):
            raw["lowland_rgb"] = _rgb(mp["lowland"], _DEFAULT_LOWLAND)
        if mp.get("slope"):
            raw["slope_rgb"] = _rgb(mp["slope"], _DEFAULT_SLOPE)
        if mp.get("highland"):
            raw["highland_rgb"] = _rgb(mp["highland"], _DEFAULT_HIGHLAND)
        if mp.get("snow"):
            raw["snow_rgb"] = _rgb(mp["snow"], _DEFAULT_SNOW)
        if atmos.get("haze"):
            raw["haze_rgb"] = _rgb(atmos["haze"], (0.70, 0.76, 0.82))
        if "sky" in atmos:
            raw["sky_preset"] = atmos["sky"]
        if "temperature" in atmos:
            raw["temperature_c"] = float(atmos["temperature"])
        if veg.get("density"):
            raw["veg_density"] = str(veg["density"])
        if "enabled" in water:
            raw["water_enabled"] = bool(water["enabled"])
        if "level" in water:
            raw["water_level"] = float(water["level"])
        if water.get("color"):
            raw["water_rgb"] = _rgb(water["color"], _DEFAULT_WATER)
        if mp.get("label"):
            raw["terrain_label"] = str(mp["label"])
        known = {f.name for f in fields(cls)}
        cleaned = {}
        for k, v in raw.items():
            if k not in known:
                continue
            if k.endswith("_rgb") and isinstance(v, (list, tuple)):
                cleaned[k] = _rgb(v, getattr(cls, k) if hasattr(cls, k) else (0.3, 0.3, 0.3))
            else:
                cleaned[k] = v
        return cls(**cleaned)


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
