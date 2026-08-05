# 07_simulation

| Area | Status |
|------|--------|
| **`cerber_studio/`** | **PRIMARY** — NULLXES CERBER Studio (PySide6 + Panda3D + ORT/ZMQ) |
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
