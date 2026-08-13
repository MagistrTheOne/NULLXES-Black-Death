"""World GLB packs. Generator picks category; pack decides look."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config.paths import STUDIO_ROOT

PACKS_DIR = STUDIO_ROOT / "assets" / "world"


@dataclass
class PropDef:
    id: str
    file: str
    weight: float = 1.0
    lod: bool = False
    category: str = "prop"


@dataclass
class AssetPack:
    id: str
    biomes: list[str] = field(default_factory=list)
    category: str = "vegetation"
    props: list[PropDef] = field(default_factory=list)
    root: Path = PACKS_DIR

    def resolve(self, prop: PropDef) -> Path | None:
        name = Path(prop.file).name
        for path in (self.root / prop.file, self.root / name, PACKS_DIR / prop.file, PACKS_DIR / name):
            if path.is_file():
                return path
        return None


def _from_yaml(path: Path) -> AssetPack | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    props = []
    raw_props = data.get("props") or {}
    if isinstance(raw_props, dict):
        for key, spec in raw_props.items():
            if not isinstance(spec, dict):
                continue
            props.append(
                PropDef(
                    id=str(key),
                    file=str(spec.get("file") or ""),
                    weight=float(spec.get("weight", 1.0)),
                    lod=bool(spec.get("lod", False)),
                    category=str(spec.get("category") or data.get("category") or "prop"),
                )
            )
    return AssetPack(
        id=str(data.get("id") or path.stem),
        biomes=[str(b) for b in (data.get("biomes") or [])],
        category=str(data.get("category") or path.parent.name),
        props=props,
        root=path.parent,
    )


def scan_packs() -> list[AssetPack]:
    found: list[AssetPack] = []
    if not PACKS_DIR.is_dir():
        return found
    for path in sorted(PACKS_DIR.rglob("pack.yaml")):
        pack = _from_yaml(path)
        if pack is not None:
            found.append(pack)
    return found


def pick_for_biome(biome: str, category: str, packs: list[AssetPack] | None = None) -> AssetPack | None:
    pool = packs if packs is not None else scan_packs()
    key = (biome or "").lower()
    matched = [p for p in pool if p.category == category and (not p.biomes or key in p.biomes or "all" in p.biomes)]
    if matched:
        return matched[0]
    generic = [p for p in pool if p.category == category]
    return generic[0] if generic else None
