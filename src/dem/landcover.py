"""
ESA WorldCover 10 m (2021, v200) from the public AWS bucket, no account needed.

Tiles are 3x3 degree COGs named after their south-west corner (multiples of 3), e.g.
ESA_WorldCover_10m_2021_v200_N27E081_Map.tif covers 27-30N, 81-84E.

Classes:
 10 tree cover   20 shrubland   30 grassland   40 cropland   50 built-up
 60 bare/sparse vegetation      70 snow & ice  80 permanent water
 90 herbaceous wetland          95 mangroves   100 moss & lichen
  0 no data (ocean outside tiles)
"""
from __future__ import annotations

import math
import os
import warnings

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge

from .fetch import open_tile, with_retries

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("AWS_REGION", "eu-central-1")

CLASSES = {
    10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built",
    60: "bare", 70: "snow_ice", 80: "water", 90: "wetland", 95: "mangrove", 100: "moss_lichen",
}


def worldcover_url(lat: float, lon: float) -> str:
    la = math.floor(lat / 3) * 3
    lo = math.floor(lon / 3) * 3
    ns = "N" if la >= 0 else "S"
    ew = "E" if lo >= 0 else "W"
    tile = f"{ns}{abs(la):02d}{ew}{abs(lo):03d}"
    return f"s3://esa-worldcover/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"


def worldcover_tiles(west, south, east, north) -> list[str]:
    urls = []
    for la in range(math.floor(south / 3) * 3, math.floor((north - 1e-9) / 3) * 3 + 1, 3):
        for lo in range(math.floor(west / 3) * 3, math.floor((east - 1e-9) / 3) * 3 + 1, 3):
            urls.append(worldcover_url(la, lo))
    return urls


def read_landcover(west, south, east, north, res_m: float = 100.0):
    """
    Read WorldCover for a bbox, downsampled to about res_m metres (uses the COG overviews,
    so a 100 m read downloads ~100x less than full 10 m). Returns (classes uint8, transform).
    """
    res_deg = res_m / 111_320.0
    datasets = []
    try:
        for url in worldcover_tiles(west, south, east, north):
            ds = open_tile(url)  # None only if the tile doesn't exist (open ocean); network errors raise
            if ds is not None:
                datasets.append(ds)
    except Exception:
        for d in datasets:
            d.close()
        raise
    if not datasets:
        warnings.warn("No WorldCover tiles for this bbox (open ocean?).")
        w = max(1, round((east - west) / res_deg)); h = max(1, round((north - south) / res_deg))
        return np.zeros((h, w), np.uint8), rasterio.transform.from_bounds(west, south, east, north, w, h)
    try:
        mosaic, transform = with_retries(lambda: merge(
            datasets, bounds=(west, south, east, north), res=(res_deg, res_deg), nodata=0,
            resampling=Resampling.nearest))
    finally:
        for d in datasets:
            d.close()
    return mosaic[0].astype(np.uint8), transform
