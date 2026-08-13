# arduiplane — Flight-1 firmware kit (local)

**HW:** none yet. This folder is the flash/param reference for Pixhawk 6C when the board arrives.  
**Not** Copter. **Not** SITL binary. Python stack stays in `06_autonomy/l0_bridge`.

| File | Role |
|------|------|
| `arduplane.apj` | ArduPlane **4.7.0** `Pixhawk6C` (board_id **56**, git `1511f271`) |
| `MissionPlanner-latest.msi` | GCS 1.3.9384.38258 |
| `pixhawk6c_x8.parm` | X8 elevon + TELEM2 + ELRS CRSF + pitot + MAV3 streams |
| `features.txt` | Compile flags of this exact APJ |
| `capabilities.json` | Flight-1 slice of those flags + UART map |
| `params_ref.json` | 4.7 pdef slice for locked params |
| `MANIFEST.json` | sha256 / board_id lock |
| `verify_firmware.py` | inspect kit without FC |
| `extract_from_kit.py` | rebuild json from features.txt + `_apm.pdef.json` |

```text
python arduiplane/extract_from_kit.py
python arduiplane/verify_firmware.py
python 06_autonomy/tools/flight1_bench_chain.py
```

**Pulled (no FC):** UART map, MS4525/CRSF/Guided compiled IN, OpenDroneID and GUIDED_NOGPS compiled OUT, 4.7 rename `GUID_TIMEOUT`→`GUIDED_TIMEOUT`, `SRn`→`MAVn`.

**Not worth pulling:** MSI DLLs, `aircraft.xml` (3DR copters), `ParameterFactMetaData.xml` (UAVCAN ESC), `arduplane.elf`/`.hex` (flash uses `.apj`).

## Flash (when 6C is on USB)

1. Install MSI → Mission Planner  
2. SETUP → Install Firmware → **Load custom firmware** → `arduplane.apj`  
3. Connect → Config/Tuning → Full Parameter List → Load `pixhawk6c_x8.parm` → Write  
4. Calibrate IMU / compass / airspeed zero / radio. Do not skip pitot.

## UART lock (same as BOM)

| Port | SERIAL | Protocol |
|------|--------|----------|
| TELEM1 | 1 | MAVLink2 GSC |
| TELEM2 | 2 | MAVLink2 Orin 921600, RTSCTS off |
| GPS1 | 3 | M10 |
| TELEM3 | 5 | ELRS CRSF (`23`) |

Python never PWM. Adapter: `ArduPlaneAdapter` → `MISSION_ITEM_INT` current=2. Copter velocity = reject.

Physical assembly filter (Copter wiki → X8/6C): `ASSEMBLY.md`.
