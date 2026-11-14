#!/usr/bin/env python3
"""
Step 1 of the search: cut a large area into ~15 km cells and drop cells that can't be Moon
analogs (land-cover blacklist + buffers around built-up and water, ocean, population),
BEFORE the expensive DEM analysis. No slope filter here.

All thresholds are in config/pipeline.yaml (section `filter`); rules in src/pipeline/filters.py.

Examples (run from the repo root):
    python src/filter_cells.py --bbox 83 28 85 30 --name mustang_polar
    python src/filter_cells.py --bbox -4 36.5 -1.5 38.5 --name andalusia --pop data/GHS_POP_4326_30ss.tif

Outputs in out/<name>/ :
    cells.csv         every cell: bounds, land-cover shares, masking, patch size, keep + reason
    cells.geojson     same, open in QGIS / geojson.io
    usable_mask.tif   usable pixels (1) on the land-cover grid, for the base-spot step
    survivors.txt     one ready-to-run analyze_bbox.py command per kept cell

Population (optional): GHS-POP in WGS84 (EPSG:4326), e.g. the 30 arcsec version from
https://human-settlement.emergency.copernicus.eu/download.php, passed with --pop.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # src/

from pipeline.config import load_config  # noqa: E402
from pipeline.filters import run_filter  # noqa: E402


def write_outputs(out_dir, rows, lc_transform, usable, dem_res, name):
    import rasterio
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "cells.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    features = [{
        "type": "Feature",
        "properties": {k: v for k, v in r.items() if k not in ("west", "south", "east", "north")},
        "geometry": {"type": "Polygon", "coordinates": [[
            [r["west"], r["south"]], [r["east"], r["south"]], [r["east"], r["north"]],
            [r["west"], r["north"]], [r["west"], r["south"]]]]},
    } for r in rows]
    with open(os.path.join(out_dir, "cells.geojson"), "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    with rasterio.open(os.path.join(out_dir, "usable_mask.tif"), "w", driver="GTiff",
                       height=usable.shape[0], width=usable.shape[1], count=1, dtype="uint8",
                       crs="EPSG:4326", transform=lc_transform, compress="deflate") as dst:
        dst.write(usable.astype("uint8"), 1)
    with open(os.path.join(out_dir, "survivors.txt"), "w") as f:
        for r in rows:
            if r["keep"]:
                f.write(f"python src/analyze_bbox.py --bbox {r['west']:.5f} {r['south']:.5f} "
                        f"{r['east']:.5f} {r['north']:.5f} --res {dem_res} --name {name}_{r['id']}\n")


def print_summary(rows):
    kept = [r for r in rows if r["keep"]]
    print(f"Kept {len(kept)} / {len(rows)} cells, dropped {len(rows) - len(kept)}.")
    any_reason, only_reason = Counter(), Counter()
    for r in rows:
        keys = [s.split(" ")[0] for s in filter(None, r["reason"].split("; "))]
        any_reason.update(keys)
        if len(keys) == 1:
            only_reason[keys[0]] += 1
    if any_reason:
        print("Drop reasons (a cell can have several):", dict(any_reason))
        print("Cells dropped for exactly one reason:  ", dict(only_reason))
    for r in sorted(kept, key=lambda r: -r["usable"])[:10]:
        print(f"  {r['id']}  usable {r['usable']:.0%}  patch {r['largest_patch_km2']:.0f} km2  "
              f"bbox {r['west']:.3f} {r['south']:.3f} {r['east']:.3f} {r['north']:.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    ap.add_argument("--name", default="search")
    ap.add_argument("--out", default="out")
    ap.add_argument("--config", default=None, help="default: config/pipeline.yaml")
    ap.add_argument("--pop", help="optional population raster (EPSG:4326, people per pixel)")
    ap.add_argument("--dem-res", type=int, default=30, choices=[30, 90], help="res written into survivors.txt")
    a = ap.parse_args()

    cfg = load_config(a.config)
    rows, lc, transform, masks = run_filter(tuple(a.bbox), cfg, a.pop)
    out_dir = os.path.join(a.out, a.name)
    write_outputs(out_dir, rows, transform, masks["usable"], a.dem_res, a.name)
    print_summary(rows)
    print(f"Wrote {out_dir}/cells.csv, cells.geojson, usable_mask.tif, survivors.txt")


if __name__ == "__main__":
    main()
