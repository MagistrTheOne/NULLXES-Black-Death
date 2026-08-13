# NULLXES CERBER Studio v1.1

**NULLXES BLACKBOX** product shell + **CERBER Studio** engineering IDE.  
**Not** Unity/Unreal/Godot · **not** digital twin · **not** HIL.

Canon: [`00_docs/architecture/CERBER_STUDIO.md`](../../00_docs/architecture/CERBER_STUDIO.md)

## Stack

| Piece | Tech |
|-------|------|
| GUI | PySide6 |
| 3D | Panda3D (offscreen → Qt viewport) |
| Assets | GLB via `panda3d-gltf` |
| Dynamics | Arcade v1 (complete) |
| IPC | ZeroMQ + msgpack |
| Detect | onnxruntime via `VisionPipeline` |
| Tracker | IOU + stable IDs (`studio/tracker.py`) |

## Run

```bash
cd 07_simulation/cerber_studio
pip install -r requirements.txt

python run_studio.py --demo          # product: Main Menu, 1920×1080 borderless
python run_studio.py                 # engineering IDE
python run_studio.py --engineering
```

User settings: `~/.nullxes/cerber_studio/settings.yaml`  
Logs: `~/.nullxes/cerber_studio/logs/`

## Aircraft models

Drop `.glb` into repo `models/` (or `assets/airframes/<id>/aircraft.glb` + `aircraft.yaml`). Restart / rescan. Raw GLB appears as **UNCONFIGURED MODEL** with a generic fixed-wing demo profile.

## Product controls

| Input | Action |
|-------|--------|
| WASD | pitch / roll |
| Q E | yaw |
| Shift / Ctrl | throttle |
| C | nose / chase camera |
| Space | launch |
| R | reset ego |
| 1 / 2 / 3 / 4 | MANUAL / ASSIST / FOLLOW / MISSION |
| Esc | pause |
| Mouse drag | hangar orbit / chase offset |
| Wheel | hangar zoom |

## Engineering controls

| Input | Action |
|-------|--------|
| WASD | pitch / roll |
| Q E | yaw |
| Shift / Ctrl | throttle |
| F1 | reset target |
| R | reset ego |
| 1 / 2 / 3 / 4 | MANUAL / ASSIST / PURSUIT / MISSION |

## Acceptance

- `--demo` opens Main Menu at borderless Full HD (clamped to the monitor)
- GLB from `models/` appears in AIRCRAFT
- Engineering `run_studio.py` still opens the IDE docks
- Valid ORT → boxes; invalid → BLOCKED, no fake detections
