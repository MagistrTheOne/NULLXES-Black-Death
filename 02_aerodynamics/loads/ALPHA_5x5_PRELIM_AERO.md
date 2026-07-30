# ALPHA 5×5 — Preliminary aero & power

**Status:** DESIGN ESTIMATE analytic v0 — **not** XFOIL/XFLR5/flight data.  
**Pending:** real polars via `scripts/run_xfoil_polars.py` + XFLR5 per `scripts/build_xflr5_notes.md`.  
**Locks:** \(b=5\) м, \(S=20\) м², \(AR=1.25\), MTOW 42 кг, \(V=27.8\) м/с (100 км/ч)

## 1. Assumptions

| Symbol | Value |
|--------|-------|
| \(\rho\) | 1.225 kg/m³ (ISA SL) |
| \(W\) | \(42 \times 9.81 = 411.8\) N |
| \(e\) (Oswald) | **0.65** (low-AR BWB, conservative) |
| \(C_{D0}\) | **0.028** (thick centerbody + exposed gear/props) |
| \(\eta_{prop}\) | 0.70 |
| \(\eta_{motor}\) | 0.85 |
| \(\eta_{total}\) | \(0.70\times0.85=0.595\) |

\[
C_L=\frac{W}{qS},\quad
C_{Di}=\frac{C_L^2}{\pi\,AR\,e},\quad
C_D=C_{D0}+C_{Di},\quad
D=q S C_D,\quad
P_{aero}=D V,\quad
P_{elec}=P_{aero}/\eta_{total}
\]

## 2. Cruise @ 100 km/h

| Qty | Value |
|-----|-------|
| \(q\) | 473.4 Pa |
| \(qS\) | 9467 N |
| \(C_L\) | **0.0435** |
| \(C_{Di}\) | 0.00074 |
| \(C_D\) | **0.0287** |
| \(L/D\) | **1.51** |
| \(D\) | 272 N |
| \(P_{aero}\) | **7560 W** |
| \(P_{elec}\) | **12706 W** |

Cruise @ 100 km/h is **power-hostile** at AR=1.25 (parasite-dominated, terrible L/D).

## 3. Best L/D (endurance / loiter)

\[
C_{L,opt}=\sqrt{C_{D0}\,\pi\,AR\,e}=\sqrt{0.028\times\pi\times1.25\times0.65}=0.267
\]

| Qty | Value |
|-----|-------|
| \((L/D)_{max}\) | **4.77** |
| \(V_{md}\) | \(\sqrt{2W/(\rho S C_{L,opt})}=**8.0\) м/с** (28.7 km/h) |
| \(P_{aero,min}\) | \(W V/(L/D)=**690\) W** |
| \(P_{elec,md}\) | **1160 W** |

## 4. Energy vs 6 h requirement

| Case | \(P_{elec}\) | \(E(6h)\) | \(m_{batt}@180\) Wh/kg |
|------|--------------|-----------|-------------------------|
| Cruise 100 km/h | 12.7 kW | 76.2 kWh | **423 kg** (impossible @ MTOW 42) |
| Best L/D loiter | 1.16 kW | 6.96 kWh | **38.7 kg** (still > MTOW budget) |
| Budget battery 8.5 kg | — | 1.53 kWh available | endurance @ \(P_{md}\): **1.32 h** |

**Decision (locked process):** reallocate mass toward battery (rev A mass breakdown) for max achievable endurance at \(V_{md}\); **PE-05 6 h at AR=1.25 is not met** without raising AR / cutting \(C_{D0}\) via CFD / raising MTOW. Alpha flight program uses **endurance_mode = \(V_{md}\)** and reports **E_ach ≈ battery Wh / 1160 W**.

With max reallocation battery **16.0 kg** → 2.88 kWh → **≈2.5 h** @ best L/D (see mass rev A).

## 5. Thrust check @ cruise

\(T_{req}=D=272\) N @ 100 km/h. Static thrust lock ≥226 N is for takeoff; cruise thrust capability must cover 272 N → motors sized with continuous power ≥ \(P_{elec}/2\) each ≈ **6.4 kW** if forced to cruise 100 km/h, **or** mission profile uses slow cruise.  

**Alpha propulsion lock adjustment for physics:** keep hardware floor **≥1.2 kW cont each** for CTOL/climb margin at low speed; **mission cruise for energy = \(V_{md}\)–50 km/h band**; 100 km/h is dash, not endurance.

@ 50 km/h (13.9 m/s): \(C_L=0.174\), \(C_D=0.0335\), \(D=79\) N, \(P_{aero}=1100\) W, \(P_{elec}=1850\) W → with 16 kg batt (2.88 kWh) endurance **≈1.6 h**.

## 6. XFLR5

Replace §2–3 numbers after running workflow in `scripts/build_xflr5_notes.md`.
