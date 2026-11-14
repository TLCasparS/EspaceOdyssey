"""CROSS-CHECK ONLY: recompute the Polar lunar targets independently and compare them with
config/lunar_targets.json. It never writes that file: src/compute_lunar_target.py is the one
script that produces the targets (agreed 14 Nov 2026).

Lunar target values for the Polar criteria, computed with the Earth pipeline's own code.

Shackleton is treated exactly like one Earth cell:
  - a 15 km cell (grid.cell_km) centred on the crater, read with the same buffer (polar.buffer_m),
  - resampled to the same 60 m grid (dem.grid.reproject_dem, grid.resampling from the config),
  - every pixel usable (no land cover on the Moon),
  - criteria from src/pipeline/polar.py, unchanged.
The one Moon-specific choice: the cell may contain several depressions (small craters on the rim
or floor); the target is Shackleton itself, so the WIDEST depression is used, not the cell's
"best" candidate.

Input : a LOLA LDEM GeoTIFF in lunar south polar stereographic metres, local path or https URL
        (cloud-optimized: only the window is downloaded). Recommended source:
        https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
Output: a table of this script's values next to config/lunar_targets.json and the difference.
        The window differs on purpose (cell centred on the IAU crater coordinates, not on the
        low point found from the data), so small differences are expected.

Usage (from the repo root):
    python src/moon_targets.py https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dem.grid import reproject_dem  # noqa: E402
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.polar import CRITERIA, polar_candidates  # noqa: E402

# Shackleton centre (IAU Gazetteer of Planetary Nomenclature; check before it goes on a slide).
SHACKLETON_LAT, SHACKLETON_LON = -89.67, 129.8
MOON_SPS = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"
MOON_LL = "+proj=longlat +R=1737400 +no_defs"

def read_window(path: str, half_m: float):
    """Native-resolution DEM window of +-half_m around Shackleton (only those bytes are read)."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import from_bounds

    if path.startswith(("http://", "https://")):
        path = "/vsicurl/" + path
    with rasterio.open(path) as src:
        crs = src.crs or CRS.from_proj4(MOON_SPS)
        xs, ys = warp_transform(CRS.from_proj4(MOON_LL), crs, [SHACKLETON_LON], [SHACKLETON_LAT])
        cx, cy = xs[0], ys[0]
        b = src.bounds
        if cx - half_m < b.left or cx + half_m > b.right or cy - half_m < b.bottom or cy + half_m > b.top:
            raise SystemExit(f"{os.path.basename(path)} does not cover the full cell + buffer "
                             f"(+-{half_m / 1000:.1f} km around Shackleton). Use the 20 m south-pole LDEM.")
        win = from_bounds(cx - half_m, cy - half_m, cx + half_m, cy + half_m, transform=src.transform)
        z = src.read(1, window=win, masked=True).astype("float32").filled(np.nan)
        tf = src.window_transform(win)
        res = abs(src.transform.a)
    return z, tf, crs, (cx, cy), res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dem", help="LOLA LDEM GeoTIFF path or https URL")
    a = ap.parse_args()

    cfg = load_config()
    cell_half = cfg["grid"]["cell_km"] * 1000 / 2
    buf = cfg["polar"]["buffer_m"]
    res_m, resampling = cfg["grid"]["res_m"], cfg["grid"]["resampling"]

    z, tf, crs, (cx, cy), src_res = read_window(a.dem, cell_half + buf)
    print(f"source: {os.path.basename(a.dem)}  native {src_res:g} m  window {z.shape[1]}x{z.shape[0]} px")
    mg = reproject_dem(z, tf, crs, res_m=res_m, resampling=resampling)  # projected source: keeps the lunar CRS

    # Cell = pixel centres within +-cell_half of the crater centre (the lunar analogue of a lon/lat cell).
    rr, cc = np.indices(mg.dem.shape)
    px = mg.transform.c + (cc + 0.5) * mg.transform.a
    py = mg.transform.f + (rr + 0.5) * mg.transform.e
    in_cell = (np.abs(px - cx) < cell_half) & (np.abs(py - cy) < cell_half)
    usable = np.ones_like(in_cell)                                    # no land cover on the Moon

    info, cands = polar_candidates(mg, in_cell, usable, SHACKLETON_LAT, cfg)
    deps = [c for c in cands if c["anchor"] == "depression"]
    if not deps:
        raise SystemExit("no qualifying depression found in the cell - check the DEM window")
    shack = max(deps, key=lambda c: c["c7_width_m"])
    print(f"{len(deps)} depression(s) in the cell; using the widest: "
          f"{shack['c7_width_m'] / 1000:.1f} km wide, {shack['c7_depth_m']:.0f} m spill depth, "
          f"low point {shack['low_elev_m']:.0f} m")
    print(f"base pad: {shack['base_to_low_km']} km from the low point at {shack['base_elev_m']} m"
          f"{'  (REJECTED: ' + shack['reason'] + ')' if not shack['keep'] else ''}")

    values = {name: shack.get(name) for name in CRITERIA}   # c13 is per place since 14 Nov
    with open(TARGETS_PATH, encoding="utf-8") as f:
        ref = json.load(f)["polar"]["criteria"]
    print(f"\n  {'criterion':15s} {'this script':>12s} {'targets file':>13s} {'diff':>7s}  verified")
    for name in CRITERIA:
        mine, theirs = values[name], ref.get(name, {}).get("value")
        diff = (f"{100 * (mine - theirs) / abs(theirs):+.1f}%"
                if mine is not None and theirs not in (None, 0) else "")
        print(f"  {name:15s} {str(mine):>12s} {str(theirs):>13s} {diff:>7s}  {ref.get(name, {}).get('verified')}")
    print("\nCross-check only: config/lunar_targets.json is written by src/compute_lunar_target.py.")


if __name__ == "__main__":
    np.seterr(invalid="ignore")
    main()
