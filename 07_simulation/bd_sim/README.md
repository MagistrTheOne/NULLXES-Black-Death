# NULLXES BD Flight Sim (S1)

**Stage:** S1 believable arcade flying-wing. **Not** twin. **Not** ArduPlane. **Not** CERBER Studio.

Studio stays the vision IDE: `../cerber_studio/`. This folder is the product demo / game sim.

```bash
cd 07_simulation/bd_sim
pip install -r requirements.txt
python run_sim.py
python run_sim.py --cerber
```

`--cerber` publishes nose RGB to `tcp://127.0.0.1:5593`. Start the Studio worker with matching ports. No weights → BLOCKED, no fake boxes.

## Controls

| Key | Action |
|-----|--------|
| W/S | pitch |
| A/D | roll |
| Q | yaw left |
| E | LAUNCH (no hover) |
| Shift / Ctrl | throttle |
| 1–4 | MANUAL / ASSIST / FOLLOW / MISSION |
| F1 | reset target |
| R | reset ego |

## Output

JSONL: `07_simulation/bd_sim/runs/bd_sim_*.jsonl`  
glTF: drop `assets/airframes/x8.glb` (gitignored). Fallback = procedural wing.

## Does not prove

X8 aero, Pixhawk, SITL, HIL. Next FDM = JSBSim (S2). See `00_docs/adr/ADR-008_FLIGHT_SIM.md`.
