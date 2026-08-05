# NULLXES CERBER Studio v1

**Engineering IDE** for CERBER perception in a virtual world.  
**Not** Unity/Unreal/Godot · **not** digital twin · **not** HIL.

Canon: [`00_docs/architecture/CERBER_STUDIO.md`](../../00_docs/architecture/CERBER_STUDIO.md)

## Stack

| Piece | Tech |
|-------|------|
| GUI | PySide6 |
| 3D | Panda3D (offscreen → Qt viewport) |
| Dynamics | Arcade v1 (complete) |
| IPC | ZeroMQ + msgpack |
| Detect | onnxruntime via `VisionPipeline` |
| Tracker | IOU + stable IDs (`studio/tracker.py`) |

## Run

```bash
cd 07_simulation/cerber_studio
pip install -r requirements.txt
python run_studio.py
```

1. Click viewport (focus for WASD).  
2. **CERBER → Start worker** (needs valid ONNX + sha for boxes; otherwise BLOCKED status, no fake detections).  
3. WORLD / AIRCRAFT / CAMERA panels are live.

## Controls

| Input | Action |
|-------|--------|
| WASD | pitch / roll |
| Q E | yaw |
| Shift / Ctrl | throttle |
| F1 | reset target |
| R | reset ego |
| 1 / 2 / 3 | MANUAL / ASSIST / PURSUIT |

## Panels (all working)

WORLD · CAMERA · AIRCRAFT · CERBER · TRACKS · LOGS · CERBER EYE (PiP)

## Aircraft models v1

Procedural presets **s800** · **ar_wing** — product visuals for Studio v1.

## Acceptance

- IDE opens with 3D flight  
- Worker start/stop works  
- Valid ORT → boxes + track table; invalid → BLOCKED in CERBER/LOGS  
- No `TODO`/`FIXME` stubs in this tree  

Deprecated Ursina lab: `../cerber_lab/`.
