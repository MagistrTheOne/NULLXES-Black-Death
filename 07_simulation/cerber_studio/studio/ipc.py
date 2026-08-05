"""ZeroMQ contracts for CERBER Studio — mirrors SoftBus detection/health semantics."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import cv2
import msgpack
import numpy as np
import zmq

DEFAULT_FRAME_ENDPOINT = "tcp://127.0.0.1:5591"
DEFAULT_RESULT_ENDPOINT = "tcp://127.0.0.1:5592"


@dataclass
class Detection:
    cls_id: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    name: str = ""
    track_id: int = -1


@dataclass
class VisionHealth:
    vision_ok: bool = False
    cams_alive: int = 0
    detail: str = ""
    stamp_s: float = 0.0
    infer_fps: float = 0.0


@dataclass
class TrackRow:
    track_id: int
    cls_id: int
    name: str
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class WorkerResult:
    stamp_s: float
    health: VisionHealth
    detections: list[Detection] = field(default_factory=list)
    tracks: list[TrackRow] = field(default_factory=list)
    jpeg: bytes = b""


def encode_frame(bgr: np.ndarray, meta: dict[str, Any] | None = None) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    payload = {
        "stamp_s": time.time(),
        "h": int(bgr.shape[0]),
        "w": int(bgr.shape[1]),
        "meta": meta or {},
        "jpeg": buf.tobytes(),
    }
    return msgpack.packb(payload, use_bin_type=True)


def decode_frame(blob: bytes) -> tuple[np.ndarray, dict[str, Any]]:
    payload = msgpack.unpackb(blob, raw=False)
    arr = np.frombuffer(payload["jpeg"], dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError("JPEG decode failed")
    return bgr, payload


def encode_result(result: WorkerResult) -> bytes:
    data = {
        "stamp_s": result.stamp_s,
        "health": asdict(result.health),
        "detections": [asdict(d) for d in result.detections],
        "tracks": [asdict(t) for t in result.tracks],
        "jpeg": result.jpeg,
    }
    return msgpack.packb(data, use_bin_type=True)


def decode_result(blob: bytes) -> WorkerResult:
    data = msgpack.unpackb(blob, raw=False)
    health = VisionHealth(**data["health"])
    dets = [Detection(**d) for d in data.get("detections", [])]
    tracks = [TrackRow(**t) for t in data.get("tracks", [])]
    return WorkerResult(
        stamp_s=float(data["stamp_s"]),
        health=health,
        detections=dets,
        tracks=tracks,
        jpeg=data.get("jpeg", b""),
    )


class FramePublisher:
    def __init__(self, endpoint: str = DEFAULT_FRAME_ENDPOINT) -> None:
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.PUB)
        self.sock.bind(endpoint)
        self.endpoint = endpoint

    def send(self, bgr: np.ndarray, meta: dict[str, Any] | None = None) -> None:
        self.sock.send(encode_frame(bgr, meta))

    def close(self) -> None:
        self.sock.close(linger=0)


class FrameSubscriber:
    def __init__(self, endpoint: str = DEFAULT_FRAME_ENDPOINT) -> None:
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.SUB)
        self.sock.connect(endpoint)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
        self.sock.setsockopt(zmq.RCVTIMEO, 100)

    def recv(self) -> tuple[np.ndarray, dict[str, Any]] | None:
        try:
            blob = self.sock.recv()
        except zmq.Again:
            return None
        return decode_frame(blob)

    def close(self) -> None:
        self.sock.close(linger=0)


class ResultPublisher:
    def __init__(self, endpoint: str = DEFAULT_RESULT_ENDPOINT) -> None:
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.PUB)
        self.sock.bind(endpoint)

    def send(self, result: WorkerResult) -> None:
        self.sock.send(encode_result(result))

    def close(self) -> None:
        self.sock.close(linger=0)


class ResultSubscriber:
    def __init__(self, endpoint: str = DEFAULT_RESULT_ENDPOINT) -> None:
        self.ctx = zmq.Context.instance()
        self.sock = self.ctx.socket(zmq.SUB)
        self.sock.connect(endpoint)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
        self.sock.setsockopt(zmq.RCVTIMEO, 10)

    def recv(self) -> WorkerResult | None:
        try:
            blob = self.sock.recv()
        except zmq.Again:
            return None
        return decode_result(blob)

    def close(self) -> None:
        self.sock.close(linger=0)


def health_json(h: VisionHealth) -> str:
    return json.dumps(asdict(h), ensure_ascii=False)
