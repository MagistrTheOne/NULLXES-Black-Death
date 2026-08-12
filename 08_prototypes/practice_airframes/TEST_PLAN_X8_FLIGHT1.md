# TEST PLAN — Skywalker X8 PNP Flight-1 (~2026-09)

**Platform:** Skywalker X8 PNP + Pixhawk 6C + Orin NX 16GB  
**BOM:** `00_docs/architecture/FLIGHT1_BOM_LOCK.md`  
**Not:** Alpha 5×5. Not F405/F722. Not USB camera.

## Ground (props restrained)

- [ ] CG with NX+cam+6S as flown
- [ ] Elevon / throttle direction on 6C MAIN OUT
- [ ] Airspeed zero + pitot leak check (`ARSPD_TYPE=1`)
- [ ] M10 3D fix, compass ≥10 cm from ESC
- [ ] ELRS failsafe = RTL/LOITER, not continue
- [ ] TELEM2 921600 MAVLink2 to NX; TELEM1 = GSC only
- [ ] NX on own 6S DC; FC 5V unused by NX
- [ ] IMX568 CSI → `/bd/cam/forward` ≥30 fps GS
- [ ] `ArduPlaneAdapter` Guided goto on bench (no Copter velocity)
- [ ] Companion UART drop → FC RTL/LOITER without Python

## Autonomy (still props-off)

- [ ] Real IMU → L0 hold
- [ ] GNSS → `/bd/nav/ekf` (no fake fix)
- [ ] DMI ACCEPT → GoalMsg → Plane Guided
- [ ] REJECT does not advance mission
- [ ] Envelope boot CIVIL; DEFENSE only with `operator_ack`

## First hop (civil envelope)

- [ ] Manual CTOL, then FBWA, then AUTO/Guided inside agreed box
- [ ] RC override always wins
- [ ] Abort: throttle cut + RTL documented before hop

## Exit

Bus + Plane Guided + CSI frame + DMI intent proven on X8 ground then short hop. Mass/power logged. Lessons = facts only.
