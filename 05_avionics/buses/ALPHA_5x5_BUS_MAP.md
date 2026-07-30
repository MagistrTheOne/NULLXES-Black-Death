# ALPHA 5×5 — Bus map

| Bus | Devices | Notes |
|-----|---------|-------|
| CAN 1 | ESC_L, ESC_R telemetry | 1 Mbit |
| CAN 2 | spare / LG / PDB | |
| UART / DShot | ESC command if not CAN | from L0 |
| SPI / I2C | IMU A (on FC), IMU B (remote) | ≥0.4 m separation |
| Ethernet | Compute A ↔ Compute B ↔ FC companion | ROS 2 DDS |
| USB | cameras (or CSI on Jetson) | 4 cams |
| Ethernet / UART | LiDAR | mid-360 |

Topic names: `01_requirements/interfaces/ALPHA_5x5_ROS_TOPICS.md`.
