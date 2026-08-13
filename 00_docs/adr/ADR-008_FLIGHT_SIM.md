# ADR-008 — NULLXES Flight Simulation Architecture

**Status:** Accepted  
**Date:** 2026-08-13  
**Deciders:** Maga / NULLXES systems  
**Refs:** [CERBER_STUDIO.md](../architecture/CERBER_STUDIO.md) · `07_simulation/bd_sim/`

## Context

Need a product flying-wing demo without claiming Gazebo/AirSim twin or a second flight controller. CERBER Studio is a vision IDE, not a game. Combat AP stays Pixhawk 6C + ArduPlane 4.7.

## Decision

1. **Renderer:** Panda3D (+ glTF) on S0–S3. Do not replace with Godot/Unity/Unreal.
2. **Product split:** `cerber_studio/` = CERBER IDE. `bd_sim/` = S1 game/sim.
3. **S1 dynamics:** energy / point-mass arcade in `bd_sim/sim/dynamics.py`. Not CFD. Not X8 proof.
4. **Serious FDM (S2):** JSBSim headless. Panda3D consumes `VehicleState`. No custom 6DOF.
5. **SITL (S3):** ArduPlane SITL + JSBSim + MAVLink. Not before Flight-1 hop.
6. **HIL (S4):** Pixhawk 6C. Python never PWM.
7. **Sensors S1:** Panda RGB + derived nav. CERBER ZMQ fail-closed.
8. **Comms S1:** in-process + ZMQ. MAVLink only S3+.
9. **Recording:** JSONL.
10. **Gazebo / AirSim / soft_runtime twin:** BLOCKED.
11. Simulation stages named **S0–S5**. Do not call them L0 (L0 = inner-loop on 6C).

## Consequences

DemoPilot must not emit `/bd/l0/setpoint`. Arcade cannot be used as Flight-1 evidence. After Flight-1 logs exist, calibrate JSBSim XML and stop growing Python aero.
