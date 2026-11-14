"""Fetch Copernicus DEM GLO-30 and ESA WorldCover 2021 for a bounding box.

Primary source: Microsoft Planetary Computer (STAC search + signed COG URLs, no account).
Fallback: the public AWS buckets (same COG files, no account):
  DEM:        https://copernicus-dem-30m.s3.amazonaws.com/
  WorldCover: https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/

If Planetary Computer fails or takes longer than `pc_timeout_s`, the AWS buckets are used.
Both rasters come back in their native lon/lat grid (EPSG:4326); they have different
pixel sizes (DEM 1 arcsec N-S, WorldCover 1/12000 deg), so each has its own transform.
Use terrain.py to put them on one metric grid.

Usage:
    region = fetch_region((-89.9, 75.25, -89.4, 75.5))   # west, south, east, north
    region.dem, region.worldcover
"""
from __future__ import annotations

import concurrent.futures as cf
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dem.fetch import open_tile, tiles_for_bbox, with_retries  # noqa: E402  (sets unsigned S3 access)

PC_DEM_COLLECTION = {30: "cop-dem-glo-30", 90: "cop-dem-glo-90"}
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
WC_AWS_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
              "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif")

# Fail fast on stalled HTTP reads instead of hanging (GDAL reads env vars at open time).
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "30")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "1")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")

# ESA WorldCover v200 class codes
WORLDCOVER_CLASSES = {
    10: "tree_cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built_up",
    60: "bare_sparse", 70: "snow_ice", 80: "water", 90: "herbaceous_wetland",
    95: "mangroves", 100: "moss_lichen",
}


@dataclass
class Region:
    bbox: tuple[float, float, float, float]   # west, south, east, north (deg)
    dem: np.ndarray                           # float32 metres, NaN = no data
    dem_transform: "rasterio.Affine"
    worldcover: np.ndarray                    # uint8 class codes, 0 = no data
    wc_transform: "rasterio.Affine"
    crs: str = "EPSG:4326"
    source: str = ""                          # "planetary_computer" or "aws"


def _mosaic(urls: list[str], bbox, nodata, dtype) -> tuple[np.ndarray, "rasterio.Affine"]:
    """Read only the bbox window from each COG and merge them."""
    import rasterio
    from rasterio.merge import merge

    sources = []
    try:
        for u in urls:
            ds = open_tile(u)   # None only if the tile does not exist (ocean); network errors raise
            if ds is not None:
                sources.append(ds)
        if not sources:
            raise RuntimeError(f"no tiles exist for bbox {bbox}")
        # North of 50 deg, DEM tiles in different latitude bands have different longitude
        # spacing; merge onto the finest one instead of whichever tile came first.
        res = (min(s.res[0] for s in sources), min(s.res[1] for s in sources))
        arr, transform = with_retries(
            lambda: merge(sources, bounds=bbox, res=res, nodata=nodata, dtype=dtype))
    finally:
        for s in sources:
            s.close()
    return arr[0], transform


def _urls_planetary_computer(bbox, dem_res: int = 30) -> tuple[list[str], list[str]]:
    import planetary_computer
    import pystac_client

    cat = pystac_client.Client.open(PC_STAC, modifier=planetary_computer.sign_inplace)
    dem_items = cat.search(collections=[PC_DEM_COLLECTION[dem_res]], bbox=bbox).item_collection()
    wc_items = cat.search(collections=["esa-worldcover"], bbox=bbox,
                          query={"esa_worldcover:product_version": {"eq": "2.0.0"}}).item_collection()
    if len(dem_items) == 0:
        raise RuntimeError("Planetary Computer: no Copernicus DEM items for bbox")
    if len(wc_items) == 0:
        raise RuntimeError("Planetary Computer: no WorldCover 2021 items for bbox")
    return ([it.assets["data"].href for it in dem_items],
            [it.assets["map"].href for it in wc_items])


def _urls_aws(bbox, dem_res: int = 30) -> tuple[list[str], list[str]]:
    west, south, east, north = bbox
    dem = tiles_for_bbox(west, south, east, north, res=dem_res)
    wc = []
    # WorldCover tiles are 3x3 deg, named by their south-west corner.
    for la in range(math.floor(south / 3) * 3, math.floor((north - 1e-9) / 3) * 3 + 1, 3):
        for lo in range(math.floor(west / 3) * 3, math.floor((east - 1e-9) / 3) * 3 + 1, 3):
            tile = f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"
            wc.append(WC_AWS_URL.format(tile=tile))
    return dem, wc


