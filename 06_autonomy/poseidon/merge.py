"""Merge CERBER + POSEIDON detections (CERBER class id space)."""

from __future__ import annotations

from perception.vision.decode import Detection
from perception.vision.nms import nms


def merge_detections(
    cerber: list[Detection],
    poseidon: list[Detection],
    *,
    iou: float = 0.45,
) -> list[Detection]:
    """Class-aware NMS over union of generalist + specialist boxes."""
    return nms(list(cerber) + list(poseidon), iou)
