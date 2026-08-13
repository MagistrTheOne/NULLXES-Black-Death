# 07_simulation

| Area | Status |
|------|--------|
| **`cerber_studio/`** | **PRIMARY vision IDE** — PySide6 + Panda3D + ORT/ZMQ |
| **`bd_sim/`** | **S1 product flight sim / game** — believable arcade flying-wing. Not twin. Not ArduPlane. |
| `cerber_lab/` | **DEPRECATED** — Ursina arcade; use Studio |
| `digital_twin/topic_map.yaml` | topic contract (OK) |
| `gazebo/` | proxy box only — **BLOCKED** as twin |
| `airsim/` | Multirotor sketch — **BLOCKED** as twin |
| `scenarios/` · `hil/` | YAML templates only — no fake runners |
| `soft_runtime/` | **BLOCKED** — mocks removed |

## CERBER Studio (run now)

```bash
cd 07_simulation/cerber_studio
pip install -r requirements.txt
python run_studio.py
```

Canon: `00_docs/architecture/CERBER_STUDIO.md`.

## BD-SIM S1 (game / product arcade)

```bash
cd 07_simulation/bd_sim
pip install -r requirements.txt
python run_sim.py
```

ADR: `00_docs/adr/ADR-008_FLIGHT_SIM.md`. Next FDM = JSBSim (not this folder's job).
