"""Read a square window around the lunar south pole from a LOLA DEM over HTTP (GDAL /vsicurl/,
range requests) without downloading the whole file.

Default source: LDEM_80S_20MPP_ADJ.TIF (20 m, 80-90 S, 2.7 GB), PGDA product 90
"A New View of the Lunar South Pole from LOLA" (Barker et al. 2023). The page states all its TIFs
are cloud-optimised GeoTIFFs (512 px tiles + overviews), so only the needed tiles travel.
(The 5 m 87S mosaic ldem_87s_5mpp.tif failed this way on 14 Nov 2026: broken / empty tile reads.)

    python src/fetch_lola_window.py                      # +-25 km at native 20 m -> data/moon/shackleton_20m_window.tif
    python src/fetch_lola_window.py --half-km 30 --x0 5000 --y0 -8000

CRS: south polar stereographic, x/y in metres, MOON_ME frame (DE421). Heights in metres, NaN = no data.
Any further resampling (to the common 60 m grid) happens later in dem.grid.reproject_dem.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.env import Env
from rasterio.windows import from_bounds

URL = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF"
OUT = Path(__file__).resolve().parents[1] / "data" / "moon" / "shackleton_20m_window.tif"


def read_window(half_km: float = 25.0, x0: float = 0.0, y0: float = 0.0, url: str = URL):
    """Native-resolution window of +-half_km around (x0, y0) in the file's CRS -> (z, transform, crs)."""
    h = half_km * 1000
    with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
             GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open("/vsicurl/" + url) as src:
            win = from_bounds(x0 - h, y0 - h, x0 + h, y0 + h, src.transform).round_offsets().round_lengths()
            z = src.read(1, window=win, masked=False).astype(np.float32)
            if src.nodata is not None and not np.isnan(src.nodata):
                z[z == src.nodata] = np.nan
            return z, src.window_transform(win), src.crs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--half-km", type=float, default=25.0)
    ap.add_argument("--x0", type=float, default=0.0, help="window centre x (m, polar stereographic)")
    ap.add_argument("--y0", type=float, default=0.0, help="window centre y (m)")
    ap.add_argument("--url", default=URL)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    t0 = time.time()
    z, tf, crs = read_window(a.half_km, a.x0, a.y0, a.url)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(a.out, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1,
                       dtype="float32", crs=crs, transform=tf, nodata=np.nan, compress="deflate",
                       tiled=True) as dst:
        dst.write(z, 1)
        dst.update_tags(source=a.url, read=f"+-{a.half_km:g} km around ({a.x0:g}, {a.y0:g}) m, native resolution, /vsicurl/")
    print(f"{z.shape[1]}x{z.shape[0]} px at {tf.a:g} m, {np.isnan(z).mean():.2%} NaN, "
          f"z {np.nanmin(z):.0f}..{np.nanmax(z):.0f} m, {time.time() - t0:.0f} s -> {a.out}")


if __name__ == "__main__":
    main()
