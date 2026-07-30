# ALPHA 5×5 — Time sync A/B

| Item | Spec |
|------|------|
| Method | PTP (hardware if NIC allows) else chrono sync over `/bd/dual/mirror` stamps |
| L0 clock | monotonic steady_clock on FC; stamp IMU |
| Autonomy | align camera/LiDAR/GNSS to FC time via offset estimate |
| Failover | election uses local receive time; timeout 150 ms independent of PTP |
| Max skew target | ≤ 5 ms A↔B in NOMINAL |

Without PTP lock → still fly; raise nav covariance (DEGRADED_SENS if skew >20 ms sustained).
