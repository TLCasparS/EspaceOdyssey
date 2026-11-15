"""GLiM rock class for every place of the night runs -> data/material/rock_classes.csv.

Points: Polar = bowl low point (low_lon, low_lat), Mare = base spot (base_lon, base_lat).
Reads out/ only. Display / proposal data: changes no score and no export.

    python src/compute_rock_classes.py                       # PANGAEA 0.5 deg grid (default)
    python src/compute_rock_classes.py --gdb "<path>/LiMW_GIS 2015.gdb" --layer <name> --field xx
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.material import CODES, GridSource, PolygonFileSource, classify_point  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "espaceodyssey_data"
DEFAULT_GRID = DATA_HOME / "glim_pangaea_0p5deg" / "extracted" / "glim_wgs84_0point5deg.txt.asc"
RUNS = {"polar": ("night_polar", "low_lon", "low_lat"), "mare": ("night_mare", "base_lon", "base_lat")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-root", default=str(ROOT / "out"), help="folder with night_polar/ and night_mare/")
    ap.add_argument("--grid", default=str(DEFAULT_GRID))
    ap.add_argument("--gdb", help="full GLiM polygons instead of the grid")
    ap.add_argument("--layer")
    ap.add_argument("--field", default="xx")
    ap.add_argument("--radius-km", type=float, default=5.0)
    ap.add_argument("--dest", default=str(ROOT / "data" / "material" / "rock_classes.csv"))
    a = ap.parse_args(argv)

    if a.gdb:
        src, src_name = PolygonFileSource(a.gdb, layer=a.layer, class_field=a.field), f"GLiM polygons {a.gdb}"
    else:
        src, src_name = GridSource(a.grid), "GLiM 0.5 deg grid, PANGAEA doi:10.1594/PANGAEA.788537 (CC-BY 3.0)"
    print("source:", src_name)

    rows = []
    for run, (folder, lon_col, lat_col) in RUNS.items():
        df = pd.read_csv(Path(a.out_root) / folder / "ranking.csv")
        t = time.time()
        for _, r in df.iterrows():
            res = classify_point(float(r[lon_col]), float(r[lat_col]), src, a.radius_km)
            rows.append({"run": run, "rank": int(r["rank"]), "cell": r["id"],
                         "lon": round(float(r[lon_col]), 5), "lat": round(float(r[lat_col]), 5),
                         "point": "low point" if run == "polar" else "base spot",
                         "ROCK_CLASS": res["rock_class"] or "", "covered_share": res["covered_share"],
                         **{f"share_{c}": ("" if res[f"share_{c}"] is None else res[f"share_{c}"])
                            for c in CODES}})
        print(f"{run}: {len(df)} places in {time.time() - t:.1f} s")

    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", dest, len(rows), "rows")


if __name__ == "__main__":
    main()
