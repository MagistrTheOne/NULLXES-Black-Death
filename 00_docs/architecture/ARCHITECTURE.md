# NULLXES BLACK DEATH — architecture (surface)

**Date:** 2026-08-13 · Maga  
**Class:** public-surface map. Not NDA pack. Not BOM buy-sheet. Not ADR dump.

```
BLACK DEATH     airframe + SoftBus stack
    CERBER      eyes (detect → track → fusion → WorldFact)
    POSEIDON    specialist facts only
    DMI         decide + TaskOffer / ACCEPT / REJECT
    ATLAS       GSC coordinator (AllocationPlan → DMI)
    L0          ArduPlane inner loop — swarm-blind, weapon-blind
```

One airframe. Two envelopes: **CIVIL** (boot) | **DEFENSE** (`operator_ack`). Same L0.

---

## Data path

```
IMX568 CSI
    → CERBER (ONNX detect/track/fusion)
        → POSEIDON (optional facts)
            → DMI (policy gate → GoalMsg)
                → Guidance
                    → ArduPlaneAdapter (Plane Guided, not Copter velocity)
                        → Pixhawk 6C  ──PWM──► elevons / throttle

GSC (ATLAS + COP + voice TTS)
    → AllocationPlan / envelope_switch
        → DMI executor only
```

Python never PWM. RC > DMI. Companion UART drop → FC RTL/LOITER.

---

## Products

| Module | Runs on | Does | Does not |
|--------|---------|------|----------|
| CERBER | Orin NX | Vision → WorldFact | LLM / cloud |
| POSEIDON | Orin NX | Specialist packs | GuidanceIntent |
| DMI | Orin NX | Offer/claim, mission gate | Inner-loop, MARL |
| ATLAS | GSC host | AllocationPlan | Companion, cameras, fire-control |
| Voice | GSC host | Local ONNX TTS / SAPI | Cloud TTS, onboard mouth |
| L0 | Pixhawk 6C | ArduPlane 4.7.0 | Swarm, weapons |

Weights: NULLXES train → export → sha. Architecture names (YOLO, …) = corpses only.

---

## Flight-1 hardware (practice, not Alpha 5×5)

```
Skywalker X8 PNP
    Pixhawk 6C + M10 + PM          ArduPlane Pixhawk6C
    Jetson Orin NX 16 GB           companion
    IMX568 GS CSI                  /bd/cam/forward
    ASPD-4525 I2C                  airspeed
    ELRS 2.4 CRSF                  TELEM3  (Pocket TX / RP3 RX)
    SiK 915/433                    TELEM1  GSC
    TELEM2 921600 MAVLink2         Orin
    6S                             PM→6C, XT30→NX  (no 5V loop)
```

Firmware kit: `arduiplane/`. BOM: `FLIGHT1_BOM_LOCK.md`.  
Train (after pod up): [CERBER_V3_ATLAS_RUNPOD.md](CERBER_V3_ATLAS_RUNPOD.md).

---

## Envelopes

| | CIVIL | DEFENSE |
|--|-------|---------|
| Boot | default | `operator_ack` |
| Profiles | `mission_profiles/*.yaml` | `mission_profiles/defense/*.yaml` |
| COP | GSC territorial, km-scale | GSC territorial 30–50 km |
| EO camera | metres / tens of metres | same CERBER |
| L0 | identical | identical |

30–50 km ≠ camera range. RID / GNSS integrity = hooks, not a second autopilot.

---

## SoftBus (names only)

| Topic | Who |
|-------|-----|
| `/bd/cam/forward` | CSI |
| `/bd/dmi/world_fact` | CERBER/DMI |
| `/bd/dmi/*` offer/claim | DMI |
| `/bd/goal` → `/bd/plane_cmd` | Guidance → Plane |
| `/bd/mission/envelope` | EnvelopeController |
| `/bd/gsc/territorial_*` | GSC COP |
| `/bd/gsc/voice_cue` | GSC only |

---

## Repo

| Tree | Role |
|------|------|
| `00_docs/` | canon |
| `05_avionics/` | C++ L0 lib (not Flight-1 path) |
| `06_autonomy/` | CERBER / POSEIDON / DMI / ATLAS / SoftBus |
| `07_simulation/` | cerber_studio (vision IDE) · **bd_sim S1 arcade** |
| `08_prototypes/` | practice / X8 test plan |
| `arduiplane/` | Plane 4.7.0 kit |
| `10_tests/` | unit |

Alpha 5×5 geometry locked until Flight-1 lessons. Product 50×50 later. Betas do not reopen Alpha.

---

## Out of this map

Cloud decision path · Hub coordinator LLM · munition bus · jammer/spoof emitter · Copter firmware · F405/F722 · USB-FPV cam · Pixhawk 2.4.8
