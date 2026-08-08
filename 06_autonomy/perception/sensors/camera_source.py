"""Camera frame sources — OpenCV/V4L2/CSI via index or GStreamer pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CapturedFrame:
    bgr: object  # np.ndarray HWC uint8
    sensor_stamp_ns: int
    seq: int


class FrameSource(Protocol):
    def open(self) -> bool: ...

    def read(self) -> CapturedFrame | None: ...

    def close(self) -> None: ...

    @property
    def name(self) -> str: ...


class OpenCvCameraSource:
    """Production path: OpenCV VideoCapture (V4L2 / CSI / USB index or pipeline string)."""

    def __init__(
        self,
        device: int | str = 0,
        *,
        camera_name: str = "forward",
        width: int = 0,
        height: int = 0,
        fps: int = 0,
    ) -> None:
        self._device = device
        self._camera_name = camera_name
        self._width = width
        self._height = height
        self._fps = fps
        self._cap = None
        self._seq = 0

    @property
    def name(self) -> str:
        return self._camera_name

    def open(self) -> bool:
        import cv2

        self._cap = cv2.VideoCapture(self._device)
        if self._width > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        if self._height > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        if self._fps > 0:
            self._cap.set(cv2.CAP_PROP_FPS, self._fps)
        return bool(self._cap is not None and self._cap.isOpened())

    def read(self) -> CapturedFrame | None:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None
        self._seq += 1
        # Prefer driver buffer timestamp when available; else monotonic.
        stamp_ns = time.monotonic_ns()
        try:
            import cv2

            msec = self._cap.get(cv2.CAP_PROP_POS_MSEC)
            if msec and msec > 0:
                stamp_ns = int(msec * 1_000_000.0)
        except Exception:
            pass
        return CapturedFrame(bgr=frame, sensor_stamp_ns=stamp_ns, seq=self._seq)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
