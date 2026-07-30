cmake_minimum_required(VERSION 3.8)
project(bd_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Setpoint.msg"
  "msg/NavState.msg"
  "msg/Detection.msg"
  "msg/DetectionArray.msg"
  "msg/VisionHealth.msg"
  "msg/FmMode.msg"
  "msg/Heartbeat.msg"
  "msg/Mirror.msg"
  "msg/ImuSample.msg"
  "msg/GnssFix.msg"
  "msg/Actuators.msg"
  "msg/L0Health.msg"
  "msg/ActiveChannel.msg"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
