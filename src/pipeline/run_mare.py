"""Mare run: bbox -> land-cover filter -> 15 km cells -> mare_cell per kept cell (60 m local UTM) -> scores.

Kept separate from pipeline/run.py so the frozen, validated Polar path (config-v1) stays untouched. Uses the
same filter, DEM, grid and cell helpers. Until the lunar Mare targets exist (Mateo), every criterion has
method 'none': the run still writes all raw values (that is what Track B needs), with empty scores.

    python src/run_pipeline.py --base mare --bbox ... --name <run>
Outputs in out/<name>/: ranking.csv (all kept cells, scored ones first), cells.geojson, radar.json, run_info.json.
"""
from __future__ import annotations

import csv
import json
import os
import time

import numpy as np

from dem.fetch import read_bbox
from dem.grid import metric_crs_for, onto_grid, reproject_dem
from pipeline.filters import padded_bbox, run_filter
from pipeline.mare import FACT_C16, MARE_CRITERIA, mare_cell
from pipeline.run import _clean, cell_mask_on_grid, cut_window, pixel_lonlat
from pipeline.scoring import method, score_direct, scoring_note, total_score

LABELS = {"c9_relief": ("9 Relief (5 km of base pad)", "m"), "c10_flat_base": ("10 Flat base spot", "deg"),
          "c12_drivable": ("12 Drivable share", "share < 15 deg"), "c13_roughness": ("13 Roughness", "m")}
COLS = (["rank", "id", "score", "n_scored", "lon", "lat"]
        + [x for c in MARE_CRITERIA for x in (c, f"s_{c}", f"method_{c}")]
        + ["base_lon", "base_lat", "base_elev_m", "zone_covered", "reason", "usable", "utm_crs",
           "west", "south", "east", "north"])


def mare_buffer_m(cfg) -> float:
    return cfg["mare"]["radius_km"] * 1000 + 500        # the 5 km zone around a pad at the cell edge + margin


def cell_mare(cell, dem, dem_tf, usable, lc_tf, cfg):
    m = cfg["mare"]
    lon_c, lat_c = (cell["west"] + cell["east"]) / 2, (cell["south"] + cell["north"]) / 2
    sub, sub_tf = cut_window(dem, dem_tf, padded_bbox(cell["west"], cell["south"], cell["east"], cell["north"],
                                                      mare_buffer_m(cfg)))
    mg = reproject_dem(sub, sub_tf, "EPSG:4326", res_m=cfg["grid"]["res_m"], dst_crs=metric_crs_for(lon_c, lat_c),
                       resampling=cfg["grid"]["resampling"])
    in_cell = cell_mask_on_grid(mg, cell)
    usable_g = onto_grid(usable.astype(np.uint8), lc_tf, "EPSG:4326", mg, nodata=0) == 1
    res = mare_cell(mg, in_cell, usable_g, cfg)
    r, c = res.pop("base_row"), res.pop("base_col")
    if r is None:
        res["base_lon"] = res["base_lat"] = None
    else:
        lo, la = pixel_lonlat(mg, r, c)
        res["base_lon"], res["base_lat"] = round(float(lo), 5), round(float(la), 5)
    res["utm_crs"] = mg.crs
    for name in MARE_CRITERIA:
        sc = score_direct(res[name], m["criteria"][name])
        res[f"s_{name}"] = None if sc is None else round(sc, 4)
    return res


