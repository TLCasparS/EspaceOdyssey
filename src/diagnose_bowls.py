"""Read-only diagnosis: which bowl-filter limit do the depressions of a region fail?

Same steps as run_pipeline (land-cover filter, 15 km cells, 60 m local-UTM grid with buffer,
priority-flood fill), but WITHOUT the size limits: every closed depression at least --min-depth deep
whose low point lies in a cell that passed the land-cover filter is listed with the limits it fails
(depth / width / elongation, from config polar.min_depression_depth_m, min_depression_width_m,
max_elongation). Changes no filter and writes no pipeline output.

    python src/diagnose_bowls.py --bbox 14.5 77.9 17.5 78.7 --name svalbard_nordenskiold
    -> out/<name>/bowl_diagnosis.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem.fetch import read_bbox  # noqa: E402
from dem.grid import metric_crs_for, reproject_dem  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.filters import padded_bbox, run_filter  # noqa: E402
from pipeline.polar import fill_depressions, longest_axis_m  # noqa: E402
from pipeline.run import cell_mask_on_grid, cut_window, pixel_lonlat  # noqa: E402


def depressions(mg, in_cell, min_depth_m):
    """All closed depressions >= min_depth_m whose low point is in the cell: depth, width, elongation."""
    depth = np.nan_to_num(fill_depressions(mg.dem) - mg.dem)
    lab, n = ndimage.label(depth > 1e-6, structure=np.ones((3, 3), bool))
    if n == 0:
        return []
    idx = np.arange(1, n + 1)
    dmax = ndimage.maximum(depth, lab, idx)
    low = ndimage.maximum_position(depth, lab, idx)
    count = ndimage.sum(np.ones_like(depth), lab, idx)
    out = []
    for k in range(n):
        r, c = (int(v) for v in low[k])
        if dmax[k] < min_depth_m or not in_cell[r, c]:
            continue
        width = 2 * np.sqrt(count[k] * mg.res_m ** 2 / np.pi)
        out.append({"low": (r, c), "depth_m": float(dmax[k]), "width_m": float(width),
                    "elongation": longest_axis_m(lab == k + 1, mg.res_m) / width})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--min-depth", type=float, default=20.0, help="ignore shallower depressions (noise)")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    cfg = load_config()
    p, g = cfg["polar"], cfg["grid"]
    t0 = time.time()
    rows, _, _, _ = run_filter(tuple(a.bbox), cfg, None, log=lambda *x: None)
    kept = [r for r in rows if r["keep"]]
    dem, prof = read_bbox(*padded_bbox(*a.bbox, p["buffer_m"] + 1000), res=30)
    print(f"{a.name}: {len(kept)}/{len(rows)} cells pass the land-cover filter; DEM read ({time.time() - t0:.0f} s)")
    found = []
    for cell in kept:
        lon_c, lat_c = (cell["west"] + cell["east"]) / 2, (cell["south"] + cell["north"]) / 2
        sub, sub_tf = cut_window(dem, prof["transform"], padded_bbox(cell["west"], cell["south"], cell["east"],
                                                                   cell["north"], p["buffer_m"]))
        mg = reproject_dem(sub, sub_tf, "EPSG:4326", res_m=g["res_m"], dst_crs=metric_crs_for(lon_c, lat_c),
                           resampling=g["resampling"])
        for d in depressions(mg, cell_mask_on_grid(mg, cell), a.min_depth):
            fails = [n for n, bad in (("depth", d["depth_m"] < p["min_depression_depth_m"]),
                                      ("width", d["width_m"] < p["min_depression_width_m"]),
                                      ("elongation", d["elongation"] > p["max_elongation"])) if bad]
            lon, lat = pixel_lonlat(mg, d["low"][0], d["low"][1])
            found.append({"cell": cell["id"], "lat": round(float(lat), 5), "lon": round(float(lon), 5),
                          "low_elev_m": round(float(mg.dem[d["low"]]), 1), "depth_m": round(d["depth_m"], 1),
                          "width_m": round(d["width_m"]), "elongation": round(d["elongation"], 2),
                          "fails": "+".join(fails) or "none"})
    path = os.path.join(a.out, a.name, "bowl_diagnosis.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "lat", "lon", "low_elev_m", "depth_m", "width_m", "elongation", "fails"])
        w.writeheader()
        w.writerows(found)
    print(f"  {len(found)} depressions >= {a.min_depth:g} m deep: {dict(Counter(x['fails'] for x in found))} "
          f"({time.time() - t0:.0f} s) -> {path}")


if __name__ == "__main__":
    main()
