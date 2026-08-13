# BLACKBOX soak — Stability Gate

Target: 60 minute JUST FLY.

```
cd 07_simulation/cerber_studio
python tests/soak/run_soak.py --minutes 60 --seed 1947 --region random
```

Fixed profile inside the harness:

- TOD 16:30
- Time Flow 4x
- Activity ON
- Recording ON
- CERBER ON (`--no-cerber` to skip worker)
- Music ON (`--no-music` to skip mixer)

Quick harness check (not the gate):

```
python tests/soak/run_soak.py --minutes 0.5 --no-cerber --no-music --region forest
```

Report:

`~/.nullxes/cerber_studio/soak/last.yaml`

Acceptance:

- no crash
- no audio dropout
- no simulation spiral
- no duplicate activity
- no disappearing discovered POI
- no recorder corruption
- replay reaches final state
- RAM does not continuously grow
