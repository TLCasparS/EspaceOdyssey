#!/usr/bin/env python3
"""
Fetch Copernicus DEM for a bounding box and compute terrain metrics.

Examples (run from the repo root):
    python src/analyze_bbox.py --bbox 83.6 28.7 84.0 29.1 --name mustang
    python src/analyze_bbox.py --bbox -3.05 37.40 -2.85 37.55 --name gorafe
    python src/analyze_bbox.py --bbox 83 28 85 30 --res 90 --name mustang_wide --no-tifs

Outputs in out/<name>/ :
    summary.json              stats for elevation, slope, roughness, relief, TRI
    elevation.tif, slope_deg.tif, roughness_m.tif, relief_m.tif, tri_m.tif   (unless --no-tifs)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # src/

from dem.fetch import read_bbox, save_tif  # noqa: E402
from dem.terrain import pixel_size_m, summarize  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", nargs=4, type=float, required=True,
                    metavar=("WEST", "SOUTH", "EAST", "NORTH"), help="degrees, WGS84")
    ap.add_argument("--res", type=int, default=30, choices=[30, 90])
    ap.add_argument("--name", default="area")
    ap.add_argument("--out", default="out")
    ap.add_argument("--relief-window-m", type=float, default=1000.0)
    ap.add_argument("--no-tifs", action="store_true", help="only write summary.json")
    a = ap.parse_args()

    west, south, east, north = a.bbox
    print(f"Reading Copernicus DEM {a.res} m for {a.bbox} ...")
    elev, profile = read_bbox(west, south, east, north, res=a.res)

    dx, dy = pixel_size_m(profile["transform"], (south + north) / 2)
    summary, layers = summarize(elev, dx, dy, a.relief_window_m)
    summary = {"name": a.name, "bbox": a.bbox, "res": a.res, **summary}

    out_dir = os.path.join(a.out, a.name)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    if not a.no_tifs:
        for layer_name, arr in layers.items():
            save_tif(os.path.join(out_dir, f"{layer_name}.tif"), arr, profile)

    print(json.dumps({k: summary[k] for k in
                      ("pixel_size_m", "valid_fraction", "frac_slope_lt_5deg", "frac_slope_lt_10deg")}, indent=2))
    print(f"Slope median: {summary['slope_deg']['median']} deg | "
          f"Relief median: {summary['relief_m']['median']} m")
    print(f"Wrote {out_dir}/")


if __name__ == "__main__":
    main()
