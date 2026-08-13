# Assembly — what to take from ArduPilot wiki

Copter index ([autopilot-assembly-instructions](https://ardupilot.org/copter/docs/autopilot-assembly-instructions.html)) is the wrong vehicle. Use **Plane** `common-*` pages. Flight-1 = Skywalker X8 PNP + Pixhawk 6C. PNP already has motor/ESC/servos.

| Wiki section | Need? | Flight-1 lock |
|--------------|-------|----------------|
| [Mounting](https://ardupilot.org/plane/docs/common-mounting-the-flight-controller.html) | **YES** | 6C in fuselage bay, **arrow forward**, near CG, 4× foam cubes. `AHRS_ORIENTATION=0`. Calibrate accel **after** orientation. |
| Autopilot Wiring | **YES, not that page** | Holybro [6C ports](https://docs.holybro.com/autopilot/pixhawk-6c/pixhawk-6c-ports) + `FLIGHT1_BOM_LOCK.md` Wire. Copter quad diagram = reject. |
| NAVIO2 Wiring | **NO** | Linux-as-FC. We are Pixhawk + Orin companion. |
| ESCs and Motors | **NO (Copter)** | Do not do motor order / 4-in-1 / prop direction matrix. PNP: **one** ESC signal → MAIN OUT 3 (`SERVO3_FUNCTION=70`). Elevons MAIN 1/2 (`77`/`78`). No second ESC. |
| [GPS+Compass](https://ardupilot.org/plane/docs/common-installing-3dr-ublox-gps-compass-module.html) | **YES** | Holybro **M10 → GPS1** (not DF13 Pixhawk1 split GPS+I2C). Arrow forward, mast, **≥10 cm from ESC/6S/NX**. Compass cal in MP. GPS baud ignored — driver sets it. |
| [Vibration Damping](https://ardupilot.org/plane/docs/common-vibration-damping.html) | **YES (short)** | Foam under 6C. After first hop: IMU vibe in MP. Soft-mount NX separately so 40 W fan does not shake IMU. |
| [Magnetic Interference](https://ardupilot.org/plane/docs/common-magnetic-interference.html) | **YES** | Twist 6S/ESC power. Compass on mast. NX + PM are DC magnets — not next to M10. GPS-for-yaw later, not Flight-1 hop. |

## Not on that Copter list — still mandatory

| Item | Do |
|------|-----|
| Pitot | ASPD-4525 I2C. Tube out of prop wash. `ARSPD_TYPE=1`. Zero on ground. |
| ELRS | **TELEM3 / SERIAL5** CRSF (`PROTOCOL=23`). Not 6C RCIN pin (SBUS/PPM only). |
| GSC radio | TELEM1 SiK 915/433. Not 2.4. |
| Orin | TELEM2 TX/RX/GND, 921600, RTSCTS off. Own 6S DC. Common GND only. |
| PM | Holybro PM → 6C POWER. NX never from FC 5V. |

## I/O from [common-flight-controller-io](https://ardupilot.org/copter/docs/common-flight-controller-io.html) → Pixhawk 6C

6C has **IOMCU**: MAIN = IO coprocessor (RC-redundant), AUX = FMU. Elevons/throttle on **MAIN**. Pinout: [holybro 6C ports](https://docs.holybro.com/autopilot/pixhawk-6c/pixhawk-6c-ports).

| Wiki type | Flight-1 | 6C port |
|-----------|----------|---------|
| USB SERIAL0 | Flash / MP USB | USB-C |
| UART TELEM1 | GSC SiK | TELEM1 UART7, RTSCTS ok for SiK |
| UART TELEM2 | Orin MAVLink2 921600 | TELEM2 UART5, **RTSCTS off**, TX↔RX |
| UART TELEM3 | **ELRS 2.4 CRSF** | TELEM3 USART2. Wire VCC/TX/RX/GND only. Pins 4–5 NC (some SN = I2C — do not put ELRS there) |
| GPS | M10 | GPS1 (UART+I2C compass in one plug) |
| I2C | ASPD-4525 | I2C port. Pull-ups on 6C — no extra 2k |
| PMU | Holybro analog PM | POWER1. CUR/VLT analog. `BATT_MONITOR=4` |
| RCIN / PPM/SBUS / DSM | **unused** | ELRS is not SBUS. CRSF needs UART. |
| MAIN OUT | elevon L/R + throttle | IO_CH1=77, CH2=78, CH3=70. Servo rail from PNP BEC |
| AUX OUT | unused Flight-1 | FMU, DShot capable — not needed |
| CAN / SPI / analog RSSI | unused | RSSI from CRSF (`RSSI_TYPE=3`), not analog pin 103 |
| Safety SW / buzzer | kit GPS1 already carries SW+LED+buzzer | leave on M10 cable |

TX↔RX always crossed. 6C UART is 3.3 V; ELRS 5 V VCC from TELEM3 pin1 is ok, data is 3.3.

## 2.4 GHz radio (not the FC)

**Pixhawk 2.4.8 is an old board name. Not 2.4 GHz. Do not buy it.**

| Role | Lock | Band |
|------|------|------|
| Pilot RC | ExpressLRS CRSF | **2.4 GHz** |
| TX | RadioMaster Pocket internal ELRS 2.4 + EdgeTX | 2.4 |
| RX | RadioMaster **RP3** diversity, UART | 2.4 |
| GSC / Mission Planner | Holybro SiK | **915 or 433**, TELEM1 |

Same bind phrase TX↔RX. Packet rate 250 Hz enough for Plane. Setup: [ELRS ArduPilot](https://www.expresslrs.org/quick-start/ardupilot-setup/) — `SERIAL5_PROTOCOL=23`, `RSSI_TYPE=3`, `RC_OPTIONS=8704` (bit9 suppress + bit13 420k).

Canon: `pixhawk6c_x8.parm`. Python never PWM.
