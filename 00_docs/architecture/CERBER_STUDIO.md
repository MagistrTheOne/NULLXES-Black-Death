# NULLXES CERBER Studio

**Status:** Product v1 — engineering IDE (virtual world)  
**Code:** `07_simulation/cerber_studio/`  
**Not:** Unity · Unreal · Godot · digital twin · HIL

## What it is

Desktop **Python** laboratory for CERBER perception and pursuit modes:

- PySide6 shell (WORLD · CAMERA · AIRCRAFT · CERBER · TRACKS · LOGS)
- Panda3D 3D viewport (procedural flying-wing models)
- Arcade dynamics v1 (complete — not a stub under Bullet)
- Virtual nose camera → CERBER worker (ONNX Runtime) via ZeroMQ
- IOU multi-object tracker with stable IDs

## Run

```bash
cd 07_simulation/cerber_studio
pip install -r requirements.txt
python run_studio.py
```

## Architecture (v1)

```
PySide6 UI + Panda3D world
        → VirtualCamera (BGR)
        → ZMQ → cerber_worker
        → VisionPipeline (fail-closed) → Tracker v1
        → ZMQ → overlay + TRACKS + LOGS
```

Aircraft visuals v1: procedural presets **s800** · **ar_wing** (product models, not placeholders).

## Honest scope

| Is | Is not |
|----|--------|
| Virtual world for CERBER / modes | Alpha / BLACK DEATH aero twin |
| Real ONNX when weights+sha valid | Fake boxes when ORT blocked |
| Studio v1 complete feature set | REPLAY / HW buttons in UI |

## Next product releases (docs only — not coded here)

- CAD/glTF airframe swap  
- Bullet / richer aero  
- Connect Hardware (USB/CSI + telemetry)  
- SoftBus / ROS 2 bridge  
- Replay from recorded logs  

## Deprecated

`07_simulation/cerber_lab/` (Ursina arcade) — use CERBER Studio.
