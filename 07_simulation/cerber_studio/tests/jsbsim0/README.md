# JSBSIM-0

Headless FDM contract. No Panda, no CERBER, no operations.

```
cd 07_simulation/cerber_studio
python tests/jsbsim0/run_jsbsim0.py
```

Checks:

- initialize
- set controls
- 200 fixed-dt steps
- retrieve VehicleState in BLACKBOX ENU
- reset
- shutdown

If `jsbsim` is not installed the runner uses the NED kinematic stand-in behind `FrameAdapter`. Product flight stays on ArcadeBackend until JSBSIM-1.
