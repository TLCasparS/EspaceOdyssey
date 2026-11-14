#!/usr/bin/env python3
"""
Polar pipeline, one command: bbox -> land-cover filter -> terrain criteria 7, 9, 10, 11, 13, 14
per surviving cell (60 m local UTM grid) -> weighted score -> ranking.

Examples (run from the repo root):
    python src/run_pipeline.py --bbox 83 28 85 30 --name mustang_polar
    python src/run_pipeline.py --bbox 83 28 85 30 --name mustang_polar --res 90     # faster screening

Outputs in out/<name>/ :
    ranking.csv     ranked surviving cells: score, raw value + score + method per criterion
    cells.geojson   every cell (kept and dropped, with reasons and all values), for the map
    radar.json      per ranked cell: 0-1 score per criterion (+ lunar target placeholders)
    run_info.json   bbox, data sources, config used
Thresholds and weights: config/pipeline.yaml.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # src/

from pipeline.config import load_config  # noqa: E402
from pipeline.polar import CRITERIA  # noqa: E402
from pipeline.run import run  # noqa: E402

SHORT = {"c7_bowl": "7 bowl", "c9_relief": "9 relief m", "c10_flat_base": "10 base deg",
         "c11_walls": "11 walls deg", "c13_roughness": "13 rough m", "c14_aspect": "14 pole"}


def fmt(v, nd=2):
    return "  -  " if v is None else f"{v:.{nd}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    ap.add_argument("--name", default="polar")
    ap.add_argument("--out", default="out")
    ap.add_argument("--res", type=int, default=30, choices=[30, 90], help="Copernicus GLO-30 or GLO-90")
    ap.add_argument("--config", default=None)
    ap.add_argument("--pop", help="optional GHS-POP raster (EPSG:4326)")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    cfg = load_config(a.config)
    rows, ranked = run(tuple(a.bbox), a.name, cfg, a.res, a.pop, a.out)

    print(f"\nTop {min(a.top, len(ranked))} (raw value [score]; rank scores only comparable within this run):")
    head = f"{'#':>3} {'cell':9} {'score':>5} {'n':>2} " + " ".join(f"{SHORT[c]:>17}" for c in CRITERIA)
    print(head)
    for r in ranked[:a.top]:
        vals = []
        for c in CRITERIA:
            nd = 0 if c == "c9_relief" else (3 if c in ("c7_bowl",) else 1 if c in ("c10_flat_base", "c11_walls", "c13_roughness") else 2)
            vals.append(f"{fmt(r[c], nd):>9} [{fmt(r['s_' + c])}]")
        print(f"{r['rank']:>3} {r['id']:9} {r['score']:5.3f} {r['n_scored']:>2} " + " ".join(f"{v:>17}" for v in vals))
    print("\nlocation of the top cells (cell centre / base spot / low point, lon lat):")
    for r in ranked[:a.top]:
        print(f"  {r['id']}  centre {r['lon']:.3f} {r['lat']:.3f}   base {r['base_lon']} {r['base_lat']}"
              f"   low {r['low_lon']} {r['low_lat']} ({r['low_elev_m']} m)")


if __name__ == "__main__":
    main()
