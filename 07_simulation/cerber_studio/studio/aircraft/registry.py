"""Discover GLB + YAML airframes from assets/airframes and repo models/."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from ..config.paths import AIRFRAMES_DIR, BBOX_DIR, MODELS_DIR
from ..dynamics import PRESETS
from .definition import (
    AircraftClass,
    AircraftDefinition,
    AircraftMetadata,
    AnimationManifest,
    CameraProfile,
    ControlSurfaceSpec,
    DemoFlightProfile,
    RotorSpec,
    VisualModel,
)

log = logging.getLogger("cerber_studio.aircraft")

_ID_RE = re.compile(r"[^a-z0-9_]+")
_SUPERSEDED_RAW = frozenset({"58drun", "basedrone"})


def _slug(name: str) -> str:
    s = _ID_RE.sub("_", name.lower().strip())
    return s.strip("_") or "aircraft"


def _parse_class(raw: str | None, default: AircraftClass = AircraftClass.CUSTOM) -> AircraftClass:
    if not raw:
        return default
    key = str(raw).lower().replace("-", "_").replace(" ", "_")
    for item in AircraftClass:
        if item.value == key:
            return item
    return default


def _vec3(raw, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        return float(raw[0]), float(raw[1]), float(raw[2])
    return fallback


def _rotors(raw) -> list[RotorSpec]:
    out: list[RotorSpec] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict) or not item.get("node"):
            continue
        out.append(
            RotorSpec(
                node=str(item["node"]),
                axis=str(item.get("axis", "Z")),
                direction=float(item.get("direction", 1.0)),
            )
        )
    return out


def _surfaces(raw) -> list[ControlSurfaceSpec]:
    out: list[ControlSurfaceSpec] = []
    if not isinstance(raw, dict):
        return out
    for name, item in raw.items():
        if not isinstance(item, dict) or not item.get("node"):
            continue
        out.append(
            ControlSurfaceSpec(
                name=str(name),
                node=str(item["node"]),
                source=str(item.get("source", "elevator")),
                gain=float(item.get("gain", 1.0)),
                axis=str(item.get("axis", "Y")),
                max_deg=float(item.get("max_deg", 22.0)),
            )
        )
    return out


def _animation(data: dict) -> AnimationManifest:
    raw = data.get("animation") or {}
    return AnimationManifest(
        rotors=_rotors(raw.get("rotors")),
        propellers=_rotors(raw.get("propellers")),
        control_surfaces=_surfaces(raw.get("control_surfaces") or {}),
        flight_clip=str(raw.get("flight_clip") or ""),
        hangar_clip=str(raw.get("hangar_clip") or ""),
    )


def _resolve_model_path(folder: Path, rel: str | None, fallback: Path | None) -> Path | None:
    candidates: list[Path] = []
    if rel:
        raw = Path(str(rel))
        candidates.append(folder / raw)
        candidates.append(MODELS_DIR / raw.name)
        candidates.append(BBOX_DIR / raw.name)
        if raw.is_absolute():
            candidates.append(raw)
    if fallback is not None:
        candidates.append(fallback)
    for path in candidates:
        if path.is_file():
            return path
    return None


def builtin_from_preset(key: str, **overrides) -> AircraftDefinition:
    p = PRESETS[key]
    class_ = AircraftClass.FLYING_WING
    name = p.title
    ident = key
    if key == "ar_wing":
        ident = "ar_wing_pro"
        name = "AR Wing Pro"
    elif key == "s800":
        ident = "reptile_s800"
        name = "Reptile S800"
    return AircraftDefinition(
        id=overrides.get("id", ident),
        name=overrides.get("name", name),
        class_=overrides.get("class_", class_),
        visual=VisualModel(procedural_key=key, scale=p.scale),
        camera=CameraProfile(),
        demo_flight=DemoFlightProfile(
            mass_kg=4.0 if key == "s800" else 5.2,
            cruise_speed_mps=16.0 if key == "s800" else 18.0,
            stall_speed_mps=9.0,
            max_speed_mps=p.max_speed,
            turn_rate_deg=p.turn_rate_deg,
            is_demo=True,
        ),
        meta=AircraftMetadata(
            manufacturer="NULLXES procedural",
            configuration="flying_wing",
            source="builtin",
            demo_params=True,
        ),
    )


def from_raw_glb(path: Path) -> AircraftDefinition:
    ident = _slug(path.stem)
    pretty = path.stem.replace("_", " ").replace("-", " ").strip()
    if pretty.lower() == pretty:
        pretty = pretty.title() if pretty.isalpha() else pretty
    return AircraftDefinition(
        id=ident,
        name=pretty or path.stem,
        class_=AircraftClass.CUSTOM,
        visual=VisualModel(path=path, scale=1.0, auto_normalize=True),
        camera=CameraProfile(),
        demo_flight=DemoFlightProfile(is_demo=True),
        meta=AircraftMetadata(
            manufacturer="",
            configuration="unconfigured",
            source="models",
            demo_params=True,
        ),
        unconfigured=True,
    )


def from_folder(folder: Path) -> AircraftDefinition | None:
    yaml_path = folder / "aircraft.yaml"
    glb = folder / "aircraft.glb"
    gltf = folder / "aircraft.gltf"
    model_file = glb if glb.is_file() else (gltf if gltf.is_file() else None)
    data: dict = {}
    if yaml_path.is_file():
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("invalid aircraft.yaml in %s: %s", folder, exc)
            data = {}
    if not data and model_file is None:
        return None

    ident = str(data.get("id") or folder.name)
    name = str(data.get("name") or folder.name.replace("_", " ").title())
    class_ = _parse_class(data.get("class"), AircraftClass.FLYING_WING)
    model = data.get("model") or {}
    path = _resolve_model_path(folder, model.get("file"), model_file)

    proc = model.get("procedural")
    auto = False
    if path is not None:
        auto = bool(model.get("auto_normalize", not yaml_path.is_file()))

    cam = data.get("camera") or {}
    demo = data.get("demo") or {}
    unconfigured = not yaml_path.is_file()
    return AircraftDefinition(
        id=_slug(ident),
        name=name,
        class_=class_,
        visual=VisualModel(
            path=path,
            procedural_key=str(proc) if proc else None,
            scale=float(model.get("scale", 1.0)),
            up_axis=str(model.get("up_axis", "Z")),
            forward_axis=str(model.get("forward_axis", "Y")),
            auto_normalize=auto,
            rotation=_vec3(model.get("rotation"), (0.0, 0.0, 0.0)),
            offset=_vec3(model.get("offset"), (0.0, 0.0, 0.0)),
        ),
        camera=CameraProfile(
            chase_distance=float(cam.get("chase_distance", 8.0)),
            chase_height=float(cam.get("chase_height", 2.0)),
            nose_offset=_vec3(cam.get("nose_offset"), (0.0, 0.35, 0.12)),
        ),
        demo_flight=DemoFlightProfile(
            mass_kg=float(demo.get("mass_kg", 4.0)),
            cruise_speed_mps=float(demo.get("cruise_speed_mps", 18.0)),
            stall_speed_mps=float(demo.get("stall_speed_mps", 10.0)),
            max_speed_mps=float(demo.get("max_speed_mps", 35.0)),
            turn_rate_deg=float(demo.get("turn_rate_deg", 75.0)),
            is_demo=True,
        ),
        meta=AircraftMetadata(
            manufacturer=str(data.get("manufacturer", "")),
            configuration=str(data.get("configuration", "")),
            source="airframes",
            demo_params=True,
        ),
        unconfigured=unconfigured,
        animation=_animation(data),
    )


class AircraftRegistry:
    def __init__(self) -> None:
        self.items: list[AircraftDefinition] = []

    def scan(self) -> list[AircraftDefinition]:
        found: dict[str, AircraftDefinition] = {}

        if AIRFRAMES_DIR.is_dir():
            for folder in sorted(AIRFRAMES_DIR.iterdir()):
                if not folder.is_dir():
                    continue
                defn = from_folder(folder)
                if defn is None or defn.visual.path is None or not defn.visual.path.is_file():
                    continue
                found[defn.id] = defn

        if MODELS_DIR.is_dir():
            claimed = {
                d.visual.path.resolve()
                for d in found.values()
                if d.visual.path is not None and d.visual.path.is_file()
            }
            for glb in sorted(MODELS_DIR.glob("*.glb")):
                if glb.resolve() in claimed or _slug(glb.stem) in _SUPERSEDED_RAW:
                    continue
                defn = from_raw_glb(glb)
                found[defn.id] = defn
            for gltf in sorted(MODELS_DIR.glob("*.gltf")):
                if gltf.resolve() in claimed or _slug(gltf.stem) in _SUPERSEDED_RAW:
                    continue
                defn = from_raw_glb(gltf)
                found[defn.id] = defn

        self.items = list(found.values())
        self.items.sort(key=lambda d: d.name.lower())
        return self.items

    def get(self, ident: str) -> AircraftDefinition | None:
        for item in self.items:
            if item.id == ident:
                return item
        return None

    def get_or_first(self, ident: str) -> AircraftDefinition:
        hit = self.get(ident)
        if hit is not None:
            return hit
        if self.items:
            return self.items[0]
        raise FileNotFoundError(
            "No aircraft GLB found. Put models in repo models/ or assets/airframes/*/aircraft.glb"
        )