def _read(bbox, url_fn, dem_res):
    dem_urls, wc_urls = url_fn(bbox, dem_res)
    dem, dem_tf = _mosaic(dem_urls, bbox, nodata=np.nan, dtype="float32")
    wc, wc_tf = _mosaic(wc_urls, bbox, nodata=0, dtype="uint8")
    return dem, dem_tf, wc, wc_tf


def _save(path: Path, arr, transform, nodata, source):
    import rasterio
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                       dtype=arr.dtype, crs="EPSG:4326", transform=transform, nodata=nodata,
                       compress="deflate") as dst:
        dst.write(arr, 1)
        dst.update_tags(source=source)


def _load(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.tags().get("source", "unknown")


def fetch_region(bbox: tuple[float, float, float, float], source: str = "auto",
                 pc_timeout_s: float = 90.0, cache_dir: str | Path | None = None,
                 name: str | None = None, verbose: bool = True, dem_res: int = 30) -> Region:
    """DEM + WorldCover for bbox = (west, south, east, north) in degrees.

    source: "auto" (Planetary Computer, AWS on error/timeout), "pc" or "aws".
    dem_res: 30 (GLO-30) or 90 (GLO-90, ~9x less data, for screening large areas).
    cache_dir: if given, results are stored as GeoTIFFs and reused on the next call.
    """
    bbox = tuple(float(v) for v in bbox)
    west, south, east, north = bbox
    if not (west < east and south < north):
        raise ValueError(f"bbox must be (west, south, east, north), got {bbox}")
    if dem_res not in PC_DEM_COLLECTION:
        raise ValueError("dem_res must be 30 or 90")
    log = print if verbose else (lambda *a, **k: None)

    if cache_dir is not None:
        stem = (name or "_".join(f"{v:.4f}" for v in bbox)) + ("" if dem_res == 30 else f"_glo{dem_res}")
        dem_p, wc_p = Path(cache_dir) / f"{stem}_dem.tif", Path(cache_dir) / f"{stem}_worldcover.tif"
        if dem_p.exists() and wc_p.exists():
            log(f"  using cached {dem_p.name}, {wc_p.name}")
            dem, dem_tf, src = _load(dem_p)
            wc, wc_tf, _ = _load(wc_p)
            return Region(bbox, dem.astype(np.float32), dem_tf, wc, wc_tf, source=f"{src} (cached)")

    result, used = None, None
    if source in ("auto", "pc"):
        t0 = time.time()
        pool = cf.ThreadPoolExecutor(max_workers=1)
        fut = pool.submit(_read, bbox, _urls_planetary_computer, dem_res)
        try:
            result = fut.result(timeout=pc_timeout_s if source == "auto" else None)
            used = "planetary_computer"
            log(f"  Planetary Computer: {time.time() - t0:.1f} s")
        except Exception as e:  # includes TimeoutError
            if source == "pc":
                raise
            reason = f"slower than {pc_timeout_s:.0f} s" if isinstance(e, cf.TimeoutError) else repr(e)
            log(f"  Planetary Computer failed ({reason}); falling back to AWS")
        finally:
            pool.shutdown(wait=False, cancel_futures=True)  # a stalled read is left to time out
    if result is None:
        if source not in ("auto", "aws"):
            raise ValueError(f"source must be 'auto', 'pc' or 'aws', got {source!r}")
        t0 = time.time()
        result = _read(bbox, _urls_aws, dem_res)
        used = "aws"
        log(f"  AWS: {time.time() - t0:.1f} s")

    dem, dem_tf, wc, wc_tf = result
    if cache_dir is not None:
        _save(dem_p, dem, dem_tf, nodata=np.nan, source=used)
        _save(wc_p, wc, wc_tf, nodata=0, source=used)
    return Region(bbox, dem, dem_tf, wc, wc_tf, source=used)


def bbox_around(lat: float, lon: float, half_km: float) -> tuple[float, float, float, float]:
    """(west, south, east, north) of a square of +-half_km around a point."""
    dlat = half_km / 110.574
    dlon = half_km / (111.320 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Fetch DEM + WorldCover for a bbox")
    p.add_argument("bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    p.add_argument("--source", default="auto", choices=["auto", "pc", "aws"])
    p.add_argument("--res", type=int, default=30, choices=[30, 90])
    p.add_argument("--cache-dir", default=None)
    a = p.parse_args()
    r = fetch_region(tuple(a.bbox), source=a.source, cache_dir=a.cache_dir, dem_res=a.res)
    print(f"source={r.source} dem={r.dem.shape} [{np.nanmin(r.dem):.0f}, {np.nanmax(r.dem):.0f}] m  "
          f"worldcover={r.worldcover.shape} classes={sorted(np.unique(r.worldcover).tolist())}")
