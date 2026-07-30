#include "inner_loop.hpp"

#include <algorithm>
#include <cmath>

namespace {

double clamp(double v, double lo, double hi) {
  return std::max(lo, std::min(hi, v));
}

}  // namespace

ActuatorCmd InnerLoop::step(const Setpoint& sp, const ImuSample& imu, double dt_s) {
  Setpoint use = sp.valid ? sp : last_good_;
  if (sp.valid) {
    last_good_ = sp;
    hold_mode_ = false;
  }

  // Gyro feedback (body rates): indices 0=x(roll), 1=y(pitch), 2=z(yaw)
  const double p = imu.gyro_rps[0];
  const double q = imu.gyro_rps[1];
  const double r = imu.gyro_rps[2];

  // Simple cascaded-ish: angle error → rate cmd → surface
  const double roll_err = use.roll_rad - integ_roll_;
  const double pitch_err = use.pitch_rad - integ_pitch_;
  // Integrate attitude from gyro (crude; replace with complementary/EKF on FC)
  integ_roll_ += p * dt_s;
  integ_pitch_ += q * dt_s;

  const double roll_rate_cmd = clamp(kp_att_ * roll_err, -2.0, 2.0);
  const double pitch_rate_cmd = clamp(kp_att_ * pitch_err, -2.0, 2.0);
  const double yaw_rate_cmd = use.yaw_rate_rps;

  const double roll_u = kp_rate_ * (roll_rate_cmd - p) + kd_rate_ * (-p);
  const double pitch_u = kp_rate_ * (pitch_rate_cmd - q) + kd_rate_ * (-q);
  const double yaw_u = kp_yaw_ * (yaw_rate_cmd - r);

  ActuatorCmd cmd;
  // Elevons: pitch common, roll differential
  cmd.elevon_left = clamp(pitch_u + roll_u, -1.0, 1.0);
  cmd.elevon_right = clamp(pitch_u - roll_u, -1.0, 1.0);
  const double yaw_mix = clamp(yaw_u, -0.25, 0.25);
  const double t = clamp(use.thrust_norm, 0.0, 1.0);
  cmd.motor_main[0] = clamp(t - yaw_mix, 0.0, 1.0);
  cmd.motor_main[1] = clamp(t + yaw_mix, 0.0, 1.0);

  if (hold_mode_) {
    cmd.elevon_left = clamp(-kp_rate_ * p, -0.3, 0.3);
    cmd.elevon_right = clamp(-kp_rate_ * q, -0.3, 0.3);
    cmd.motor_main[0] = cmd.motor_main[1] = idle_thrust_;
  }
  return cmd;
}

void InnerLoop::set_hold_attitude() {
  hold_mode_ = true;
  last_good_.valid = false;
}
