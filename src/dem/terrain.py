"""
Terrain metrics that can be compared between Earth DEMs and lunar DEMs (e.g. LOLA).

Two sets of functions:
- Degree-grid functions (pixel_size_m, slope_deg, roughness, local_relief, summarize): quick look
  only, used by src/analyze_bbox.py. They work on the native lon/lat grid with an approximate
  metre conversion and fill NaN with the nearest value.
- Metric-grid functions (compute_terrain on a dem.grid.MetricGrid): use these for the pipeline.
tri() is shared by both.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .grid import MetricGrid


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


# --- Metric-grid metrics (use these for the pipeline) -------------------------------------
# Moved from src/terrain.py. Work on a dem.grid.MetricGrid (square metric pixels).
# Cells within half a window of the grid edge or of missing data are NaN, so no metric is
# computed from a truncated window. Fetch a buffer around the area of interest.

@dataclass
class Terrain:
    slope_deg: np.ndarray
    aspect_deg: np.ndarray
    relief_m: np.ndarray
    roughness_m: np.ndarray
    tri_m: np.ndarray
    relief_window_m: float
    roughness_window_px: int


def _horn_gradients(z: np.ndarray, res_m: float) -> tuple[np.ndarray, np.ndarray]:
    """dz/d(east) and dz/d(north) in grid axes; NaN where the 3x3 window is incomplete."""
    p = np.pad(z.astype(np.float64), 1, constant_values=np.nan)
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]   # row above (north)
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]      # row below (south)
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * res_m)
    dzdn = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * res_m)
    return dzdx, dzdn


def _grid_north_azimuth(mg: MetricGrid) -> np.ndarray:
    """Per pixel: azimuth of true north measured clockwise from grid north (degrees)."""
    from pyproj import Transformer

    rows, cols = mg.dem.shape
    # Convergence varies slowly; compute on a coarse lattice and interpolate.
    step = max(1, min(rows, cols) // 20)
    rr = np.arange(0, rows + step, step).clip(max=rows - 1)
    cc = np.arange(0, cols + step, step).clip(max=cols - 1)
    C, R = np.meshgrid(cc + 0.5, rr + 0.5)
    x, y = mg.transform * (C, R)
    to_ll = Transformer.from_crs(mg.crs, "EPSG:4326", always_xy=True)
    to_xy = Transformer.from_crs("EPSG:4326", mg.crs, always_xy=True)
    lon, lat = to_ll.transform(x, y)
    x2, y2 = to_xy.transform(lon, lat + 0.001)
    coarse = np.degrees(np.arctan2(x2 - x, y2 - y))
    zoom = (rows / coarse.shape[0], cols / coarse.shape[1])
    full = ndimage.zoom(coarse, zoom, order=1)
    return full[:rows, :cols]


def _window_valid(nan_mask: np.ndarray, size: int) -> np.ndarray:
    """True where a size x size window lies fully inside the grid and has no NaN."""
    bad = ndimage.maximum_filter(nan_mask.astype(np.uint8), size=size, mode="constant", cval=1)
    return bad == 0


def compute_terrain(mg: MetricGrid, relief_window_m: float = 5000.0,
                    roughness_window_px: int = 3, flat_slope_deg: float = 0.5) -> Terrain:
    z = mg.dem.astype(np.float64)
    nan = np.isnan(z)

    dzdx, dzdn = _horn_gradients(z, mg.res_m)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdn)))
    # Downslope direction (-dzdx, -dzdn) as an azimuth from grid north, then to true north.
    aspect_grid = np.degrees(np.arctan2(-dzdx, -dzdn))
    aspect = (aspect_grid - _grid_north_azimuth(mg)) % 360.0
    aspect[~(slope >= flat_slope_deg)] = np.nan   # flat or NaN: aspect is meaningless

    n = int(round(relief_window_m / mg.res_m)) | 1    # odd window size in pixels
    zmax = ndimage.maximum_filter(np.where(nan, -np.inf, z), size=n, mode="nearest")
    zmin = ndimage.minimum_filter(np.where(nan, np.inf, z), size=n, mode="nearest")
    relief = np.where(_window_valid(nan, n), zmax - zmin, np.nan)

    k = roughness_window_px
    zc = np.where(nan, 0.0, z - np.nanmean(z))       # centre to limit float cancellation
    mean = ndimage.uniform_filter(zc, size=k, mode="nearest")
    mean_sq = ndimage.uniform_filter(zc * zc, size=k, mode="nearest")
    rough = np.sqrt(np.clip(mean_sq - mean * mean, 0, None))
    rough = np.where(_window_valid(nan, k), rough, np.nan)

    tri_m = np.where(_window_valid(nan, 3), tri(mg.dem), np.nan)

    f32 = lambda a: a.astype(np.float32)
    return Terrain(f32(slope), f32(aspect), f32(relief), f32(rough), f32(tri_m), n * mg.res_m, k)
