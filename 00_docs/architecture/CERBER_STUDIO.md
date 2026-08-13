# NULLXES CERBER Studio

**Status:** Product v1.1 — engineering IDE + demonstration shell (virtual world)  
**Code:** `07_simulation/cerber_studio/`  
**Not:** Unity · Unreal · Godot · digital twin · HIL

## What it is

Desktop **Python** laboratory for CERBER perception and pursuit modes:

- PySide6 product shell (`--demo`): Main Menu → Aircraft → Mission → Flight
- PySide6 engineering IDE (`run_studio.py`): WORLD · CAMERA · AIRCRAFT · CERBER · TRACKS · LOGS
- Panda3D viewport (procedural flying-wing + user GLB)
- Arcade dynamics v1 (complete — not a stub under Bullet)
- Virtual nose camera → CERBER worker (ONNX Runtime) via ZeroMQ
- IOU multi-object tracker with stable IDs

## Run

```bash
cd 07_simulation/cerber_studio
pip install -r requirements.txt
python run_studio.py --demo
python run_studio.py
```

## Architecture (v1.1)

```
PRODUCT UI
     ↓
SimulationSession
     ↓
PySide6 + Panda3D world
        → VirtualCamera (BGR)
        → ZMQ → cerber_worker
        → VisionPipeline (fail-closed) → Tracker v1
        → ZMQ → overlay + TRACKS / product HUD
```

Aircraft: YAML manifests under `assets/airframes/` plus auto-scan of repo `models/*.glb`. Visual GLB is not physics. DemoFlightProfile drives ArcadeDynamics.

User settings: `~/.nullxes/cerber_studio/settings.yaml` (not git-tracked).

## Honest scope

| Is | Is not |
|----|--------|
| Virtual world for CERBER / modes | Alpha / BLACK DEATH aero twin |
| Real ONNX when weights+sha valid | Fake boxes when ORT blocked |
| GLB preview + generic FW profile | Quad behaviour on a flying wing |
| Demo missions | ArduPlane Mission Protocol |

## Deprecated

`07_simulation/cerber_lab/` (Ursina arcade) — use CERBER Studio.
