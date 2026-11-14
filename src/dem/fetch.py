"""
Read Copernicus DEM (GLO-30 / GLO-90) straight from the public AWS buckets.

No AWS account needed. Tiles are 1x1 degree cloud-optimized GeoTIFFs named after
their south-west corner, e.g. N28_00_E083_00 covers 28-29N, 83-84E.

    from dem import read_bbox
    elev, profile = read_bbox(83.6, 28.7, 84.0, 29.1)          # 30 m
    elev, profile = read_bbox(83.0, 28.0, 85.0, 30.0, res=90)  # 90 m, faster
"""
from __future__ import annotations

import math
import os
import time
import warnings

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.merge import merge

# Public bucket -> unsigned requests. Also keep GDAL from listing directories (faster).
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

_BUCKETS = {30: ("copernicus-dem-30m", "10"), 90: ("copernicus-dem-90m", "30")}
NODATA = -32767.0


def tile_url(lat: float, lon: float, res: int = 30) -> str:
    """S3 path of the tile containing (lat, lon)."""
    if res not in _BUCKETS:
        raise ValueError("res must be 30 or 90")
    bucket, code = _BUCKETS[res]
    la, lo = math.floor(lat), math.floor(lon)
    ns = "N" if la >= 0 else "S"
    ew = "E" if lo >= 0 else "W"
    name = f"Copernicus_DSM_COG_{code}_{ns}{abs(la):02d}_00_{ew}{abs(lo):03d}_00_DEM"
    return f"s3://{bucket}/{name}/{name}.tif"


def tiles_for_bbox(west: float, south: float, east: float, north: float, res: int = 30) -> list[str]:
    """All tile paths intersecting the bounding box (degrees, WGS84)."""
    if west >= east or south >= north:
        raise ValueError("bbox must be (west, south, east, north) with west<east, south<north")
    urls = []
    # subtract a tiny epsilon so a bbox ending exactly on a tile edge doesn't pull the next tile
    for la in range(math.floor(south), math.floor(north - 1e-9) + 1):
        for lo in range(math.floor(west), math.floor(east - 1e-9) + 1):
            urls.append(tile_url(la, lo, res))
    return urls


def _is_missing(err: Exception) -> bool:
    """True if GDAL says the file does not exist (vs. a network/read problem)."""
    msg = str(err)
    return "does not exist" in msg or "404" in msg or "No such file" in msg


def open_tile(url: str, attempts: int = 3):
    """rasterio dataset, or None if the tile does not exist (ocean / not public).

    Network errors are retried and then raised, so a flaky connection is never
    mistaken for ocean.
    """
    for i in range(attempts):
        try:
            return rasterio.open(url)
        except RasterioIOError as e:
            if _is_missing(e):
                return None
            if i == attempts - 1:
                raise RuntimeError(f"could not open {url} after {attempts} tries: {e}") from e
            time.sleep(2 * (i + 1))


def with_retries(fn, attempts: int = 3):
    """Call fn(); retry on read errors (e.g. a tile download cut short)."""
    for i in range(attempts):
        try:
            return fn()
        except RasterioIOError as e:
            if i == attempts - 1:
                raise
            warnings.warn(f"read failed ({e}); retrying")
            time.sleep(2 * (i + 1))


def read_bbox(west: float, south: float, east: float, north: float, res: int = 30):
    """
    Return (elevation, profile) for a bounding box, merging tiles as needed.

    elevation: 2-D float32 numpy array, metres above EGM2008 geoid, NaN where no data
               (ocean, or the few non-public country tiles).
    profile:   rasterio profile (transform, crs, ...) to save results with rasterio.
    """
    urls = tiles_for_bbox(west, south, east, north, res)
    datasets, missing = [], []
    try:
        for url in urls:
            ds = open_tile(url)          # raises on network errors, None only if truly missing
            (datasets.append(ds) if ds is not None else missing.append(url))
    except Exception:
        for d in datasets:
            d.close()
        raise
    if not datasets:
        raise RuntimeError("No DEM tiles exist for this bbox (all ocean / not public).")
    if missing:
        warnings.warn(f"{len(missing)} tile(s) not available (ocean or not public): "
                      + ", ".join(u.split('/')[-1] for u in missing))

    try:
        # Above ~50 deg latitude tiles have coarser longitude spacing; use the finest grid.
        target_res = (min(d.res[0] for d in datasets), min(d.res[1] for d in datasets))
        mosaic, transform = with_retries(lambda: merge(
            datasets, bounds=(west, south, east, north), res=target_res, nodata=NODATA))
        crs = datasets[0].crs
    finally:
        for d in datasets:
            d.close()

    elev = mosaic[0].astype("float32")
    elev[elev <= NODATA + 1] = np.nan

    profile = {
        "driver": "GTiff", "dtype": "float32", "count": 1,
        "height": elev.shape[0], "width": elev.shape[1],
        "crs": crs, "transform": transform, "nodata": np.nan,
        "compress": "deflate", "tiled": True,
    }
    return elev, profile


def save_tif(path: str, array: np.ndarray, profile: dict) -> None:
    """Write a single-band float array with the given profile."""
    p = dict(profile, height=array.shape[0], width=array.shape[1], dtype="float32", count=1)
    with rasterio.open(path, "w", **p) as dst:
        dst.write(array.astype("float32"), 1)
