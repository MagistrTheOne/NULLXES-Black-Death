# Build Alpha L0 (avionics)

Flight artifact is the **library** `bd_inner_loop` only.

```bash
cd "05_avionics/flight_software"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Host compile smoke (synthetic I/O, not flight): `99_tools/host/l0_smoke_main.cpp` — link against `bd_inner_loop` separately if needed.

Requires CMake + C++17 compiler on PATH.
