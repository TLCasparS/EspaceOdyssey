#!/usr/bin/env python3
"""
Step 1 of the search: cut a large area into a grid and throw out cells that can't be
Moon analogs (vegetation, water, wetlands, built-up, populated, ocean), BEFORE the
expensive DEM analysis.

Examples (run from the repo root):
    python src/filter_cells.py --bbox 82 27 86 31 --name nepal_west
    python src/filter_cells.py --bbox -4 36.5 -1.5 38.5 --name andalusia --pop data/GHS_POP_4326_30ss.tif
    python src/filter_cells.py --bbox 83 28 85 30 --name mustang --keep-classes 60 70 100 --min-usable 0.6

Outputs in out/<name>/ :
    cells.csv        every cell: bounds, land-cover fractions, population, keep yes/no + reason
    cells.geojson    same, open in QGIS / geojson.io to see kept vs dropped cells
    survivors.txt    one ready-to-run analyze_bbox.py command per kept cell

Population (optional): download a GHS-POP grid in WGS84 (EPSG:4326), e.g. the 30 arcsec
version, from https://human-settlement.emergency.copernicus.eu/download.php and pass it
with --pop. Without it, WorldCover's built-up class is used as the only settlement filter.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # src/

from dem.landcover import CLASSES, read_landcover  # noqa: E402
from pipeline.cells import cell_area_km2, make_grid, window_of  # noqa: E402


class Population:
    """Reads a population-count raster (EPSG:4326) and returns people/km2 for a cell."""

    def __init__(self, path):
        import rasterio
        self.src = rasterio.open(path)
        if self.src.crs is None or self.src.crs.to_epsg() != 4326:
            raise SystemExit(f"--pop must be in WGS84 (EPSG:4326), got {self.src.crs}. "
                             "Download the 'WGS84 / 3 or 30 arcsec' version of GHS-POP.")

    def density(self, c):
        from rasterio.windows import from_bounds
        win = from_bounds(c["west"], c["south"], c["east"], c["north"], self.src.transform)
        win = win.round_offsets().round_lengths()
        a = self.src.read(1, window=win, boundless=True, fill_value=0).astype("float64")
        nd = self.src.nodata
        if nd is not None:
            a[a == nd] = 0
        a[a < 0] = 0
        return float(a.sum()) / max(cell_area_km2(c), 1e-9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    ap.add_argument("--name", default="search")
    ap.add_argument("--out", default="out")
    ap.add_argument("--cell-km", type=float, default=15.0, help="cell size (default 15 km = Artemis region size)")
    ap.add_argument("--keep-classes", nargs="+", type=int, default=[60],
                    help="WorldCover classes that count as usable (default: 60 bare/sparse; add 70 100 for polar)")
    ap.add_argument("--min-usable", type=float, default=0.7, help="min share of usable land per cell")
    ap.add_argument("--max-built", type=float, default=0.005, help="max share of built-up pixels")
    ap.add_argument("--max-water", type=float, default=0.10, help="max share of water + wetland + mangrove")
    ap.add_argument("--min-land", type=float, default=0.9, help="min share of cell covered by data (drops coast/ocean)")
    ap.add_argument("--pop", help="optional population raster (EPSG:4326, people per pixel)")
    ap.add_argument("--max-pop", type=float, default=5.0, help="max people per km2 (needs --pop)")
    ap.add_argument("--lc-res", type=float, default=100.0, help="land-cover read resolution in m (default 100)")
    ap.add_argument("--dem-res", type=int, default=30, choices=[30, 90], help="res written into survivors.txt")
    a = ap.parse_args()

    west, south, east, north = a.bbox
    cells = make_grid(west, south, east, north, a.cell_km)
    print(f"{len(cells)} cells of ~{a.cell_km} km. Reading WorldCover at {a.lc_res:.0f} m ...")
    lc, transform = read_landcover(west, south, east, north, a.lc_res)
    pop = Population(a.pop) if a.pop else None

    keep_set = np.array(a.keep_classes)
    rows = []
    for c in cells:
        rs, cs = window_of(c, transform, lc.shape)
        block = lc[rs, cs]
        n = block.size
        if n == 0:
            continue
        frac = {name: float((block == v).sum()) / n for v, name in CLASSES.items()}
        land = float((block != 0).sum()) / n
        usable = float(np.isin(block, keep_set).sum()) / n
        water = frac["water"] + frac["wetland"] + frac["mangrove"]
        density = pop.density(c) if pop else None

        reasons = []
        if land < a.min_land:
            reasons.append(f"ocean/no-data {1 - land:.0%}")
        if usable < a.min_usable:
            reasons.append(f"usable {usable:.0%}<{a.min_usable:.0%}")
        if frac["built"] > a.max_built:
            reasons.append(f"built-up {frac['built']:.1%}")
        if water > a.max_water:
            reasons.append(f"water/wetland {water:.0%}")
        if density is not None and density > a.max_pop:
            reasons.append(f"pop {density:.1f}/km2")

        rows.append({
            **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in c.items()},
            "keep": not reasons, "reason": "; ".join(reasons),
            "land": round(land, 4), "usable": round(usable, 4), "water_wet": round(water, 4),
            "pop_per_km2": None if density is None else round(density, 2),
            **{f"f_{k}": round(v, 4) for k, v in frac.items()},
        })

    kept = [r for r in rows if r["keep"]]
    kept.sort(key=lambda r: -r["usable"])

    out_dir = os.path.join(a.out, a.name)
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

    with open(os.path.join(out_dir, "survivors.txt"), "w") as f:
        for r in kept:
            f.write(f"python src/analyze_bbox.py --bbox {r['west']:.5f} {r['south']:.5f} "
                    f"{r['east']:.5f} {r['north']:.5f} --res {a.dem_res} --name {a.name}_{r['id']}\n")

    # Summary of why cells were dropped
    print(f"Kept {len(kept)} / {len(rows)} cells.")
    drop_counts = {}
    for r in rows:
        for reason in filter(None, r["reason"].split("; ")):
            key = reason.split(" ")[0]
            drop_counts[key] = drop_counts.get(key, 0) + 1
    if drop_counts:
        print("Drop reasons (a cell can have several):", drop_counts)
    for r in kept[:10]:
        print(f"  {r['id']}  usable {r['usable']:.0%}  bbox {r['west']:.3f} {r['south']:.3f} "
              f"{r['east']:.3f} {r['north']:.3f}")
    print(f"Wrote {out_dir}/cells.csv, cells.geojson, survivors.txt")


if __name__ == "__main__":
    main()
