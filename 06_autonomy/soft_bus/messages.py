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
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    frame_id: str = "enu"
    cov_xx: float = 1.0e6
    cov_yy: float = 1.0e6
    cov_zz: float = 1.0e6
    source: str = "fc"  # fc | vio | fused


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
    trace_id: str = ""


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
    trace_id: str = ""


@dataclass
class TraceSpan:
    """One stage in an end-to-end autonomy trace (TRACE_SPEC)."""

    trace_id: str
    span_id: str
    stage: str
    status: str = "ok"  # ok | degrade | error | skip
    t_start_ns: int = 0
    t_end_ns: int = 0
    parent_span_id: str = ""
    detail: str = ""
    attrs: dict[str, str] = field(default_factory=dict)


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
class ConceptHit:
    """POSEIDON-VE open-vocab hit (product model = POSEIDON-VE-*)."""

    object_id: str
    track_id: int
    concept: str
    score: float
    source: str = "poseidon_ve"
    model: str = "POSEIDON-VE-01"
    emb_dim: int = 0
    stamp_ns: int = 0
    trace_id: str = ""
    reranker: str = ""


@dataclass
class ConceptHitArray:
    hits: list[ConceptHit] = field(default_factory=list)
    stamp_s: float = 0.0
    trace_id: str = ""


@dataclass
class SceneFactObject:
    object_id: str
    role: str = "subject"
    concept: str = ""
    score: float = 0.0


@dataclass
class SceneFactRelation:
    kind: str
    subject_id: str
    object_id: str
    confidence: float = 0.0


@dataclass
class SceneFactEvent:
    kind: str
    confidence: float = 0.0


@dataclass
class SceneFact:
    """POSEIDON-VL structured scene semantics — never GuidanceIntent."""

    scene_id: str
    stamp_ns: int = 0
    trace_id: str = ""
    source: str = "poseidon_vl"
    model: str = "POSEIDON-VL-01"
    scene_type: str = ""
    summary: str = ""
    objects: list[SceneFactObject] = field(default_factory=list)
    relations: list[SceneFactRelation] = field(default_factory=list)
    events: list[SceneFactEvent] = field(default_factory=list)
    validity: bool = False
    hallucination_flags: list[str] = field(default_factory=list)
    budget_ms_used: float = 0.0


@dataclass
class WorldDelta:
    """POSEIDON-FW next-state prediction — DMI only, never Guidance."""

    delta_id: str
    parent_trace_id: str = ""
    action_id: str = ""
    model: str = "POSEIDON-FW-GSC"
    horizon_s: float = 5.0
    predicted_summary: str = ""
    risk_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    validity: bool = False
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
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    frame_id: str = "body"


@dataclass
class GnssFix:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    fix_ok: bool = False
    stamp_s: float = 0.0
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    frame_id: str = "enu"
    hdop: float = 99.0


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
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    frame_id: str = "cam_forward"
    seq: int = 0
    trace_id: str = ""


@dataclass
class CalibActiveMsg:
    """Active calibration file hashes — fail-closed if empty/mismatch."""

    camera_hash: str = ""
    imu_hash: str = ""
    extrinsics_hash: str = ""
    stamp_s: float = 0.0
    ok: bool = False


@dataclass
class TimeSyncMsg:
    """Companion monotonic ↔ FC / sensor offsets [ns]."""

    cam_imu_offset_ns: int = 0
    fc_offset_ns: int = 0
    stamp_ns: int = 0
    quality: str = "unknown"  # unknown | coarse | locked


@dataclass
class VioStateMsg:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    qw: float = 1.0
    qx: float = 0.0
    qy: float = 0.0
    qz: float = 0.0
    cov_xx: float = 1.0e6
    cov_yy: float = 1.0e6
    cov_zz: float = 1.0e6
    status: str = "uninit"  # uninit | ok | degraded | diverge
    provider: str = ""
    stamp_s: float = 0.0
    stamp_ns: int = 0
    sensor_stamp_ns: int = 0
    frame_id: str = "body"


@dataclass
class MavlinkHealthMsg:
    link_ok: bool = False
    mode: str = ""
    armed: bool = False
    guided_ok: bool = False
    failsafe: bool = False
    last_heartbeat_s: float = 0.0
    stamp_s: float = 0.0


@dataclass
class SensorHubHealth:
    cam_ok: bool = False
    imu_ok: bool = False
    gnss_ok: bool = False
    dropped_frames: int = 0
    detail: str = ""
    stamp_s: float = 0.0


@dataclass
class SegMetaMsg:
    """Rate-limited segmentation meta (mask optional / out-of-band)."""

    classes_present: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    ok: bool = False
    stamp_s: float = 0.0
    stamp_ns: int = 0


@dataclass
class DepthGridMsg:
    """Coarse obstacle grid in body/ENU — FLIGHT-2."""

    cells: list[tuple[float, float, float, float]] = field(default_factory=list)
    # (x, y, z, confidence)
    frame_id: str = "body"
    ok: bool = False
    stamp_s: float = 0.0
    stamp_ns: int = 0


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
    trace_id: str = ""
    action: str = "GOTO_XYZ"


@dataclass
class MissionProfileMsg:
    profile_id: str
    version: int = 1
    content_hash: str = ""
    stamp_s: float = 0.0


@dataclass
class PolicyDecisionMsg:
    action: str
    allowed: bool
    reason: str = ""
    trace_id: str = ""
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
TOPIC_POSEIDON_VE_HITS = "/bd/poseidon/ve/hits"
TOPIC_POSEIDON_VL_SCENE = "/bd/poseidon/vl/scene"
TOPIC_POSEIDON_FW_DELTA = "/bd/poseidon/fw/delta"
TOPIC_HB_A = "/bd/dual/heartbeat_A"
TOPIC_HB_B = "/bd/dual/heartbeat_B"
TOPIC_MIRROR = "/bd/dual/mirror"
TOPIC_GOAL = "/bd/planning/goal"
TOPIC_BATTERY_SOC = "/bd/power/battery_soc"
TOPIC_TRACK_TARGET = "/bd/guidance/track_target"
TOPIC_NAV_VIO = "/bd/nav/vio"
TOPIC_NAV_FUSED = "/bd/nav/fused"
TOPIC_VISION_SEG = "/bd/vision/seg"
TOPIC_DEPTH_GRID = "/bd/depth/grid"
TOPIC_CALIB_ACTIVE = "/bd/calib/active"
TOPIC_TIME_SYNC = "/bd/time/sync"
TOPIC_MAVLINK_HEALTH = "/bd/l0/mavlink_health"
TOPIC_SENSORHUB_HEALTH = "/bd/sensorhub/health"
TOPIC_PLANE_CMD = "/bd/l0/plane_cmd"
TOPIC_TRACE_SPAN = "/bd/trace/span"
TOPIC_MISSION_PROFILE = "/bd/mission/profile"
TOPIC_POLICY_DECISION = "/bd/mission/policy_decision"
