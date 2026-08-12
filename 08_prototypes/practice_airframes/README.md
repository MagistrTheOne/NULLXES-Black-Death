# Practice airframes — autonomy / DMI track

**Not** Alpha 5×5 geometry. Goal: prove bus, L0 hold, dual heartbeat (if two SBCs), and DMI intent→guidance on real airframes before Alpha Flight-1.

| Stage | Window | Airframe | Focus |
|-------|--------|----------|-------|
| 1 | ~2026-08-03 | edu sample | power, FC link, real IMU topic, L0 hold, host DMI coordinator |
| 2 | ~2026-09 | **Skywalker X8 PNP** (Flight-1) | CTOL + companion; BOM locked `FLIGHT1_BOM_LOCK.md` |

Canon: [ADR-002 DMI](../../00_docs/adr/ADR-002_DMI_V1.md) · [FLIGHT1_BOM_LOCK.md](../../00_docs/architecture/FLIGHT1_BOM_LOCK.md) · `TEST_PLAN_X8_FLIGHT1.md` · bench in `10_tests/practice/`.

## Proves

- SoftBus / ROS topic contracts with **real** IMU (and later cam/GNSS when wired)
- L0 inner-loop hold from real samples (no invented telemetry in repo)
- DMI: Ground Coordinator on host issues SwarmIntent; agent ACCEPT → GoalMsg → guidance
- Dual-compute heartbeat if two compute modules present

## Does not prove

- Alpha planform / MTOW / endurance claims
- Full Shared World as SLAM
- Multi-ship BLACK DEATH 50×50
- YOLO flight without real ONNX weights
