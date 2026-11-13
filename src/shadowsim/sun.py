"""Sun position on Earth (azimuth and elevation) without external dependencies.

Low-precision algorithm from the Astronomical Almanac (good to roughly 0.01 deg
for 1950-2050), plus a standard refraction correction near the horizon.
Azimuth is measured from north, clockwise (east = 90 deg).
"""
from __future__ import annotations

import numpy as np


def year_times(year: int, step_minutes: int = 60) -> np.ndarray:
    """All UTC time steps of one calendar year as numpy datetime64[s]."""
    start = np.datetime64(f"{year}-01-01T00:00:00")
    end = np.datetime64(f"{year + 1}-01-01T00:00:00")
    return np.arange(start, end, np.timedelta64(step_minutes, "m")).astype("datetime64[s]")


def _refraction_deg(elev_deg: np.ndarray) -> np.ndarray:
    """Atmospheric refraction (Saemundsson), added to the true elevation."""
    h = np.clip(elev_deg, -1.0, 90.0)
    r_arcmin = 1.02 / np.tan(np.radians(h + 10.3 / (h + 5.11)))
    r = r_arcmin / 60.0
    return np.where(elev_deg > -1.0, r, 0.0)


def sun_position(lat_deg: float, lon_deg: float, times_utc: np.ndarray,
                 refraction: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Return (azimuth_deg, elevation_deg) of the Sun's centre for each time."""
    t = np.asarray(times_utc, dtype="datetime64[s]").astype(np.int64)
    n = t / 86400.0 + 2440587.5 - 2451545.0  # days since J2000.0

    mean_lon = np.radians((280.460 + 0.9856474 * n) % 360.0)
    g = np.radians((357.528 + 0.9856003 * n) % 360.0)
    ecl_lon = mean_lon + np.radians(1.915) * np.sin(g) + np.radians(0.020) * np.sin(2 * g)
    eps = np.radians(23.439 - 0.0000004 * n)

    ra = np.arctan2(np.cos(eps) * np.sin(ecl_lon), np.cos(ecl_lon))
    dec = np.arcsin(np.sin(eps) * np.sin(ecl_lon))

    gmst_h = (18.697374558 + 24.06570982441908 * n) % 24.0
    ha = np.radians(gmst_h * 15.0 + lon_deg) - ra

    lat = np.radians(lat_deg)
    sin_el = np.sin(lat) * np.sin(dec) + np.cos(lat) * np.cos(dec) * np.cos(ha)
    elev = np.degrees(np.arcsin(np.clip(sin_el, -1, 1)))
    az = np.degrees(np.arctan2(-np.sin(ha) * np.cos(dec),
                               np.sin(dec) * np.cos(lat) - np.cos(dec) * np.sin(lat) * np.cos(ha))) % 360.0
    if refraction:
        elev = elev + _refraction_deg(elev)
    return az, elev
