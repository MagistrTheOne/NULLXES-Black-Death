# Planning

| Package | Role | Status |
|---------|------|--------|
| `behaviour/` | `AlphaBT` flight-mode policy | shipped |
| `trajectory/` | Path / lawnmower / GoalMsg tick | HAS_CODE |
| `missions/` | MissionPlan YAML + executor | HAS_CODE |

Alpha does not claim a `py_trees` graph. Mode logic lives in `behaviour/alpha_bt.py`.
