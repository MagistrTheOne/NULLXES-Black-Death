# ALPHA 5×5 — Mass breakdown **rev A**

**Status:** rev A · MTOW **design budget** lock **42 кг** · payload **10 кг** (not weighed build)  
**Driver:** battery reallocation after prelim aero estimate (`04_propulsion_energy/energy_storage/ALPHA_5x5_BATTERY.md`)

## 1. Budget

| Группа | Масса (кг) | % MTOW | Комментарий |
|--------|------------|--------|-------------|
| Structure (CFRP + core) | **9,0** | 21,4 % | stiffness-sized; was 14.0 |
| Propulsion (2× main + props + ESC) | **4,0** | 9,5 % | was 4.5 |
| Energy (battery + BMS + wiring) | **16,0** | 38,1 % | 2880 Wh usable @ 180 Wh/kg |
| Avionics + compute A/B | **1,8** | 4,3 % | |
| Sensors | **1,4** | 3,3 % | |
| Landing gear / harness / misc | **0,8** | 1,9 % | |
| Systems margin | **0,0** | 0 % | consumed into battery |
| **Empty + systems (no payload)** | **33,0** | 78,6 % | |
| **Payload** | **10,0** | 23,8 % | locked |
| **MTOW** | **43,0 → clamp** | — | trim **1,0 кг** from structure→ **structure 8,0** OR accept audit |

**Corrected to exact 42.0:**

| Группа | кг |
|--------|-----|
| Structure | **8,0** |
| Propulsion | **4,0** |
| Energy | **16,0** |
| Avionics | **1,8** |
| Sensors | **1,4** |
| LG / misc | **0,8** |
| Margin | **0,0** |
| Payload | **10,0** |
| **Sum** | **42,0** |

## 2. Structure split (8,0 кг)

| Элемент | кг |
|---------|-----|
| Skins | 3,2 |
| Spars / carry-through | 2,4 |
| Ribs / bulkheads | 1,2 |
| Core | 0,8 |
| Hardpoints / LG attach | 0,4 |

## 3. Energy

- Pack 16 kg · 2880 Wh · endurance @ \(V_{md}\) ≈ **2.5 h** (not 6 h — see battery doc)

## 4. Growth

Flutter stiffness may force structure back up → then cut dash capability / range, **not** payload, or raise MTOW via ADR.
