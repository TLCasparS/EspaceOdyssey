"""
Terrain metrics that can be compared between Earth DEMs and lunar DEMs (e.g. LOLA).

All functions take a 2-D elevation array (NaN = no data) plus the pixel size in metres.
Copernicus DEM is in geographic degrees, so use pixel_size_m() to convert first.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage


def pixel_size_m(transform, center_lat: float) -> tuple[float, float]:
    """(dx, dy) in metres for a lat/lon grid at the given latitude."""
    deg_x, deg_y = abs(transform.a), abs(transform.e)
    lat = math.radians(center_lat)
    # WGS84 metres per degree (good to <0.1 %)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * lat) + 1.175 * math.cos(4 * lat)
    m_per_deg_lon = 111412.84 * math.cos(lat) - 93.5 * math.cos(3 * lat)
    return deg_x * m_per_deg_lon, deg_y * m_per_deg_lat


def _filled(elev: np.ndarray) -> np.ndarray:
    """Replace NaN with nearest valid value so filters don't explode (result is re-masked)."""
    mask = np.isnan(elev)
    if not mask.any():
        return elev
    if mask.all():
        return np.zeros_like(elev)
    idx = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
    return elev[tuple(idx)]


def slope_deg(elev: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Slope in degrees (Horn's method, same as gdaldem slope)."""
    z = _filled(elev)
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float) / (8 * dx)
    ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=float) / (8 * dy)
    gx = ndimage.convolve(z, kx, mode="nearest")
    gy = ndimage.convolve(z, ky, mode="nearest")
    s = np.degrees(np.arctan(np.hypot(gx, gy)))
    s[np.isnan(elev)] = np.nan
    return s.astype("float32")


def roughness(elev: np.ndarray, window: int = 5) -> np.ndarray:
    """Standard deviation of elevation in a window (metres)."""
    z = _filled(elev).astype("float64")
    mean = ndimage.uniform_filter(z, window, mode="nearest")
    mean_sq = ndimage.uniform_filter(z * z, window, mode="nearest")
    r = np.sqrt(np.clip(mean_sq - mean * mean, 0, None))
    r[np.isnan(elev)] = np.nan
    return r.astype("float32")


def local_relief(elev: np.ndarray, window: int = 33) -> np.ndarray:
    """Max minus min elevation in a window (metres). 33 px ~ 1 km at 30 m."""
    z = _filled(elev)
    r = ndimage.maximum_filter(z, window, mode="nearest") - ndimage.minimum_filter(z, window, mode="nearest")
    r[np.isnan(elev)] = np.nan
    return r.astype("float32")


def tri(elev: np.ndarray) -> np.ndarray:
    """Terrain Ruggedness Index (Riley 1999): mean abs difference to the 8 neighbours."""
    z = _filled(elev)
    pad = np.pad(z, 1, mode="edge")
    h, w = z.shape
    diffs = [np.abs(pad[1 + i:1 + i + h, 1 + j:1 + j + w] - z)
             for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)]
    t = np.mean(diffs, axis=0)
    t[np.isnan(elev)] = np.nan
    return t.astype("float32")


def summarize(elev: np.ndarray, dx: float, dy: float, relief_window_m: float = 1000.0) -> dict:
    """Compute all metrics and return (summary stats dict, layers dict)."""
    win = max(3, int(round(relief_window_m / ((dx + dy) / 2))) | 1)  # odd window
    layers = {
        "elevation": elev.astype("float32"),
        "slope_deg": slope_deg(elev, dx, dy),
        "roughness_m": roughness(elev),
        "relief_m": local_relief(elev, win),
        "tri_m": tri(elev),
    }

    def stats(a):
        v = a[~np.isnan(a)]
        if v.size == 0:
            return None
        return {k: round(float(x), 2) for k, x in zip(
            ("min", "p10", "median", "mean", "p90", "max"),
            (v.min(), np.percentile(v, 10), np.median(v), v.mean(), np.percentile(v, 90), v.max()))}

    s = layers["slope_deg"]
    valid = ~np.isnan(s)
    summary = {
        "pixel_size_m": [round(dx, 2), round(dy, 2)],
        "valid_fraction": round(float(valid.mean()), 4),
        "relief_window_px": win,
        # share of terrain flat enough for landing/building (thresholds used in lunar site studies)
        "frac_slope_lt_5deg": round(float((s[valid] < 5).mean()), 4) if valid.any() else None,
        "frac_slope_lt_10deg": round(float((s[valid] < 10).mean()), 4) if valid.any() else None,
        "frac_slope_gt_30deg": round(float((s[valid] > 30).mean()), 4) if valid.any() else None,
        **{name: stats(arr) for name, arr in layers.items()},
    }
    return summary, layers
