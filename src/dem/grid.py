"""Common metric grid: put any DEM onto square metric pixels (default 60 m) before computing
slope / roughness, so Earth and Moon values are comparable (they depend on resolution and
projection).

    mg = reproject_dem(z, transform, "EPSG:4326")                 # Earth: local UTM, 60 m
    mg = reproject_dem(z_lola, tf_lola, lola_crs)                  # Moon: already projected -> keep CRS, 60 m
    mg = reproject_dem(z_moon_ll, tf, moon_geographic_crs, dst_crs=moon_polar_stereo)

Missing data stays NaN ("no data", never 0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class MetricGrid:
    dem: np.ndarray                    # float32 metres, NaN = no data
    transform: "rasterio.Affine"
    crs: object                        # anything rasterio/pyproj accept (EPSG string, WKT, proj4)
    res_m: float
    worldcover: np.ndarray | None = None   # uint8 class codes on the same grid, 0 = no data


def metric_crs_for(lon: float, lat: float) -> str:
    """Earth only: UTM zone for a point; polar stereographic beyond UTM's 84N / 80S limits."""
    if lat >= 84:
        return "EPSG:3413"
    if lat <= -80:
        return "EPSG:3031"
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:{32600 + zone if lat >= 0 else 32700 + zone}"


def _resampling(name: str):
    from rasterio.enums import Resampling
    return Resampling[name]


def default_dst_crs(src_crs, bounds):
    """Projected source -> keep it. Earth lon/lat (WGS84) -> local UTM. Other lon/lat -> ask."""
    from pyproj import CRS
    crs = CRS.from_user_input(src_crs)
    if crs.is_projected:
        return src_crs
    if crs.ellipsoid is not None and abs(crs.ellipsoid.semi_major_metre - 6_378_137.0) < 1_000:
        west, south, east, north = bounds
        return metric_crs_for((west + east) / 2, (south + north) / 2)
    raise ValueError("source is a non-Earth lon/lat CRS: pass dst_crs (e.g. a lunar polar stereographic CRS)")


def reproject_dem(z: np.ndarray, transform, src_crs, res_m: float = 60.0, dst_crs=None,
                  resampling: str = "bilinear") -> MetricGrid:
    """Reproject / resample a DEM array to square res_m pixels in a metric CRS."""
    from rasterio.crs import CRS as RioCRS
    from rasterio.transform import array_bounds
    from rasterio.warp import calculate_default_transform, reproject

    h, w = z.shape
    west, south, east, north = array_bounds(h, w, transform)
    src = RioCRS.from_user_input(src_crs)
    dst_crs = dst_crs if dst_crs is not None else default_dst_crs(src_crs, (west, south, east, north))
    dst = RioCRS.from_user_input(dst_crs)
    dst_tf, width, height = calculate_default_transform(src, dst, w, h, west, south, east, north,
                                                        resolution=res_m)
    out = np.full((height, width), np.nan, np.float32)
    reproject(z.astype(np.float32), out, src_transform=transform, src_crs=src, src_nodata=np.nan,
              dst_transform=dst_tf, dst_crs=dst, dst_nodata=np.nan, resampling=_resampling(resampling),
              tolerance=0.0)   # exact transform: GDAL's default 1/8-px approximation tilts slopes by up to ~0.7 deg
    return MetricGrid(out, dst_tf, dst_crs, res_m)


def onto_grid(arr: np.ndarray, transform, src_crs, mg: MetricGrid, nodata=0,
              resampling: str = "nearest") -> np.ndarray:
    """Put another layer (land cover, usable mask, ...) onto an existing MetricGrid."""
    from rasterio.crs import CRS as RioCRS
    from rasterio.warp import reproject
    out = np.full(mg.dem.shape, nodata, arr.dtype)
    reproject(arr, out, src_transform=transform, src_crs=RioCRS.from_user_input(src_crs), src_nodata=nodata,
              dst_transform=mg.transform, dst_crs=RioCRS.from_user_input(mg.crs), dst_nodata=nodata,
              resampling=_resampling(resampling))
    return out


def to_metric_grid(region, res_m: float = 30.0, crs: str | None = None) -> MetricGrid:
    """fetch_region.Region (DEM + WorldCover) -> MetricGrid. Used by run_terrain_sites.py."""
    mg = reproject_dem(region.dem, region.dem_transform, region.crs, res_m=res_m, dst_crs=crs)
    # nearest keeps classes crisp (mode would be nicer)
    mg.worldcover = onto_grid(region.worldcover, region.wc_transform, region.crs, mg, nodata=0)
    return mg


def crop_center(arr: np.ndarray, mg: MetricGrid, lon: float, lat: float, half_km: float) -> np.ndarray:
    """Square of +-half_km (metric) around a lon/lat point (Earth)."""
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", mg.crs, always_xy=True).transform(lon, lat)
    col, row = ~mg.transform * (x, y)
    hp = int(round(half_km * 1000 / mg.res_m))
    r, c = int(row), int(col)
    return arr[max(r - hp, 0):r + hp + 1, max(c - hp, 0):c + hp + 1]
