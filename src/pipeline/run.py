"""bbox -> land-cover filter -> Polar terrain criteria per surviving cell -> weighted score -> ranking.

The DEM is read once for the whole bbox (+ polar.buffer_m) from AWS (dem.fetch, no fallback:
read errors are raised as they are). Each surviving cell is cut out with its buffer and put on
its own local-UTM 60 m grid.
"""
from __future__ import annotations

import csv
import json
import math
import os
import time

import numpy as np

from dem.fetch import read_bbox
from dem.grid import MetricGrid, metric_crs_for, onto_grid, reproject_dem
from pipeline.filters import padded_bbox, run_filter
from pipeline.polar import CRITERIA, evaluate_polar_cell
from pipeline.scoring import NO_TARGET_NOTE, apply_rank, method, weighted_score

LABELS = {
    "c7_bowl": ("7 Bowl shape", "depth/width"),
    "c9_relief": ("9 Relief ~5 km", "m"),
    "c10_flat_base": ("10 Flat base spot", "deg"),
    "c11_walls": ("11 Steep walls", "deg"),
    "c13_roughness": ("13 Roughness", "m"),
    "c14_aspect": ("14 Pole-facing slopes", "share"),
}


def pixel_lonlat(mg: MetricGrid, rows, cols):
    """lon/lat (WGS84) of pixel centres (Earth grids)."""
    from pyproj import Transformer
    x, y = mg.transform * (np.asarray(cols) + 0.5, np.asarray(rows) + 0.5)
    return Transformer.from_crs(mg.crs, "EPSG:4326", always_xy=True).transform(x, y)


def cell_mask_on_grid(mg: MetricGrid, cell: dict) -> np.ndarray:
    """True for grid pixels whose centre lies inside the cell's lon/lat bounds."""
    rr, cc = np.indices(mg.dem.shape)
    lon, lat = pixel_lonlat(mg, rr, cc)
    return ((lon >= cell["west"]) & (lon < cell["east"]) &
            (lat >= cell["south"]) & (lat < cell["north"]))


def cut_window(dem, dem_tf, bounds):
    """Sub-array + transform of a lon/lat raster covering bounds (west, south, east, north)."""
    from rasterio.windows import Window, from_bounds, transform as win_tf
    win = from_bounds(*bounds, transform=dem_tf)
    r0, c0 = max(0, math.floor(win.row_off)), max(0, math.floor(win.col_off))
    r1 = min(dem.shape[0], math.ceil(win.row_off + win.height))
    c1 = min(dem.shape[1], math.ceil(win.col_off + win.width))
    w = Window(c0, r0, c1 - c0, r1 - r0)
    return dem[r0:r1, c0:c1], win_tf(w, dem_tf)


def evaluate_cell_terrain(cell, dem, dem_tf, usable, lc_tf, cfg):
    pcfg, gcfg = cfg["polar"], cfg["grid"]
    lon_c, lat_c = (cell["west"] + cell["east"]) / 2, (cell["south"] + cell["north"]) / 2
    sub, sub_tf = cut_window(dem, dem_tf, padded_bbox(cell["west"], cell["south"], cell["east"],
                                                      cell["north"], pcfg["buffer_m"]))
    mg = reproject_dem(sub, sub_tf, "EPSG:4326", res_m=gcfg["res_m"],
                       dst_crs=metric_crs_for(lon_c, lat_c), resampling=gcfg["resampling"])
    in_cell = cell_mask_on_grid(mg, cell)
    usable_g = onto_grid(usable.astype(np.uint8), lc_tf, "EPSG:4326", mg, nodata=0) == 1
    t = evaluate_polar_cell(mg, in_cell, usable_g, lat_c, cfg)
    for key in ("low", "base"):
        r, c = t.pop(f"{key}_row"), t.pop(f"{key}_col")
        if r is None:
            t[f"{key}_lon"] = t[f"{key}_lat"] = None
        else:
            lo, la = pixel_lonlat(mg, r, c)
            t[f"{key}_lon"], t[f"{key}_lat"] = round(float(lo), 5), round(float(la), 5)
    t["utm_crs"] = mg.crs
    return t


