# FLIGHT-1 BOM Lock

**Status:** PENDING_NULLXES — not frozen until rows below are filled.  
**Research baseline:** [ONBOARD_PERCEPTION_RESEARCH_2026-08.md](ONBOARD_PERCEPTION_RESEARCH_2026-08.md)

| Item | Recommended default | Locked value | Owner |
|------|---------------------|--------------|-------|
| Companion SoM | Jetson Orin NX 16GB | _PENDING_ | NULLXES |
| Carrier P/N | CSI or GMSL + NVMe + UART | _PENDING_ | NULLXES |
| Camera | Global shutter CSI/GMSL IMX5xx-class | _PENDING_ | NULLXES |
| Lens / FOV | ~70–90° H forward | _PENDING_ | NULLXES |
| FC | Matek H743-WING V3 | _PENDING_ | NULLXES |
| FC firmware | ArduPilot Plane | _PENDING_ | NULLXES |
| GNSS | Matek M10-5883 or CAN GPS | _PENDING_ | NULLXES |
| Power budget companion | 15–25 W cruise (nvpmodel) | _PENDING_ W | NULLXES |
| Mass budget companion+cam+cool | — | _PENDING_ g | NULLXES |
| GPL on companion image | OpenVINS vs Basalt | _PENDING_ | NULLXES |

Freeze rule: items 1–6 + license + power/mass required before `SENSOR_ARCHITECTURE.md` final.