def run_mare(bbox, name, cfg, dem_res=30, pop_path=None, out_root="out", log=print):
    t0 = time.time()
    crit = cfg["mare"]["criteria"]
    rows, lc, lc_tf, masks = run_filter(bbox, cfg, pop_path, log=log)
    log(f"Filter: kept {sum(r['keep'] for r in rows)} / {len(rows)} cells ({time.time() - t0:.0f} s)")
    pad = padded_bbox(*bbox, mare_buffer_m(cfg) + 1000)
    log(f"Reading Copernicus DEM GLO-{dem_res} for {tuple(round(v, 3) for v in pad)} ...")
    dem, prof = read_bbox(*pad, res=dem_res)
    log(f"  DEM {dem.shape} ({time.time() - t0:.0f} s)")
    out_rows = []
    for i, r in enumerate(rows):
        row = {**r, "filter_reason": r["reason"], "terrain_reason": ""}
        if r["keep"]:
            res = cell_mare(r, dem, prof["transform"], masks["usable"], lc_tf, cfg)
            row.update(res)
            row["terrain_reason"] = res["reason"] if not res["keep"] else ""
            row["score"], row["n_scored"] = total_score(row, crit) if res["keep"] else (None, 0)
        else:
            row.update({c: None for c in MARE_CRITERIA}, score=None, n_scored=0)
        for c in MARE_CRITERIA:
            row[f"method_{c}"] = method(crit[c])
        row["lon"], row["lat"] = round((r["west"] + r["east"]) / 2, 5), round((r["south"] + r["north"]) / 2, 5)
        out_rows.append(row)
        if (i + 1) % 20 == 0 or i == len(rows) - 1:
            log(f"  mare {i + 1}/{len(rows)} cells ({time.time() - t0:.0f} s)")
    kept = [r for r in out_rows if r["keep"]]
    kept.sort(key=lambda r: (r.get("score") is None, -(r.get("score") or 0.0)))
    for k, r in enumerate(kept, 1):
        r["rank"] = k if r.get("score") is not None else None
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in kept:
            w.writerow({k: _clean(r.get(k)) for k in COLS})
    feats = [{"type": "Feature",
              "properties": {k: _clean(v) for k, v in r.items() if k not in ("west", "south", "east", "north")},
              "geometry": {"type": "Polygon", "coordinates": [[[r["west"], r["south"]], [r["east"], r["south"]],
                                                               [r["east"], r["north"]], [r["west"], r["north"]],
                                                               [r["west"], r["south"]]]]}} for r in out_rows]
    with open(os.path.join(out_dir, "cells.geojson"), "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)
    radar = {
        "base_type": "mare", "note": scoring_note(crit),
        "axes": [{"id": c, "label": LABELS[c][0], "unit": LABELS[c][1], "direction": crit[c]["direction"],
                  "method": method(crit[c]), "weight": crit[c]["weight"], "target": crit[c].get("target"),
                  "tolerance": crit[c].get("tolerance"),
                  "in_total": method(crit[c]) == "target" and crit[c]["weight"] > 0} for c in MARE_CRITERIA],
        "display": {"c16_day_night_swing": FACT_C16, "c23_basalt": "not computed yet (GLiM)"},
        "score_label": "score (vs Moon): weighted mean of the axes with in_total = true",
        "lunar_target": cfg["lunar_targets"].get("mare", {}),
        "cells": [{"id": r["id"], "rank": r.get("rank"), "score": r.get("score"), "lon": r["lon"], "lat": r["lat"],
                   "scores": {c: _clean(r.get(f"s_{c}")) for c in MARE_CRITERIA},
                   "raw": {c: _clean(r.get(c)) for c in MARE_CRITERIA}} for r in kept],
    }
    with open(os.path.join(out_dir, "radar.json"), "w") as f:
        json.dump(radar, f, indent=1)
    with open(os.path.join(out_dir, "run_info.json"), "w") as f:
        json.dump({"base_type": "mare", "bbox": list(bbox), "dem": f"Copernicus GLO-{dem_res} (AWS)",
                   "note": scoring_note(crit), "n_cells": len(rows), "n_kept": len(kept),
                   "n_scored": sum(r.get("score") is not None for r in kept),
                   "config": {"grid": cfg["grid"], "filter": cfg["filter"], "mare": cfg["mare"]}}, f, indent=1)
    log(f"Done in {time.time() - t0:.0f} s. {len(kept)} kept cells, {sum(r.get('score') is not None for r in kept)} "
        f"scored -> {out_dir}/")
    return out_rows, kept
