"""Load GLB / procedural visuals. panda3d-gltf official path for .glb."""

from __future__ import annotations

import logging
from pathlib import Path

from panda3d.core import NodePath, Vec3

from ..dynamics import PRESETS, WingParams, preset
from .definition import AircraftDefinition, VisualModel

log = logging.getLogger("cerber_studio.aircraft")

_GLTF_PATCHED = False


def ensure_gltf(loader) -> bool:
    global _GLTF_PATCHED
    if _GLTF_PATCHED:
        return True
    try:
        import gltf

        if hasattr(gltf, "patch_loader"):
            gltf.patch_loader(loader)
            _GLTF_PATCHED = True
            return True
        if hasattr(gltf, "load_model"):
            _GLTF_PATCHED = True
            return True
    except Exception as exc:  # noqa: BLE001
        log.warning("gltf unavailable: %s", exc)
        return False
    return False


def to_wing_params(defn: AircraftDefinition) -> WingParams:
    key = defn.visual.procedural_key if defn.visual.procedural_key in PRESETS else None
    base = preset(key or "ar_wing")
    d = defn.demo_flight
    return WingParams(
        key=defn.id,
        title=defn.name,
        scale=defn.visual.scale if not defn.visual.auto_normalize else base.scale,
        max_speed=float(d.max_speed_mps),
        turn_rate_deg=float(d.turn_rate_deg),
        stall_speed=float(d.stall_speed_mps),
        cruise_speed=float(d.cruise_speed_mps),
        color_rgb=base.color_rgb,
        accent_rgb=base.accent_rgb,
    )


def _apply_axes(node: NodePath, visual: VisualModel) -> None:
    up = (visual.up_axis or "Z").upper()
    if up == "Y":
        node.setP(-90.0)
    elif up == "X":
        node.setR(90.0)


def _normalize(node: NodePath, visual: VisualModel, target_span: float = 3.2) -> None:
    bounds = node.getTightBounds()
    if not bounds:
        node.setScale(visual.scale)
        return
    mn, mx = bounds
    size = mx - mn
    span = max(float(size.x), float(size.y), float(size.z), 1e-4)
    scale = visual.scale * (target_span / span if visual.auto_normalize else 1.0)
    center = (mn + mx) * 0.5
    node.setPos(node, Vec3(-center.x, -center.y, -center.z))
    node.setScale(scale)


def load_visual(loader, parent: NodePath, defn: AircraftDefinition) -> tuple[NodePath, str]:
    """Attach visual. Returns (node, error). error empty on success."""
    from ..world import attach_wing

    visual = defn.visual
    if visual.path is None or not visual.path.is_file():
        params = to_wing_params(defn)
        if visual.procedural_key in PRESETS:
            params = preset(visual.procedural_key)
            params = WingParams(
                key=defn.id,
                title=defn.name,
                scale=params.scale,
                max_speed=defn.demo_flight.max_speed_mps,
                turn_rate_deg=defn.demo_flight.turn_rate_deg,
                color_rgb=params.color_rgb,
                accent_rgb=params.accent_rgb,
            )
        return attach_wing(parent, params), ""

    if not ensure_gltf(loader):
        node = attach_wing(parent, to_wing_params(defn))
        return node, visual.path.name

    try:
        model_np = None
        try:
            import gltf as gltf_mod

            if hasattr(gltf_mod, "load_model"):
                loaded = gltf_mod.load_model(str(visual.path))
                if loaded is not None:
                    model_np = NodePath(loaded) if not isinstance(loaded, NodePath) else loaded
        except Exception:  # noqa: BLE001
            model_np = None
        if model_np is None:
            model_np = loader.loadModel(str(visual.path))
        if model_np is None:
            raise RuntimeError("loader returned None")
        root = parent.attachNewNode(f"ego_{defn.id}")
        model_np.reparentTo(root)
        _apply_axes(model_np, visual)
        _normalize(model_np, visual)
        return root, ""
    except Exception as exc:  # noqa: BLE001
        log.exception("GLB load failed %s: %s", visual.path, exc)
        node = attach_wing(parent, to_wing_params(defn))
        return node, visual.path.name
