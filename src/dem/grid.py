"""Common metric grid: reproject a lon/lat DEM to local UTM (polar stereographic beyond
UTM's limits) at a fixed pixel size, so Earth and Moon metrics are computed the same way.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class MetricGrid:
    dem: np.ndarray            # float32 metres, NaN = no data
    worldcover: np.ndarray     # uint8 class codes, 0 = no data
    transform: "rasterio.Affine"
    crs: str
    res_m: float


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


def crop_center(arr: np.ndarray, mg: MetricGrid, lon: float, lat: float, half_km: float) -> np.ndarray:
    """Square of +-half_km (metric) around a lon/lat point."""
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", mg.crs, always_xy=True).transform(lon, lat)
    col, row = ~mg.transform * (x, y)
    hp = int(round(half_km * 1000 / mg.res_m))
    r, c = int(row), int(col)
    return arr[max(r - hp, 0):r + hp + 1, max(c - hp, 0):c + hp + 1]
