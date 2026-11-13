"""Horizon angles from a digital elevation model (DEM).

For every cell of an analysis window and every azimuth sector we march outwards
along the terrain and keep the steepest elevation angle we see. A cell is in
direct sunlight when the Sun is higher than that horizon angle.
This is computed once; the yearly simulation then only needs table lookups.
"""
from __future__ import annotations

import numpy as np

EARTH_RADIUS_M = 6_371_000.0
REFRACTION_K = 0.13  # standard terrestrial refraction coefficient


def _distances(step_m: float, max_dist_m: float, growth: float) -> np.ndarray:
    d, out = step_m, []
    while d <= max_dist_m:
        out.append(d)
        d = max(d * growth, d + step_m)
    return np.array(out)


def horizon_angles(dem: np.ndarray, window: tuple[int, int, int, int], dx_m: float, dy_m: float,
                   n_azimuths: int = 72, max_dist_m: float = 20_000.0, growth: float = 1.05,
                   curvature: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Horizon elevation angle (deg) for each azimuth sector and window cell.

    dem     : 2-D array, north-up (row 0 = north), metres. NaN = unknown.
    window  : (row0, row1, col0, col1) of the cells to evaluate.
    dx_m/dy_m : pixel size east-west / north-south in metres.
    Returns (azimuths_deg [n_az], horizon_deg [n_az, rows, cols]).
    Terrain outside the DEM counts as invisible, so give the DEM a buffer of
    at least max_dist_m around the window.
    """
    r0, r1, c0, c1 = window
    h, w = r1 - r0, c1 - c0
    azimuths = np.arange(n_azimuths) * 360.0 / n_azimuths
    dists = _distances(min(dx_m, dy_m), max_dist_m, growth)

    max_off_r = int(np.ceil(max_dist_m / dy_m)) + 1
    max_off_c = int(np.ceil(max_dist_m / dx_m)) + 1
    pad_top, pad_bot = max(0, max_off_r - r0), max(0, r1 + max_off_r - dem.shape[0])
    pad_left, pad_right = max(0, max_off_c - c0), max(0, c1 + max_off_c - dem.shape[1])
    z = np.pad(dem.astype(np.float32), ((pad_top, pad_bot), (pad_left, pad_right)),
               constant_values=np.nan)
    r0p, c0p = r0 + pad_top, c0 + pad_left
    z0 = z[r0p:r0p + h, c0p:c0p + w]

    horizon = np.full((n_azimuths, h, w), -90.0, dtype=np.float32)
    for k, az in enumerate(np.radians(azimuths)):
        seen = set()
        best = horizon[k]
        for d in dists:
            dr = int(round(-np.cos(az) * d / dy_m))  # rows grow southwards
            dc = int(round(np.sin(az) * d / dx_m))
            if (dr, dc) in seen or (dr == 0 and dc == 0):
                continue
            seen.add((dr, dc))
            dist = np.hypot(dr * dy_m, dc * dx_m)
            zs = z[r0p + dr:r0p + dr + h, c0p + dc:c0p + dc + w]
            drop = dist ** 2 * (1 - REFRACTION_K) / (2 * EARTH_RADIUS_M) if curvature else 0.0
            ang = np.degrees(np.arctan((zs - z0 - drop) / dist))
            np.fmax(best, ang, out=best)  # NaN (no data) never wins
    return azimuths, horizon
