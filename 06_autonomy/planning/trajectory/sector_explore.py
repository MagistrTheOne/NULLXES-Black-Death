"""Lawnmower sector explore — more than one waypoint from a bbox."""

from __future__ import annotations

from .path import Waypoint


def lawnmower(
    *,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    z: float,
    spacing_m: float = 40.0,
) -> list[Waypoint]:
    if xmax < xmin:
        xmin, xmax = xmax, xmin
    if ymax < ymin:
        ymin, ymax = ymax, ymin
    if spacing_m <= 0.0:
        raise ValueError("spacing_m must be > 0")
    span_x = xmax - xmin
    span_y = ymax - ymin
    if span_x < 1e-3 and span_y < 1e-3:
        return [Waypoint(xmin, ymin, z)]
    n = max(2, int(span_y / spacing_m) + 1)
    wps: list[Waypoint] = []
    for i in range(n):
        y = ymin + (span_y * i / (n - 1) if n > 1 else 0.0)
        if i % 2 == 0:
            wps.append(Waypoint(xmin, y, z))
            if span_x >= 1e-3:
                wps.append(Waypoint(xmax, y, z))
        else:
            wps.append(Waypoint(xmax, y, z))
            if span_x >= 1e-3:
                wps.append(Waypoint(xmin, y, z))
    return wps
