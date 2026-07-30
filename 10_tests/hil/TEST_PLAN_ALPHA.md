# HIL test plan — ALPHA 5×5 dual-compute

## Setup

1. Two autonomy processes (A primary, B standby) + L0 smoke or FC HIL  
2. Shared sim clock / ROS topics from `topic_map.yaml`  
3. Scenario: `07_simulation/hil/failover_A_kill.yaml`

## Acceptance

| # | Check | Pass |
|---|-------|------|
| 1 | Start active = A | |
| 2 | Kill A @ t=20 s | |
| 3 | Active = B within **500 ms** | |
| 4 | Mode DEGRADED_COMPUTE | |
| 5 | L0 still outputting actuator cmds | |
| 6 | No outbound cloud/API calls | |

Log: store `/bd/dual/*` and `/bd/l0/*` bag for 60 s.
