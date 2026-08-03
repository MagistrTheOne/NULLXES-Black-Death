# CERBER RT — Fault / proximity thresholds

**Status:** defaults pre-HW — **lock numbers after robot inventory**  
**Canon:** [CERBER_RT.md](../../00_docs/architecture/CERBER_RT.md)

| Mode | Enter when | Action |
|------|------------|--------|
| NOMINAL_CRAWL | cams OK, ORT OK, range OK, `d_min ≥ D_SLOW`, no bumper | ≤ `V_CRAWL` |
| SLOW | `D_STOP ≤ d_min < D_SLOW` | speed cap reduced |
| SAFE_STOP | `d_min < D_STOP` OR bumper OR critical cam/ORT/range loss | zero cmd; L0 latch |
| HOLD | operator / HW e-stop | no motion |

## Numeric trips (defaults)

| Signal | Trip |
|--------|------|
| `D_STOP` | **0.35 m** |
| `D_SLOW` | **0.80 m** |
| `V_CRAWL` (demo) | **≤ 0.15 m/s** |
| Setpoint stale (L0) | **200 ms** → STOP |
| Detect conf (publish) | **0.35** |
| ONNX sha256 mismatch | fail-closed → SAFE_STOP (no boxes) |
| QR decode | best-effort; never blocks STOP path |

Civil indoor only. No external API required for any mode.
