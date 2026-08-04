# 07_simulation

| Area | Status |
|------|--------|
| **`cerber_lab/`** | **Desktop arcade viz** — WASD wing + CERBER PiP (not twin) |
| `digital_twin/topic_map.yaml` | topic contract (OK) |
| `gazebo/` | proxy box only — **BLOCKED** as twin |
| `airsim/` | Multirotor sketch — **BLOCKED** as twin |
| `scenarios/` · `hil/` | YAML templates only — no fake runners |
| `soft_runtime/` | **BLOCKED** — mocks removed |

## CERBER Lab (run now)

```bash
cd 07_simulation/cerber_lab
pip install -r requirements.txt
python run_lab.py --wing ar_wing
python run_lab.py --wing s800 --cerber
```

See `cerber_lab/README.md`.
