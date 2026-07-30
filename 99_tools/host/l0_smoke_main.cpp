// Host-only smoke for InnerLoop library.
// NOT flight software. Synthetic setpoint/IMU for compile/link check only.
#include "inner_loop.hpp"

#include <cstdio>

int main() {
  InnerLoop loop;
  Setpoint sp;
  sp.roll_rad = 0.05;
  sp.pitch_rad = 0.02;
  sp.yaw_rate_rps = 0.0;
  sp.thrust_norm = 0.4;
  sp.valid = true;
  ImuSample imu{};
  ActuatorCmd cmd = loop.step(sp, imu, InnerLoop::kDtNominal);
  std::printf("elevon L/R=%.3f/%.3f motors=%.3f/%.3f\n", cmd.elevon_left,
              cmd.elevon_right, cmd.motor_main[0], cmd.motor_main[1]);
  return 0;
}
