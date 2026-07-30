# Gazebo — ALPHA 5×5 (WSL2)

**Status:** BLOCKED — no flight-representative vehicle model yet.

## Required before claiming twin

1. WSL2 Ubuntu 24.04 + ROS 2 Jazzy  
2. Real SDF/URDF: planform geometry, elevons, dual motors, mass/inertia from mass budget  
3. Plugins publishing canon topics in `digital_twin/topic_map.yaml`  

`models/alpha_5x5/model.sdf` is a **collision proxy box only** — not a physics twin. Do not use it for control validation.
