"""Terrain metrics on a metric grid: slope, aspect, relief and roughness.

1. `to_metric_grid` reprojects a fetch_region.Region to UTM (polar stereographic above 84 deg)
   at a fixed pixel size: DEM bilinear, WorldCover nearest neighbour, both on the same grid.
2. `compute_terrain` derives, per pixel:
   - slope_deg:   steepest slope, Horn (1981) 3x3 finite differences
   - aspect_deg:  direction the slope faces, degrees clockwise from TRUE north
                  (corrected for UTM grid convergence); NaN on flat cells
   - relief_m:    max minus min elevation in a square window (default 5 km x 5 km)
   - roughness_m: standard deviation of elevation in a small window (default 3x3 pixels)
   - tri_m:       Terrain Ruggedness Index (Riley 1999), from dem.terrain.tri

The lat/lon-grid versions of these metrics (no reprojection, for quick bbox summaries
and GeoTIFF export) live in the dem package: see src/dem/ and scripts/analyze_bbox.py.

Cells within half a window of the grid edge or of missing data are NaN, so no
metric is computed from a truncated window. Fetch a buffer around the area of interest.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dem.terrain import tri as _tri  # noqa: E402


@dataclass
class MetricGrid:
    dem: np.ndarray            # float32 metres, NaN = no data
    worldcover: np.ndarray     # uint8 class codes, 0 = no data
    transform: "rasterio.Affine"
    crs: str
    res_m: float


@dataclass
class Terrain:
    slope_deg: np.ndarray
    aspect_deg: np.ndarray
    relief_m: np.ndarray
    roughness_m: np.ndarray
    tri_m: np.ndarray
    relief_window_m: float
    roughness_window_px: int


def metric_crs_for(lon: float, lat: float) -> str:
    """UTM zone for a point; polar stereographic beyond UTM's 84N / 80S limits."""
    if lat >= 84:
        return "EPSG:3413"
    if lat <= -80:
        return "EPSG:3031"
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:{32600 + zone if lat >= 0 else 32700 + zone}"


def to_metric_grid(region, res_m: float = 30.0, crs: str | None = None) -> MetricGrid:
    import rasterio
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    west, south, east, north = region.bbox
    crs = crs or metric_crs_for((west + east) / 2, (south + north) / 2)
    h, w = region.dem.shape
    transform, width, height = calculate_default_transform(
        region.crs, crs, w, h, west, south, east, north, resolution=res_m)

    dem = np.full((height, width), np.nan, np.float32)
    reproject(region.dem, dem, src_transform=region.dem_transform, src_crs=region.crs,
              src_nodata=np.nan, dst_transform=transform, dst_crs=crs, dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    wc = np.zeros((height, width), np.uint8)
    reproject(region.worldcover, wc, src_transform=region.wc_transform, src_crs=region.crs,
              src_nodata=0, dst_transform=transform, dst_crs=crs, dst_nodata=0,
              resampling=Resampling.nearest)  # mode would be nicer, but nearest keeps classes crisp
    return MetricGrid(dem, wc, transform, crs, res_m)


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

    tri = np.where(_window_valid(nan, 3), _tri(mg.dem), np.nan)

    f32 = lambda a: a.astype(np.float32)
    return Terrain(f32(slope), f32(aspect), f32(relief), f32(rough), f32(tri), n * mg.res_m, k)


def crop_center(arr: np.ndarray, mg: MetricGrid, lon: float, lat: float, half_km: float) -> np.ndarray:
    """Square of +-half_km (metric) around a lon/lat point."""
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", mg.crs, always_xy=True).transform(lon, lat)
    col, row = ~mg.transform * (x, y)
    hp = int(round(half_km * 1000 / mg.res_m))
    r, c = int(row), int(col)
    return arr[max(r - hp, 0):r + hp + 1, max(c - hp, 0):c + hp + 1]
