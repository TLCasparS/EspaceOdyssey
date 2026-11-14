"""Terrain + land-cover summary per site -> data/results/scores.csv (one row per site).

Usage (from the repo root):
    python src/run_terrain_sites.py --only haughton_crater
    python src/run_terrain_sites.py                    # all sites in data/sites.csv

Each site: fetch DEM + WorldCover for the analysis square plus a buffer, reproject to
a metric grid, compute terrain metrics, summarise them over the analysis square.
Re-running a site replaces its row; other rows are kept.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_region import WORLDCOVER_CLASSES, bbox_around, fetch_region  # noqa: E402
from terrain import compute_terrain, crop_center, to_metric_grid  # noqa: E402

VEGETATED = (10, 20, 30, 40, 90, 95, 100)


def summarise(name, lat, lon, half_km, region, mg, t) -> dict:
    crop = lambda a: crop_center(a, mg, lon, lat, half_km)
    z, slope, relief, rough, tri, wc = (crop(a) for a in (mg.dem, t.slope_deg, t.relief_m,
                                                          t.roughness_m, t.tri_m, mg.worldcover))
    q = lambda a, p: float(np.nanpercentile(a, p))
    s = slope[np.isfinite(slope)]
    sfrac = lambda mask: round(float(mask.mean()), 3) if s.size else float("nan")
    classes = wc[wc > 0]
    frac = lambda codes: float(np.isin(classes, codes).mean()) if classes.size else float("nan")
    codes, counts = np.unique(classes, return_counts=True)
    return {
        "name": name, "lat": lat, "lon": lon, "half_width_km": half_km,
        "dem_source": region.source, "crs": mg.crs, "res_m": mg.res_m,
        "valid_dem_frac": round(float(np.isfinite(z).mean()), 3),
        "elev_min_m": round(float(np.nanmin(z)), 1), "elev_max_m": round(float(np.nanmax(z)), 1),
        "slope_median_deg": round(q(slope, 50), 2), "slope_p90_deg": round(q(slope, 90), 2),
        # same slope thresholds as dem.terrain.summarize
        "frac_slope_lt_5deg": sfrac(s < 5), "frac_slope_lt_10deg": sfrac(s < 10),
        "frac_slope_gt_30deg": sfrac(s > 30),
        f"relief{round(t.relief_window_m / 1000, 1):g}km_median_m": round(q(relief, 50), 1),
        f"relief{round(t.relief_window_m / 1000, 1):g}km_max_m": round(float(np.nanmax(relief)), 1),
        f"roughness{t.roughness_window_px}px_median_m": round(q(rough, 50), 2),
        f"roughness{t.roughness_window_px}px_p90_m": round(q(rough, 90), 2),
        "tri_median_m": round(q(tri, 50), 2), "tri_p90_m": round(q(tri, 90), 2),
        "frac_bare_sparse": round(frac([60]), 3),
        "frac_snow_ice": round(frac([70]), 3),
        "frac_water": round(frac([80]), 3),
        "frac_vegetated": round(frac(VEGETATED), 3),
        "dominant_landcover": WORLDCOVER_CLASSES.get(int(codes[counts.argmax()]), "?") if codes.size else "",
    }


def upsert(path: Path, row: dict):
    rows = []
    if path.exists():
        with open(path, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["name"] != row["name"]]
    rows.append(row)
    fields = list(row)
    for r in rows:
        fields += [k for k in r if k not in fields]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sites", default="data/sites.csv")
    p.add_argument("--only", help="run just this site name")
    p.add_argument("--half-km", type=float, default=15.0, help="half-width of the analysis square")
    p.add_argument("--res-m", type=float, default=30.0, help="pixel size of the metric grid")
    p.add_argument("--dem-res", type=int, default=30, choices=[30, 90], help="GLO-30 or GLO-90")
    p.add_argument("--relief-km", type=float, default=5.0)
    p.add_argument("--rough-px", type=int, default=3)
    p.add_argument("--source", default="auto", choices=["auto", "pc", "aws"])
    p.add_argument("--cache-dir", default="data/region")
    p.add_argument("--out", default="data/results/scores.csv")
    a = p.parse_args()

    with open(a.sites, newline="") as f:
        sites = [r for r in csv.DictReader(f) if not a.only or r["name"] == a.only]
    if not sites:
        sys.exit(f"no site named {a.only!r} in {a.sites}")

    # Buffer so relief windows at the edge of the analysis square are complete.
    fetch_half = a.half_km + a.relief_km / 2 + 1.0
    for s in sites:
        name, lat, lon = s["name"], float(s["lat"]), float(s["lon"])
        t0 = time.time()
        print(f"[{name}] fetching +-{fetch_half:g} km ...", flush=True)
        region = fetch_region(bbox_around(lat, lon, fetch_half), source=a.source,
                              cache_dir=a.cache_dir, name=f"{name}_{fetch_half:g}km",
                              dem_res=a.dem_res)
        mg = to_metric_grid(region, res_m=a.res_m)
        t = compute_terrain(mg, relief_window_m=a.relief_km * 1000, roughness_window_px=a.rough_px)
        row = summarise(name, lat, lon, a.half_km, region, mg, t)
        upsert(Path(a.out), row)
        print(f"[{name}] done in {time.time() - t0:.0f} s -> {a.out}")
        for k, v in row.items():
            print(f"    {k:28s} {v}")


if __name__ == "__main__":
    main()
