"""Soft-bus message dataclasses (mirror of bd_interfaces ROS msgs)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Setpoint:
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rate_rps: float = 0.0
    thrust_norm: float = 0.0
    valid: bool = False
    stamp_s: float = 0.0


@dataclass
class NavStateMsg:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    yaw: float = 0.0
    stamp_s: float = 0.0


@dataclass
class Detection:
    cls_id: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    track_id: int = -1


@dataclass
class DetectionArray:
    detections: list[Detection] = field(default_factory=list)
    camera: str = "forward"
    stamp_s: float = 0.0


@dataclass
class TrackMsg:
    track_id: int
    cls_id: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    age: int = 0
    hits: int = 0


@dataclass
class TrackArray:
    tracks: list[TrackMsg] = field(default_factory=list)
    camera: str = "forward"
    stamp_s: float = 0.0


@dataclass
class SceneAlert:
    severity: str  # info | warn | critical
    kind: str
    fact_id: str
    summary: str


@dataclass
class SceneAssessment:
    stamp_s: float
    summary: str
    alerts: list[SceneAlert] = field(default_factory=list)
    suggested_intent_kind: str = "ALERT_ONLY"
    link_ok: bool = True


@dataclass
class PoseidonPackStatus:
    pack_id: str
    latency_ms: float
    n_dets: int = 0


@dataclass
class PoseidonActivePacks:
    packs: list[PoseidonPackStatus] = field(default_factory=list)
    stamp_s: float = 0.0


@dataclass
class VisionHealth:
    """Pessimistic defaults — healthy must come from a real publisher."""

    vision_ok: bool = False
    cams_alive: int = 0
    detail: str = ""
    stamp_s: float = 0.0


@dataclass
class FmMode:
    mode: str = "SAFE_LOITER"
    stamp_s: float = 0.0


@dataclass
class HeartbeatMsg:
    channel_id: str
    seq: int
    healthy: bool = True
    stamp_s: float = 0.0


@dataclass
class MirrorMsg:
    stamp_s: float
    channel_id: str
    active: bool
    mission_mode: str
    health_flags: dict[str, bool] = field(default_factory=dict)
    nav: NavStateMsg = field(default_factory=NavStateMsg)
    setpoint_hash: str = ""


@dataclass
class ImuMsg:
    """accel_mps2: linear acceleration ENU [m/s^2], gravity removed by driver."""

    gyro_rps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    accel_mps2: tuple[float, float, float] = (0.0, 0.0, 0.0)
    stamp_s: float = 0.0


@dataclass
class GnssFix:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    fix_ok: bool = False
    stamp_s: float = 0.0


@dataclass
class Actuators:
    elevon_left: float = 0.0
    elevon_right: float = 0.0
    motor_main: tuple[float, float] = (0.0, 0.0)
    stamp_s: float = 0.0


@dataclass
class L0Health:
    """Pessimistic defaults — healthy must come from a real publisher."""

    esc_ok: bool = False
    imu_ok: bool = False
    bus_ok: bool = False
    stamp_s: float = 0.0


@dataclass
class ImageMsg:
    """BGR uint8 HWC image on soft bus (not ROS Image)."""

    bgr: object  # np.ndarray
    camera: str = "forward"
    stamp_s: float = 0.0


@dataclass
class ActiveChannel:
    channel_id: str = "A"
    stamp_s: float = 0.0


@dataclass
class GoalMsg:
    """Mission goal — no invented cruise altitude; set by planner/operator."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    stamp_s: float = 0.0


@dataclass
class TrackTarget:
    """Civil chase/escort/deny target in ENU — presence geometry only (ADR-004)."""

    track_id: int
    mode: str  # chase | escort | deny
    x: float
    y: float
    z: float
    cls_id: int = -1
    conf: float = 0.0
    stamp_s: float = 0.0


# Canon topic constants
TOPIC_SETPOINT = "/bd/l0/setpoint"
TOPIC_ACTIVE = "/bd/dual/active"
TOPIC_FM_MODE = "/bd/fm/mode"
TOPIC_IMU = "/bd/l0/imu"
TOPIC_ACTUATORS = "/bd/l0/actuators"
TOPIC_L0_HEALTH = "/bd/l0/health"
TOPIC_CAM_FORWARD = "/bd/cam/forward"
TOPIC_CAM_DOWN = "/bd/cam/down"
TOPIC_CAM_LEFT = "/bd/cam/left"
TOPIC_CAM_RIGHT = "/bd/cam/right"
TOPIC_LIDAR = "/bd/lidar/scan"
TOPIC_GNSS = "/bd/gnss/fix"
TOPIC_NAV = "/bd/nav/state"
TOPIC_DETECTIONS = "/bd/vision/detections"
TOPIC_VISION_HEALTH = "/bd/vision/health"
TOPIC_TRACKS = "/bd/vision/tracks"
TOPIC_SCENE = "/bd/vision/scene"
TOPIC_POSEIDON_DETECTIONS = "/bd/poseidon/detections"
TOPIC_POSEIDON_ACTIVE = "/bd/poseidon/active_packs"
TOPIC_HB_A = "/bd/dual/heartbeat_A"
TOPIC_HB_B = "/bd/dual/heartbeat_B"
TOPIC_MIRROR = "/bd/dual/mirror"
TOPIC_GOAL = "/bd/planning/goal"
TOPIC_BATTERY_SOC = "/bd/power/battery_soc"
TOPIC_TRACK_TARGET = "/bd/guidance/track_target"
