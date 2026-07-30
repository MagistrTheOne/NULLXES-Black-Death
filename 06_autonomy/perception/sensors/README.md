# Sensors adapters

**BLOCKED** — no production drivers in this tree yet.

Expected (when wired from `05_avionics` / vendor SDKs):
- cameras → `ImageMsg` on `/bd/cam/*`
- IMU → `ImuMsg` on `/bd/l0/imu` (linear accel ENU, gravity removed)
- GNSS → `GnssFix` on `/bd/gnss/fix`
- LiDAR → scan topic `/bd/lidar/scan`

Do not add fake publishers or synthetic samples here.
