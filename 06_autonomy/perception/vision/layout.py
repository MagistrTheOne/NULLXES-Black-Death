"""Vision layout contracts — no guessing."""

from __future__ import annotations

# Ultralytics detect ONNX export without end2end NMS: [1, 4+nc, N]
LAYOUT_YOLO_V8_RAW = "yolo_v8_raw"

BOX_CHANNELS = 4  # cx, cy, w, h


class UnsupportedLayoutError(ValueError):
    """Output tensor does not match the configured ONNX layout."""
