// NULLXES BLACK DEATH — L0 inner-loop (C++17)
// dt design: 0.002 s (500 Hz). No Python in this loop.

#pragma once

struct Setpoint {
  double roll_rad{0};
  double pitch_rad{0};
  double yaw_rate_rps{0};
  double thrust_norm{0};
  bool valid{false};
};

struct ImuSample {
  double gyro_rps[3]{};
  double accel_mps2[3]{};
  double stamp_s{0};
};

struct ActuatorCmd {
  double elevon_left{0};
  double elevon_right{0};
  double motor_main[2]{};
};

class InnerLoop {
 public:
  static constexpr double kDtNominal = 0.002;

  ActuatorCmd step(const Setpoint& sp, const ImuSample& imu, double dt_s);
  void set_hold_attitude();

 private:
  Setpoint last_good_{};
  bool hold_mode_{false};
  double integ_roll_{0};
  double integ_pitch_{0};
  double kp_att_{2.5};
  double kp_rate_{0.15};
  double kd_rate_{0.01};
  double kp_yaw_{0.2};
  double idle_thrust_{0.05};
};
