"""Continuous atmosphere. Presets are initial profiles, not frozen states."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

PRESETS = ("clear", "sunset", "overcast", "night", "rain", "fog", "storm")
TIME_FLOW = ("static", "1x", "4x", "12x")
FLOW_MUL = {"static": 0.0, "1x": 1.0, "4x": 4.0, "12x": 12.0}

PROFILES = {
    "clear": dict(clock=12.0, cloudiness=0.08, visibility_km=42.0, wind_mps=1.4, precipitation=0.0, temperature_c=18.0, gust_mps=0.6),
    "sunset": dict(clock=18.6, cloudiness=0.18, visibility_km=28.0, wind_mps=1.8, precipitation=0.0, temperature_c=14.0, gust_mps=1.1),
    "overcast": dict(clock=13.0, cloudiness=0.78, visibility_km=12.0, wind_mps=3.4, precipitation=0.08, temperature_c=11.0, gust_mps=2.2),
    "night": dict(clock=22.5, cloudiness=0.22, visibility_km=18.0, wind_mps=1.1, precipitation=0.0, temperature_c=8.0, gust_mps=0.5),
    "rain": dict(clock=14.0, cloudiness=0.86, visibility_km=6.5, wind_mps=4.2, precipitation=0.7, temperature_c=9.0, gust_mps=3.0),
    "fog": dict(clock=8.5, cloudiness=0.55, visibility_km=2.4, wind_mps=0.8, precipitation=0.05, temperature_c=7.0, gust_mps=0.4),
    "storm": dict(clock=16.0, cloudiness=0.95, visibility_km=4.0, wind_mps=8.5, precipitation=0.85, temperature_c=10.0, gust_mps=7.0),
}


def sun_from_clock(clock_h: float) -> tuple[float, float]:
    ang = ((clock_h - 6.0) / 12.0) * math.pi
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(ang)))))
    azimuth = (clock_h / 24.0) * 360.0 - 90.0
    return elevation, azimuth % 360.0


@dataclass
class AtmosphereState:
    preset: str = "clear"
    time_of_day_h: float = 12.0
    time_flow: str = "1x"
    wind_dir_deg: float = 40.0
    wind_mps: float = 1.2
    gust_mps: float = 0.6
    rain: float = 0.0
    fog: float = 0.0
    storm: float = 0.0
    cloudiness: float = 0.1
    visibility_km: float = 35.0
    precipitation: float = 0.0
    temperature_c: float = 16.0
    sun_elevation: float = 45.0
    sun_azimuth: float = 180.0
    visual_override: bool = False
    override_clock_h: float = 12.0

    @property
    def clock_h(self) -> float:
        return self.override_clock_h if self.visual_override else self.time_of_day_h

    @property
    def night_factor(self) -> float:
        el = self.sun_elevation
        if el >= 8.0:
            return 0.0
        if el <= -4.0:
            return 1.0
        return float((8.0 - el) / 12.0)

    @property
    def lights_on(self) -> bool:
        return self.night_factor > 0.45

    def apply_preset(self, name: str) -> None:
        key = (name or "clear").lower()
        if key not in PROFILES:
            key = "clear"
        p = PROFILES[key]
        self.preset = key
        self.time_of_day_h = float(p["clock"])
        self.cloudiness = float(p["cloudiness"])
        self.visibility_km = float(p["visibility_km"])
        self.wind_mps = float(p["wind_mps"])
        self.precipitation = float(p["precipitation"])
        self.temperature_c = float(p["temperature_c"])
        self.gust_mps = float(p["gust_mps"])
        self.rain = self.precipitation
        self.fog = max(0.0, min(1.0, 1.0 - self.visibility_km / 40.0))
        self.storm = 1.0 if key == "storm" else 0.0
        self.sun_elevation, self.sun_azimuth = sun_from_clock(self.time_of_day_h)
        self.visual_override = False

    def set_visual_clock(self, clock_h: float | None) -> None:
        if clock_h is None:
            self.visual_override = False
            self.sun_elevation, self.sun_azimuth = sun_from_clock(self.time_of_day_h)
            return
        self.visual_override = True
        self.override_clock_h = float(clock_h) % 24.0
        self.sun_elevation, self.sun_azimuth = sun_from_clock(self.override_clock_h)

    def step_clock(self, dt: float) -> None:
        mul = FLOW_MUL.get(self.time_flow, 1.0)
        self.time_of_day_h = (self.time_of_day_h + dt * mul / 3600.0) % 24.0
        clock = self.clock_h if self.visual_override else self.time_of_day_h
        if not self.visual_override:
            self.sun_elevation, self.sun_azimuth = sun_from_clock(clock)
            drift = math.sin(self.time_of_day_h * 0.41) * 0.002 * dt
            self.cloudiness = max(0.0, min(1.0, self.cloudiness + drift))
            vis_target = 42.0 - 36.0 * self.cloudiness - 18.0 * self.precipitation
            self.visibility_km += (vis_target - self.visibility_km) * min(1.0, 0.04 * dt)
            self.rain = self.precipitation
            self.fog = max(0.0, min(1.0, 1.0 - self.visibility_km / 40.0))
            if self.precipitation > 0.55 and self.cloudiness > 0.8:
                self.storm = min(1.0, self.storm + 0.02 * dt)
            else:
                self.storm = max(0.0, self.storm - 0.03 * dt)
            night = self.night_factor
            self.temperature_c += ((16.0 - 9.0 * night) - self.temperature_c) * min(1.0, 0.02 * dt)


def as_dict(atmos: AtmosphereState) -> dict:
    return {f.name: getattr(atmos, f.name) for f in fields(atmos)}
