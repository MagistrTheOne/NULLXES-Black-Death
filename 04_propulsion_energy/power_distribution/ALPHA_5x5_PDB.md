# ALPHA 5×5 — Power distribution

```
[Battery 12S]──┬── BMS ──┬── ESC_L (main 1)
               │         ├── ESC_R (main 2)
               │         ├── DC-DC 12/5V ── Compute A
               │         └── DC-DC 12/5V ── Compute B
               └── sense / precharge
```

| Rule | Spec |
|------|------|
| Compute rails | **dual independent** DC-DC from pack; loss of one rail ≠ loss of other |
| ESC feeds | separate breakers; one ESC fail isolates that motor |
| L0 power | from both rails OR diode-OR so inner-loop survives single DC-DC loss |
| Ground | single-point chassis near battery; star for avionics |

HV wiring mass included in energy group.
