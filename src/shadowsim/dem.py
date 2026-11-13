"""Load elevation data: Copernicus GLO-30 (free, global, 30 m) or a local GeoTIFF.

Copernicus GLO-30 is streamed from the public AWS bucket (no account needed):
https://registry.opendata.aws/copernicus-dem/
Each site is cropped (analysis area + horizon buffer) and cached in data/dem/.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

COP30_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/"
             "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
             "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")


@dataclass
class DemGrid:
    z: np.ndarray                          # elevation in metres, north-up
    dx_m: float                            # pixel size east-west
    dy_m: float                            # pixel size north-south
    lat: float                             # site centre
    lon: float
    window: tuple[int, int, int, int]      # analysis cells (row0, row1, col0, col1)

    @property
    def window_z(self) -> np.ndarray:
        r0, r1, c0, c1 = self.window
        return self.z[r0:r1, c0:c1]


def _tile_urls(south: float, north: float, west: float, east: float) -> list[str]:
    urls = []
    for la in range(math.floor(south), math.floor(north - 1e-9) + 1):
        for lo in range(math.floor(west), math.floor(east - 1e-9) + 1):
            urls.append(COP30_URL.format(ns="N" if la >= 0 else "S", lat=abs(la),
                                         ew="E" if lo >= 0 else "W", lon=abs(lo)))
    return urls


def _grid_from_array(z, transform, lat, lon, radius_km) -> DemGrid:
    dx = abs(transform.a) * 111_320.0 * math.cos(math.radians(lat))
    dy = abs(transform.e) * 110_574.0
    col_c, row_c = ~transform * (lon, lat)
    hr, hc = int(radius_km * 1000 / dy), int(radius_km * 1000 / dx)
    rc, cc = int(row_c), int(col_c)
    window = (max(rc - hr, 0), min(rc + hr + 1, z.shape[0]), max(cc - hc, 0), min(cc + hc + 1, z.shape[1]))
    return DemGrid(z=z, dx_m=dx, dy_m=dy, lat=lat, lon=lon, window=window)


def load_site(lat: float, lon: float, radius_km: float = 5.0, buffer_km: float = 20.0,
              cache_dir: str | Path = "data/dem", name: str | None = None,
              local_tif: str | Path | None = None) -> DemGrid:
    """Elevation around (lat, lon): analysis square of +-radius_km plus a horizon buffer."""
    import rasterio
    from rasterio.merge import merge
    from rasterio.windows import from_bounds

    half = radius_km + buffer_km
    dlat = half / 110.574
    dlon = half / (111.320 * math.cos(math.radians(lat)))
    bounds = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)  # west, south, east, north

    if local_tif is not None:
        with rasterio.open(local_tif) as src:
            win = from_bounds(*bounds, transform=src.transform)
            z = src.read(1, window=win, boundless=True, fill_value=np.nan, masked=False).astype(np.float32)
            transform = src.window_transform(win)
            if src.nodata is not None:
                z[z == src.nodata] = np.nan
        return _grid_from_array(np.nan_to_num(z, nan=0.0), transform, lat, lon, radius_km)

    cache = Path(cache_dir) / f"{name or f'{lat:.4f}_{lon:.4f}'}_r{radius_km:g}_b{buffer_km:g}.tif"
    if cache.exists():
        with rasterio.open(cache) as src:
            return _grid_from_array(src.read(1).astype(np.float32), src.transform, lat, lon, radius_km)

    sources = []
    for url in _tile_urls(bounds[1], bounds[3], bounds[0], bounds[2]):
        try:
            sources.append(rasterio.open(url))
        except rasterio.errors.RasterioIOError:
            pass  # tile does not exist (open ocean)
    if not sources:
        raise RuntimeError(f"No Copernicus tiles found around {lat}, {lon}")
    try:
        arr, transform = merge(sources, bounds=bounds, nodata=np.nan, dtype="float32")
        profile = sources[0].profile
    finally:
        for s in sources:
            s.close()
    z = np.nan_to_num(arr[0], nan=0.0)  # missing data = sea level

    cache.parent.mkdir(parents=True, exist_ok=True)
    profile.update(driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                   dtype="float32", transform=transform, nodata=None, compress="deflate")
    profile.pop("blockxsize", None); profile.pop("blockysize", None); profile.pop("tiled", None)
    with rasterio.open(cache, "w", **profile) as dst:
        dst.write(z, 1)
    return _grid_from_array(z, transform, lat, lon, radius_km)


def synthetic_crater(lat: float = 75.0, diameter_km: float = 20.0, depth_m: float = 2000.0,
                     rim_m: float = 400.0, pixel_m: float = 100.0, extent_km: float = 60.0,
                     radius_km: float = 15.0) -> DemGrid:
    """Simple bowl crater with a raised rim, for tests and demos (no internet needed)."""
    n = int(extent_km * 1000 / pixel_m) | 1
    x = (np.arange(n) - n // 2) * pixel_m / 1000.0
    xx, yy = np.meshgrid(x, -x)
    r = np.hypot(xx, yy) / (diameter_km / 2)
    inside = depth_m * (r ** 2 - 1) + rim_m
    outside = rim_m * np.exp(-((r - 1) / 0.35) ** 2)
    z = np.where(r < 1, inside, outside).astype(np.float32)
    hw = int(radius_km * 1000 / pixel_m)
    c = n // 2
    return DemGrid(z=z, dx_m=pixel_m, dy_m=pixel_m, lat=lat, lon=0.0,
                   window=(c - hw, c + hw + 1, c - hw, c + hw + 1))
