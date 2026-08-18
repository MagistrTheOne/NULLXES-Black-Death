"""Persistent product settings — ~/.nullxes/cerber_studio/settings.yaml."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .paths import settings_path

RESOLUTION_CANDIDATES: tuple[tuple[int, int], ...] = (
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
)

FPS_LIMITS: tuple[int, ...] = (30, 60, 120, 144, 0)  # 0 = unlimited
UI_SCALES: tuple[str, ...] = ("auto", "80", "90", "100", "110", "125", "150")
FOV_VALUES: tuple[int, ...] = (60, 70, 80, 90, 100, 110)

DEFAULT_BINDINGS: dict[str, str] = {
    "pitch_up": "S",
    "pitch_down": "W",
    "roll_left": "A",
    "roll_right": "D",
    "yaw_left": "Q",
    "yaw_right": "X",
    "throttle_up": "Shift",
    "throttle_down": "Ctrl",
    "launch": "E",
    "reset": "R",
    "mode_manual": "1",
    "mode_assist": "2",
    "mode_follow": "3",
    "mode_mission": "4",
    "pause": "Esc",
}


def _merge(default: dict[str, Any], loaded: Any) -> dict[str, Any]:
    out = deepcopy(default)
    if not isinstance(loaded, dict):
        return out
    for key, val in loaded.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = val
    return out


@dataclass
class DisplaySettings:
    mode: str = "borderless"  # fullscreen | borderless | windowed
    resolution: list[int] = field(default_factory=lambda: [1920, 1080])
    vsync: bool = True
    fps_limit: int = 60
    ui_scale: str = "auto"
    fov: int = 80


@dataclass
class GraphicsSettings:
    preset: str = "high"  # low | medium | high | ultra
    render_scale: float = 1.0
    msaa: int = 4  # 0, 2, 4, 8 — applied at engine boot
    texture_quality: str = "high"  # low | medium | high
    view_distance: str = "high"  # low | medium | high


@dataclass
class AudioSettings:
    master: float = 0.8
    music: float = 0.75
    engine: float = 0.8
    wind: float = 0.7
    environment: float = 0.65
    ui: float = 0.7
    warning: float = 0.85
    muted: bool = False


@dataclass
class HudSettings:
    preset: str = "flight"  # clean | flight | operator | engineering
    layer: str = "flight"
    hud: bool = True
    minimal: bool = False
    fps: bool = False
    telemetry: bool = True
    cerber_tracks: bool = True
    target_boxes: bool = True
    operator_tab: bool = False
    mission_path: bool = True
    debug_labels: bool = False
    reticle: bool = True
    flight_vector: bool = False
    altitude: bool = True
    speed: bool = True
    throttle: bool = True
    mode: bool = True


@dataclass
class ControlSettings:
    sensitivity: float = 1.0
    camera_sensitivity: float = 1.0
    invert_y: bool = False
    bindings: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_BINDINGS))


@dataclass
class SimulationSettings:
    difficulty: str = "standard"  # arcade | standard | strict
    wind: str = "low"  # off | low | medium | high
    failures: bool = False
    ground_collision: bool = True
    target_behaviour: str = "simple"  # static | simple | evasive
    speed: float = 1.0  # 0.5 | 1.0 | 2.0
    launch_assist: bool = True
    backend: str = "arcade"


@dataclass
class SessionMemory:
    aircraft_id: str = "animated_drone"
    target_id: str = "animated_drone"
    mission_id: str = "free_flight"
    region_id: str = "forest"
    world_seed: int = 1947
    weather: str = "clear"
    time_flow: str = "1x"


@dataclass
class UserSettings:
    language: str = "ru"
    display: DisplaySettings = field(default_factory=DisplaySettings)
    graphics: GraphicsSettings = field(default_factory=GraphicsSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    hud: HudSettings = field(default_factory=HudSettings)
    controls: ControlSettings = field(default_factory=ControlSettings)
    simulation: SimulationSettings = field(default_factory=SimulationSettings)
    session: SessionMemory = field(default_factory=SessionMemory)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserSettings:
        base = cls()
        merged = _merge(base.to_dict(), data)
        disp = DisplaySettings(**{k: merged["display"][k] for k in DisplaySettings().__dict__})
        gfx = GraphicsSettings(**{k: merged["graphics"][k] for k in GraphicsSettings().__dict__})
        audio = AudioSettings(**{k: merged["audio"][k] for k in AudioSettings().__dict__})
        hud = HudSettings(**{k: merged["hud"][k] for k in HudSettings().__dict__})
        ctrl_raw = merged["controls"]
        bindings = dict(DEFAULT_BINDINGS)
        bindings.update(ctrl_raw.get("bindings") or {})
        if str(bindings.get("launch", "")).upper() == "SPACE" and str(bindings.get("yaw_right", "")).upper() == "E":
            bindings["launch"] = "E"
            bindings["yaw_right"] = "X"
        controls = ControlSettings(
            sensitivity=float(ctrl_raw.get("sensitivity", 1.0)),
            camera_sensitivity=float(ctrl_raw.get("camera_sensitivity", 1.0)),
            invert_y=bool(ctrl_raw.get("invert_y", False)),
            bindings=bindings,
        )
        sim = SimulationSettings(**{k: merged["simulation"][k] for k in SimulationSettings().__dict__})
        sim.launch_assist = bool(getattr(sim, "launch_assist", True))
        sess = SessionMemory(**{k: merged["session"][k] for k in SessionMemory().__dict__})
        gfx.render_scale = float(max(0.5, min(1.5, gfx.render_scale)))
        if disp.fov not in FOV_VALUES:
            disp.fov = 80
        if disp.ui_scale not in UI_SCALES:
            disp.ui_scale = "auto"
        if disp.mode not in ("fullscreen", "borderless", "windowed"):
            disp.mode = "borderless"
        if not isinstance(disp.resolution, list) or len(disp.resolution) != 2:
            disp.resolution = [1920, 1080]
        lang = str(merged.get("language") or "ru").lower()
        if lang not in ("ru", "en"):
            lang = "ru"
        apply_hud_preset(hud, hud.preset, overwrite=False)
        return cls(
            language=lang,
            display=disp,
            graphics=gfx,
            audio=audio,
            hud=hud,
            controls=controls,
            simulation=sim,
            session=sess,
        )

    @classmethod
    def load(cls, path: Path | None = None) -> UserSettings:
        target = path or settings_path()
        if not target.is_file():
            settings = cls()
            settings.save(target)
            return settings
        try:
            raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return cls()
        return cls.from_dict(raw)

    def save(self, path: Path | None = None) -> None:
        target = path or settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def apply_hud_preset(hud: HudSettings, preset: str, *, overwrite: bool) -> None:
    name = (preset or "flight").lower()
    hud.preset = name
    hud.layer = name
    hud.operator_tab = name == "operator"
    if name == "clean":
        flags = dict(
            hud=True,
            minimal=True,
            fps=False,
            telemetry=True,
            cerber_tracks=False,
            target_boxes=False,
            mission_path=False,
            debug_labels=False,
            reticle=True,
            flight_vector=False,
            altitude=True,
            speed=True,
            throttle=True,
            mode=True,
        )
    elif name == "flight":
        flags = dict(
            hud=True,
            minimal=False,
            fps=False,
            telemetry=True,
            cerber_tracks=False,
            target_boxes=False,
            mission_path=False,
            debug_labels=False,
            reticle=False,
            flight_vector=False,
            altitude=True,
            speed=True,
            throttle=True,
            mode=True,
        )
    elif name == "engineering":
        flags = dict(
            hud=True,
            minimal=False,
            fps=True,
            telemetry=True,
            cerber_tracks=True,
            target_boxes=True,
            mission_path=True,
            debug_labels=True,
            reticle=True,
            flight_vector=True,
            altitude=True,
            speed=True,
            throttle=True,
            mode=True,
        )
    else:
        flags = dict(
            hud=True,
            minimal=False,
            fps=False,
            telemetry=True,
            cerber_tracks=True,
            target_boxes=True,
            mission_path=True,
            debug_labels=False,
            reticle=True,
            flight_vector=False,
            altitude=True,
            speed=True,
            throttle=True,
            mode=True,
        )
    if overwrite:
        for key, val in flags.items():
            setattr(hud, key, val)
    else:
        hud.minimal = flags["minimal"] if name != hud.preset else hud.minimal


def apply_graphics_preset(gfx: GraphicsSettings, preset: str) -> None:
    name = (preset or "high").lower()
    gfx.preset = name
    table = {
        "low": dict(render_scale=0.7, msaa=0, texture_quality="low", view_distance="low"),
        "medium": dict(render_scale=0.85, msaa=2, texture_quality="medium", view_distance="medium"),
        "high": dict(render_scale=1.0, msaa=4, texture_quality="high", view_distance="high"),
        "ultra": dict(render_scale=1.25, msaa=8, texture_quality="high", view_distance="high"),
    }
    row = table.get(name, table["high"])
    gfx.render_scale = float(row["render_scale"])
    gfx.msaa = int(row["msaa"])
    gfx.texture_quality = str(row["texture_quality"])
    gfx.view_distance = str(row["view_distance"])
