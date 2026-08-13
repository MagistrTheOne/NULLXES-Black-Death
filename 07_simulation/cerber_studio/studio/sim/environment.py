"""Atmosphere split: visuals stay in Panda. FDM gets physical fields only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalAtmosphere:
    wind_east_mps: float
    wind_north_mps: float
    temperature_k: float
    pressure_pa: float
    density_kgm3: float


@dataclass(frozen=True)
class VisualAtmosphere:
    clock_h: float
    sun_elevation: float
    sun_azimuth: float
    cloudiness: float
    visibility_km: float
    precipitation: float
    night_factor: float
    lights_on: bool


def _isa(alt_m: float, temperature_c: float) -> tuple[float, float]:
    t_k = 273.15 + float(temperature_c)
    t_isa = max(180.0, 288.15 - 0.0065 * max(0.0, alt_m))
    pressure = 101325.0 * (t_isa / 288.15) ** 5.2561
    density = pressure / (287.05 * max(180.0, t_k))
    return pressure, density


class EnvironmentBridge:
    def physical(self, atmos, *, alt_m: float, heading_deg: float = 0.0) -> PhysicalAtmosphere:
        import math

        mag = float(getattr(atmos, "wind_mps", 0.0))
        dir_deg = float(getattr(atmos, "wind_dir_deg", 0.0))
        rad = math.radians(dir_deg)
        east = mag * math.sin(rad)
        north = mag * math.cos(rad)
        pressure, density = _isa(alt_m, float(getattr(atmos, "temperature_c", 15.0)))
        return PhysicalAtmosphere(
            wind_east_mps=east,
            wind_north_mps=north,
            temperature_k=273.15 + float(getattr(atmos, "temperature_c", 15.0)),
            pressure_pa=pressure,
            density_kgm3=density,
        )

    def visual(self, atmos) -> VisualAtmosphere:
        return VisualAtmosphere(
            clock_h=float(atmos.clock_h),
            sun_elevation=float(atmos.sun_elevation),
            sun_azimuth=float(atmos.sun_azimuth),
            cloudiness=float(atmos.cloudiness),
            visibility_km=float(atmos.visibility_km),
            precipitation=float(atmos.precipitation),
            night_factor=float(atmos.night_factor),
            lights_on=bool(atmos.lights_on),
        )
