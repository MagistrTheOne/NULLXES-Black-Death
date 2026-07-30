# ALPHA 5×5 — Fault management thresholds

**Status:** locked for Alpha BT / FM

| Mode | Enter when | Exit / action |
|------|------------|---------------|
| NOMINAL | All: compute A&B healthy, ≥1 main thruster, fusion OK, vision ≥2 cams | Full mission |
| DEGRADED_PROP | One main thruster lost OR thrust residual < 55% commanded for >2 s | Shrink envelope; prefer RTB if >60 km from base |
| DEGRADED_SENS | Any of: camera loss, IMU loss, GNSS deny >5 s, LiDAR loss | Raise nav covariance; no aggressive terrain follow |
| DEGRADED_COMPUTE | Peer heartbeat miss > **150 ms** OR active channel crash | Failover ≤ **500 ms**; sticky active |
| SAFE_LOITER | Both thrusters critical OR nav integrity fail OR dual-compute both dead for high-level | L0 hold / civil loiter; land when site OK |
| RTB | Mission abort OR battery SOC < **25%** OR FM escalate | Direct return corridor |

## Numeric trips

| Signal | Trip |
|--------|------|
| Heartbeat timeout | 150 ms |
| Takeover deadline | 500 ms |
| GNSS coast max | 30 s then SAFE_LOITER if no visual/alt backup |
| Vision cams remaining | <2 → DEGRADED_SENS |
| Battery SOC RTB | 25% |
| Battery SOC land-now | 12% |
| Setpoint stale (L0) | 200 ms → hold attitude |

Civil terminology only. No external API required for any mode.