def run(bbox, name, cfg, dem_res=30, pop_path=None, out_root="out", log=print):
    t0 = time.time()
    rows, lc, lc_tf, masks = run_filter(bbox, cfg, pop_path, log=log)
    kept = [r for r in rows if r["keep"]]
    log(f"Filter: kept {len(kept)} / {len(rows)} cells ({time.time() - t0:.0f} s)")

    pad = padded_bbox(*bbox, cfg["polar"]["buffer_m"] + 1000)
    log(f"Reading Copernicus DEM GLO-{dem_res} for {tuple(round(v, 3) for v in pad)} ...")
    dem, prof = read_bbox(*pad, res=dem_res)
    log(f"  DEM {dem.shape} ({time.time() - t0:.0f} s)")

    crit = cfg["polar"]["criteria"]
    out_rows = []
    for i, r in enumerate(rows):
        row = {**r, "filter_reason": r["reason"]}
        if r["keep"]:
            t = evaluate_cell_terrain(r, dem, prof["transform"], masks["usable"], lc_tf, cfg)
            row.update(t)
            row["terrain_reason"] = t["reason"]
            row["reason"] = t["reason"]
            row["keep"] = t["keep"]
            if (i + 1) % 20 == 0 or i == len(rows) - 1:
                log(f"  terrain {i + 1}/{len(rows)} cells ({time.time() - t0:.0f} s)")
        else:
            row.update({c: None for c in CRITERIA})
            row["terrain_reason"] = ""
        out_rows.append(row)

    apply_rank(out_rows, crit)
    for row in out_rows:
        for c in CRITERIA:
            row.setdefault(f"s_{c}", None)
            row[f"method_{c}"] = method(crit[c])
        row["score"], row["n_scored"] = weighted_score(row, crit) if row["keep"] else (None, 0)

    ranked = sorted([r for r in out_rows if r["keep"] and r["score"] is not None], key=lambda r: -r["score"])
    for k, r in enumerate(ranked, 1):
        r["rank"] = k
    out_dir = os.path.join(out_root, name)
    write_outputs(out_dir, bbox, dem_res, cfg, out_rows, ranked)
    log(f"Done in {time.time() - t0:.0f} s. Ranked {len(ranked)} cells -> {out_dir}/")
    return out_rows, ranked


# --- outputs ----------------------------------------------------------------------------------

RANK_COLS = (["rank", "id", "score", "n_scored", "lon", "lat"]
             + [x for c in CRITERIA for x in (c, f"s_{c}", f"method_{c}")]
             + ["c7_depth_m", "c7_width_m", "has_depression", "depression_extends_outside_cell",
                "c14_n_steep", "low_lon", "low_lat", "low_elev_m", "base_lon", "base_lat",
                "usable", "largest_patch_km2", "utm_crs", "west", "south", "east", "north"])


def _clean(v):
    if isinstance(v, (np.floating, np.integer)):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def write_outputs(out_dir, bbox, dem_res, cfg, rows, ranked):
    os.makedirs(out_dir, exist_ok=True)
    for r in rows:
        r["lon"] = round((r["west"] + r["east"]) / 2, 5)
        r["lat"] = round((r["south"] + r["north"]) / 2, 5)

    with open(os.path.join(out_dir, "ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RANK_COLS, extrasaction="ignore")
        w.writeheader()
        for r in ranked:
            w.writerow({k: _clean(r.get(k)) for k in RANK_COLS})

    features = [{
        "type": "Feature",
        "properties": {k: _clean(v) for k, v in r.items() if k not in ("west", "south", "east", "north")},
        "geometry": {"type": "Polygon", "coordinates": [[
            [r["west"], r["south"]], [r["east"], r["south"]], [r["east"], r["north"]],
            [r["west"], r["north"]], [r["west"], r["south"]]]]},
    } for r in rows]
    with open(os.path.join(out_dir, "cells.geojson"), "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    crit = cfg["polar"]["criteria"]
    radar = {
        "base_type": "polar",
        "note": NO_TARGET_NOTE + "; criteria with method 'none' have no score yet (null = no data, not 0)",
        "axes": [{"id": c, "label": LABELS[c][0], "unit": LABELS[c][1], "direction": crit[c]["direction"],
                  "method": method(crit[c]), "weight": crit[c]["weight"]} for c in CRITERIA],
        "lunar_target": cfg["lunar_targets"]["polar"],    # raw values in the same units; null = TODO
        "cells": [{"id": r["id"], "rank": r["rank"], "score": r["score"], "lon": r["lon"], "lat": r["lat"],
                   "scores": {c: _clean(r.get(f"s_{c}")) for c in CRITERIA},
                   "raw": {c: _clean(r.get(c)) for c in CRITERIA}} for r in ranked],
    }
    with open(os.path.join(out_dir, "radar.json"), "w") as f:
        json.dump(radar, f, indent=1)

    with open(os.path.join(out_dir, "run_info.json"), "w") as f:
        json.dump({"bbox": list(bbox), "dem": f"Copernicus GLO-{dem_res} (AWS)",
                   "landcover": "ESA WorldCover 2021 v200 (AWS)", "note": NO_TARGET_NOTE,
                   "n_cells": len(rows), "n_ranked": len(ranked),
                   "dropped_by_filter": sum(1 for r in rows if r["filter_reason"]),
                   "dropped_by_terrain": sum(1 for r in rows if r.get("terrain_reason")),
                   "config": cfg}, f, indent=1)
