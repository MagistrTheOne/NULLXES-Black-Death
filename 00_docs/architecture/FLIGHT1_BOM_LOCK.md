# FLIGHT-1 BOM Lock

**Status:** LOCKED · 2026-08-13 · Maga  
**Carrier:** Skywalker X8 PNP (practice / integration airframe, not Alpha 5×5)  
**SDK:** ArduPilot Plane + pymavlink TELEM2 → SoftBus (`ArduPlaneAdapter`)  
**Not:** F405 / F722 / Betaflight / USB-FPV cam

| Item | Locked value | Notes |
|------|----------------|-------|
| Airframe | **Skywalker X8 PNP** 2120–2122 mm | Motor + ESC + servos in PNP. Do not add a second ESC stack. |
| FC | **Holybro Pixhawk 6C** + Holybro power module | Firmware **ArduPlane V4.7.0 stable** target `Pixhawk6C`. TELEM2 = companion. |
| GNSS | **Holybro M10** (kit with 6C) | GPS1 port. Compass ≥10 cm from ESC. ArduPilot ≥4.3. |
| Companion SoM | **Jetson Orin NX 16GB** | CERBER/DMI Python. ATLAS/voice stay GSC. |
| UAV carrier | CSI + UART + NVMe + 6S-class input | Allowed: WeAct N006 or Auvidea JNX110 / Rebotnix Blade. Pick one at PO. |
| Camera | **IMX568 global-shutter CSI** (e-CAM56_CUONX class) | No USB for flight. M12, **70–90° H** forward. |
| Airspeed | Digital pitot (ASPD-4525 / MS4525DO class) | I2C. `ARSPD_TYPE=1`. Required for Plane. |
| RC | **ExpressLRS 2.4 GHz** CRSF UART | TX: RadioMaster Pocket (internal ELRS 2.4). RX: RadioMaster **RP3** diversity. Not Pixhawk 2.4.8. Not RCIN/SBUS. |
| Telemetry GSC | **SiK 915/433** on **TELEM1** | Not 2.4 (ELRS already owns 2.4). Companion owns **TELEM2**. |
| Battery | **6S** Li-ion/LiPo, dedicated PM to FC, dedicated DC to NX | No 5V loop FC↔NX. Common GND only. |
| Companion power | **15–25 W cruise** (`nvpmodel`); 40W Super = bench/sprint | Active cooler required. |
| Avionics mass | **≤ 800 g** (NX+carrier+cam+cool+FC+GPS+pitot) | X8 payload 1–2 kg. Weigh before first hop. |
| GPL on image | OPEN | OpenVINS vs Basalt — not this freeze. VIO not required for Flight-1 hop. |

## Wire (locked)

```text
6S pack ──► Holybro PM ──► Pixhawk 6C POWER
      └──► carrier XT30/DC ──► Orin NX 16GB

PNP ESC signal ──► 6C MAIN OUT (throttle)
PNP servos     ──► 6C MAIN OUT (elevons)

M10 GPS        ──► 6C GPS1
ASPD-4525      ──► 6C I2C
ELRS RX        ──► 6C TELEM3 (SERIAL5 CRSF)
                   6C TX → RX ELRS, 6C RX → TX ELRS, 5V, GND
                   pins 4–5 unused (some SN = I2C, do not wire ELRS there)
GSC SiK        ──► 6C TELEM1

6C TELEM2 TX/RX/GND ──► carrier UART  (MAVLink2, 921600)
                         SERIAL2_PROTOCOL=2
                         SERIAL2_BAUD=921
                         BRD_SER2_RTSCTS=0

IMX568 CSI ──► carrier CSI ──► OpenCV/V4L2 ──► /bd/cam/forward
```

Python never PWM. Companion loss → FC RTL/LOITER. RC always wins.

## Firmware (locked)

Wrong page: [Copter firmware appendix](https://ardupilot.org/copter/docs/common-downloads_firmware.html) = APM 2.x corpses. Do not flash Copter, Rover, or `latest`.

| What | File |
|------|------|
| Autopilot | [arduplane.apj](https://firmware.ardupilot.org/Plane/stable/Pixhawk6C/arduplane.apj) |
| Folder | https://firmware.ardupilot.org/Plane/stable/Pixhawk6C/ |
| Version | **ArduPlane V4.7.0** official (`4.7.0-FIRMWARE_VERSION_TYPE_OFFICIAL`, 2026-07-21) |
| GCS | [MissionPlanner-latest.msi](https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi) |
| Flash | MP → SETUP → Install Firmware → **Load custom firmware** → `arduiplane/arduplane.apj` |
| Local kit | `arduiplane/` — APJ + MSI + `pixhawk6c_x8.parm` + `MANIFEST.json` |
| Verify (no FC) | `python arduiplane/verify_firmware.py` |

Do not use: Copter `Pixhawk6C`, Plane `latest`, Custom Firmware Build Server, APM2 zip from that wiki page. 6C has flash; stock Plane stable is enough. After flash: load `pixhawk6c_x8.parm` (elevon 77/78 + throttle 70), then SERIAL2 as in Wire.

## Buy links (verified 2026-08-13)

| What | URL |
|------|-----|
| X8 PNP | https://www.uavmodel.com/products/skywalker-x8-2122mm-uav-fixed-wing |
| Pixhawk 6C | https://holybro.com/products/pixhawk-6c |
| 6C ports | https://docs.holybro.com/autopilot/pixhawk-6c/pixhawk-6c-ports |
| ArduPilot 6C | https://ardupilot.org/copter/docs/common-holybro-pixhawk6c.html |
| Plane Guided | https://ardupilot.org/dev/docs/plane-commands-in-guided-mode.html |
| Companion UART | https://ardupilot.org/dev/docs/raspberry-pi-via-mavlink.html |
| Orin | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ |
| N006 carrier | https://www.cnx-software.com/2026/06/30/weact-n006-a-compact-nvidia-jetson-orin-nx-carrier-board-designed-for-robots-and-uavs/ |
| IMX568 CSI | https://www.e-consystems.com/camera-modules/5mp-sony-pregius-imx568-global-shutter-camera-module.asp |
| ASPD-4525 | https://www.lumenier.com/products/matek-digital-airspeed-sensor-aspd-4525 |
| ELRS TX | RadioMaster Pocket ELRS 2.4 (internal) |
| ELRS RX | RadioMaster RP3 2.4 diversity UART |
| ELRS+AP | https://www.expresslrs.org/quick-start/ardupilot-setup/ |

## Still pick at PO (not architecture)

Exact X8 colour/KIT vs PNP-Advanced · carrier SKU among the three allowed · M12 lens SKU inside 70–90° H · 6S capacity (start 5000–6500 mAh bench, 16–22 Ah endurance). RC TX/RX locked: Pocket + RP3 2.4.

Matek H743-WING V3 is **superseded** for this freeze (OEM page gone). Do not mix H743 leftovers with 6C on the same airframe.
