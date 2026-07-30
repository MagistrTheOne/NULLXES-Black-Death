"""Image preprocess for YOLO-ONNX (flight path)."""

from __future__ import annotations

import numpy as np

# Ultralytics letterbox pad (documented constant, not a silent default for callers)
LETTERBOX_PAD_BGR = (114, 114, 114)


def letterbox(
    image: np.ndarray,
    new_shape: tuple[int, int],
    color: tuple[int, int, int] = LETTERBOX_PAD_BGR,
) -> tuple[np.ndarray, float, tuple[int, int]]:
    """Resize with unchanged aspect ratio; pad to new_shape (h, w).

    Returns (padded_bgr, ratio, (pad_x, pad_y)).
    """
    import cv2

    h0, w0 = image.shape[:2]
    th, tw = new_shape
    ratio = min(th / h0, tw / w0)
    nh, nw = int(round(h0 * ratio)), int(round(w0 * ratio))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pad_w, pad_h = tw - nw, th - nh
    left, right = pad_w // 2, pad_w - pad_w // 2
    top, bottom = pad_h // 2, pad_h - pad_h // 2
    out = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return out, ratio, (left, top)


def bgr_to_nchw_float(image: np.ndarray) -> np.ndarray:
    """BGR uint8 HWC → float32 NCHW RGB / 255."""
    rgb = image[:, :, ::-1].astype(np.float32) / 255.0
    return np.transpose(rgb, (2, 0, 1))[None, ...]
