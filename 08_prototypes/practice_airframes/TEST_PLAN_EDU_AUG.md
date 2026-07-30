# TEST PLAN — edu sample (~2026-08-03)

**Platform:** first edu airframe (practice)  
**BLOCKED until:** physical kit + FC + at least one real IMU publishing `/bd/l0/imu` (or L0 driver equivalent)

## Pre-arrival (repo ready)

- [ ] `06_autonomy/dmi` unit tests green in CI
- [ ] `10_tests/practice/bench_smoke_contracts.py` passes (static contracts)
- [ ] ADR-002 / DMI_V1 read by team

## Day-0 bench (power / link)

- [ ] Power rails stable; ESC load bank or props safe
- [ ] FC link up; L0 library or soft L0 receives **real** IMU
- [ ] Publish `/bd/l0/health` with measured flags only (no invented esc_ok)

## Autonomy smoke

- [ ] L0 hold / setpoint path with real IMU (no synthetic stream from repo tools)
- [ ] If dual SBC: heartbeat A/B + active election
- [ ] Ground DMI coordinator on host: issue one `SwarmIntent` (sector or XYZ goal)
- [ ] Agent ACCEPT → `/bd/planning/goal` present → guidance publishes setpoint only if NAV+yaw available

## Fail cases

- [ ] Kill coordinator process → agent retains last intent; no crash of L0
- [ ] Stale agent status → Swarm Health LIMITED then LOST per aging rules

## Record

Log date, FC firmware, IMU rate, pass/fail per line into `00_docs/ALPHA_LESSONS_LEARNED.md` only when facts exist (not before).
