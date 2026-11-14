"""Copernicus GLO-90 with a local tile cache (night run: A1 bowl prescreen and B1 coarse Mare).

A GLO-90 tile is ONE 2048 px block on S3 (1200 x 1200 px at |lat| < 50), so any read of it downloads the whole
tile (~4.6 MB). Each tile is therefore downloaded once into <cache>/<name>.tif (or <name>.missing for ocean)
and reused by neighbouring tiles' buffers, by A1 and B1, and by several worker processes (atomic writes:
two workers fetching the same tile at once both write a complete file, the last os.replace wins).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from dem.fetch import NODATA, open_tile, tiles_for_bbox, with_retries


def _local(cache: Path, url: str) -> Path | None:
    """Path of the cached tile, downloading it first if needed; None if the tile does not exist (ocean)."""
    import rasterio
    name = url.rstrip("/").split("/")[-1]
    tif, missing = cache / name, cache / (name + ".missing")
    if tif.exists():
        return tif
    if missing.exists():
        return None
    cache.mkdir(parents=True, exist_ok=True)
    ds = open_tile(url)
    if ds is None:
        missing.write_text("no tile")
        return None
    with ds:
        arr = with_retries(lambda: ds.read(1))
        prof = ds.profile.copy()
    prof.update(driver="GTiff", compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256)
    tmp = cache / (name + f".tmp{os.getpid()}")
    with rasterio.open(tmp, "w", **prof) as dst:
        dst.write(arr, 1)
    os.replace(tmp, tif)
    return tif


def read_glo90(west, south, east, north, cache: Path):
    """(elevation float32 with NaN, profile) for the bbox from cached GLO-90 tiles (finest grid, like read_bbox)."""
    import rasterio
    from rasterio.merge import merge
    paths = [p for p in (_local(cache, u) for u in tiles_for_bbox(west, south, east, north, 90)) if p is not None]
    if not paths:
        raise RuntimeError("no GLO-90 tiles for this bbox (all ocean)")
    srcs = [rasterio.open(p) for p in paths]
    try:
        res = (min(s.res[0] for s in srcs), min(s.res[1] for s in srcs))
        mosaic, tf = merge(srcs, bounds=(west, south, east, north), res=res, nodata=NODATA)
        crs = srcs[0].crs
    finally:
        for s in srcs:
            s.close()
    z = mosaic[0].astype(np.float32)
    z[z <= NODATA + 1] = np.nan
    return z, {"transform": tf, "crs": crs}


def cached_tiles(cache: Path) -> list[Path]:
    return sorted(cache.glob("*.tif")) if cache.exists() else []
