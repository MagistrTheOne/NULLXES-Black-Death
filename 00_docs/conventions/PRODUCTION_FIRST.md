# Production-first policy — NULLXES BLACK DEATH

Never commit: mocks, stubs, dummy weights, fake sensors, random telemetry, placeholder behavior, TODO implementations that invent reality.

If hardware/API/driver/weights are missing: implement only contracts, algorithms, config, docs, build — or return **BLOCKED** with the exact missing dependency.

See also: `06_autonomy/ros2/README.md`, `07_simulation/soft_runtime/README.md`.
