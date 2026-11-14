"""Lunar target values for the Polar criteria, computed with the Earth pipeline's own code.

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
Output: prints the values; with --write, fills config/lunar_targets.json (value, source,
        verified=false). A person flips "verified" to true after checking each number.

Usage (from the repo root):
    python src/moon_targets.py https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
    python src/moon_targets.py <dem.tif> --write
"""
from __future__ import annotations

import argparse
import datetime as dt
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

# Criteria whose lunar value is not used, and why (kept null in lunar_targets.json).
NOT_USED = {
    "c14_aspect": "Shackleton's rim touches the lunar south pole and the Sun circles the whole horizon "
                  "there, so 'facing the pole' does not mean 'less sun' as it does on Earth. "
                  "Computed value kept in the note for reference only.",
}
TODO_NOTES = {
    "c10_flat_base": "TODO: with max_base_to_low_km = 5 the pad is searched within 5 km of the low point, "
                     "i.e. on Shackleton's floor/lower wall (permanently dark), not on the rim where "
                     "NASA's base sites are (~10 km out). Kept as is for v1; revisit the search radius.",
    "c11_walls": "TODO: the wall ring (polar.wall_ring_m = 500-3000 m from the low point) covers Shackleton's "
                 "floor and the foot of its walls; the steep inner walls run ~3-10 km out, so this value "
                 "understates them. Kept as is for v1; revisit a ring scaled to the depression size.",
}


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
    ap.add_argument("--write", action="store_true", help="fill config/lunar_targets.json")
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

    values = {name: shack.get(name) for name in CRITERIA}
    values["c13_roughness"] = info["c13_roughness"]
    for name in CRITERIA:
        flag = "  (not used: see note)" if name in NOT_USED else ""
        print(f"  {name:15s} {values[name]}{flag}")

    if not a.write:
        print("\nDry run. Add --write to fill config/lunar_targets.json.")
        return

    src_name = os.path.basename(a.dem)
    source = (f"LOLA {src_name} (NASA PGDA; native {src_res:g} m) -> {res_m:g} m {resampling}, "
              f"src/moon_targets.py, {dt.date.today().isoformat()}")
    with open(TARGETS_PATH, encoding="utf-8") as f:
        targets = json.load(f)
    pol = targets["polar"]
    for name in CRITERIA:
        c = pol["criteria"][name]
        if name in NOT_USED:
            c.update(value=None, source=None, verified=False,
                     note=f"{NOT_USED[name]} Computed: {values[name]}.")
            continue
        c.update(value=values[name], source=source, verified=False)
        if name in TODO_NOTES:
            c["note"] = TODO_NOTES[name]
    pol["status"] = ("computed by src/moon_targets.py; verified=false until a person checks each value "
                     "against the quicklook and the definition")
    pol["window"] = (f"15 km cell centred on Shackleton ({SHACKLETON_LAT}, {SHACKLETON_LON}) in lunar south "
                     f"polar stereographic, read with polar.buffer_m = {buf:g} m; widest depression in the cell")
    pol["grid"] = {"res_m": res_m, "crs": "lunar south polar stereographic (R = 1737.4 km)",
                   "resampling": resampling}
    pol["computed"] = {"n_depressions_in_cell": len(deps), "spill_depth_m": shack["c7_depth_m"],
                       "depression_width_m": shack["c7_width_m"], "low_elev_m": shack["low_elev_m"],
                       "base_to_low_km": shack["base_to_low_km"], "base_elev_m": shack["base_elev_m"]}
    with open(TARGETS_PATH, "w", encoding="utf-8") as f:
        json.dump(targets, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nWrote {TARGETS_PATH.relative_to(Path.cwd()) if TARGETS_PATH.is_relative_to(Path.cwd()) else TARGETS_PATH}")


if __name__ == "__main__":
    np.seterr(invalid="ignore")
    main()
