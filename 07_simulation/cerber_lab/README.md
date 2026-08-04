# CERBER Lab — visual flight sim (arcade)

**Status:** desktop viz app · **not** Alpha / BLACK DEATH digital twin · **not** HIL  
**Folder:** `07_simulation/cerber_lab/`

WASD flying-wing trainer with optional **real CERBER ONNX** overlay on the nose camera.

| Wing preset | Role |
|-------------|------|
| `s800` | Reptile S800-class · small / agile |
| `ar_wing` | SonicModell AR Wing Pro-class · demo face |

## Run (Windows / Linux)

```bash
cd "07_simulation/cerber_lab"
pip install -r requirements.txt
python run_lab.py
python run_lab.py --wing ar_wing
python run_lab.py --wing s800 --cerber   # needs detector_alpha*.onnx + sha
```

## Controls

| Key | Action |
|-----|--------|
| W / S | pitch |
| A / D | roll |
| Q / E | yaw |
| Shift / Ctrl | throttle |
| F1 | spawn / reset target UAV |
| C | toggle CERBER overlay |
| 1 / 2 / 3 | MANUAL / ASSIST / PURSUIT(sim) |
| R | reset ego |
| Esc | quit |

## Modes

- **MANUAL** — only WASD  
- **ASSIST** — auto yaw-toward target if CERBER/track has a lock (sim helper)  
- **PURSUIT** — stronger auto nose-point at target (sim only; not flight proof)

## CERBER

Uses repo `VisionPipeline` + `detector_alpha.yaml` / `_v2` / `_v2b`.  
If weights/sha missing → overlay shows `CERBER BLOCKED` (no fake boxes).

## Honest scope

Arcade aero. Visual behaviour of CERBER in FOV.  
Hardware and Gazebo twin come later — same product shell.
