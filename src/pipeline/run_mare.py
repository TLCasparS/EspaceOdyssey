"""Mare run: bbox -> land-cover filter -> 15 km cells -> mare_cell per kept cell (60 m local UTM) -> scores.

Kept separate from pipeline/run.py so the frozen, validated Polar path (config-v1) stays untouched. Uses the
same filter, DEM, grid and cell helpers. Until the lunar Mare targets exist (Mateo), every criterion has
method 'none': the run still writes all raw values (that is what Track B needs), with empty scores.

    python src/run_pipeline.py --base mare --bbox ... --name <run>
Outputs in out/<name>/: ranking.csv (all kept cells, scored ones first), cells.geojson, radar.json, run_info.json.

mare-v1.1 (15 Nov 2026, docs/MARE_V11.md): `--base mare --mare-v11` also computes c30 small-crater density
(pipeline.mare.small_crater_density) and scores with pipeline.mare_v11.v11_criteria (mare-v1 + c30 at
mare_v11.c30_weight); ranking.csv gets c30, score_v1 (the mare-v1 score) and BEST_TARGET / BEST_SCORE over the
Mare targets with the common tolerance. Without --mare-v11 the run is exactly mare-v1.
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
from pipeline.mare import C30, FACT_C16, MARE_CRITERIA, mare_cell, small_crater_density
from pipeline.run import _clean, cell_mask_on_grid, cut_window, pixel_lonlat
from pipeline.scoring import method, score_direct, scoring_note, total_score

LABELS = {"c9_relief": ("9 Relief (5 km of base pad)", "m"), "c10_flat_base": ("10 Flat base spot", "deg"),
          "c12_drivable": ("12 Drivable share", "share < 15 deg"), "c13_roughness": ("13 Roughness", "m"),
          C30: ("30 Small craters (5 km of base pad)", "per km2")}
V11_COLS = [C30, f"s_{C30}", f"method_{C30}", "score_v1", "BEST_TARGET", "BEST_SCORE"]
COLS = (["rank", "id", "score", "n_scored", "lon", "lat"]
        + [x for c in MARE_CRITERIA for x in (c, f"s_{c}", f"method_{c}")]
        + ["base_lon", "base_lat", "base_elev_m", "zone_covered", "reason", "usable", "utm_crs",
           "west", "south", "east", "north"])


def mare_buffer_m(cfg) -> float:
    return cfg["mare"]["radius_km"] * 1000 + 500        # the 5 km zone around a pad at the cell edge + margin


def cell_mare(cell, dem, dem_tf, usable, lc_tf, cfg, return_grid=False, crit=None):
    """crit: criteria to score with (default mare-v1 cfg["mare"]["criteria"]); with C30 in crit (mare-v1.1)
    c30 is computed too."""
    crit = crit or cfg["mare"]["criteria"]
    lon_c, lat_c = (cell["west"] + cell["east"]) / 2, (cell["south"] + cell["north"]) / 2
    sub, sub_tf = cut_window(dem, dem_tf, padded_bbox(cell["west"], cell["south"], cell["east"], cell["north"],
                                                      mare_buffer_m(cfg)))
    mg = reproject_dem(sub, sub_tf, "EPSG:4326", res_m=cfg["grid"]["res_m"], dst_crs=metric_crs_for(lon_c, lat_c),
                       resampling=cfg["grid"]["resampling"])
    in_cell = cell_mask_on_grid(mg, cell)
    usable_g = onto_grid(usable.astype(np.uint8), lc_tf, "EPSG:4326", mg, nodata=0) == 1
    res = mare_cell(mg, in_cell, usable_g, cfg)
    r, c = res.pop("base_row"), res.pop("base_col")
    if C30 in crit:
        res[C30] = (small_crater_density(mg.dem, (r, c), mg.res_m, cfg["mare_v11"]["c30"])
                    if r is not None and res["keep"] else None)
    if r is None:
        res["base_lon"] = res["base_lat"] = None
    else:
        lo, la = pixel_lonlat(mg, r, c)
        res["base_lon"], res["base_lat"] = round(float(lo), 5), round(float(la), 5)
    res["utm_crs"] = mg.crs
    for name in crit:
        sc = score_direct(res.get(name), crit[name])
        res[f"s_{name}"] = None if sc is None else round(sc, 4)
    return (res, mg) if return_grid else res


def run_mare(bbox, name, cfg, dem_res=30, pop_path=None, out_root="out", log=print, v11=False):
    t0 = time.time()
    crit = cfg["mare"]["criteria"]
    targets = None
    if v11:
        from pipeline import multi_target as mt
        from pipeline.mare_v11 import v11_criteria, v11_targets
        crit, targets = v11_criteria(cfg), v11_targets(cfg)
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
            res = cell_mare(r, dem, prof["transform"], masks["usable"], lc_tf, cfg, crit=crit)
            row.update(res)
            row["terrain_reason"] = res["reason"] if not res["keep"] else ""
            row["score"], row["n_scored"] = total_score(row, crit) if res["keep"] else (None, 0)
            if v11 and res["keep"]:
                v1 = cfg["mare"]["criteria"]
                row["score_v1"] = total_score({f"s_{k}": score_direct(row.get(k), v1[k]) for k in v1}, v1)[0]
                row["BEST_TARGET"], row["BEST_SCORE"] = mt.best({t["name"]: mt.score(row, t) for t in targets})
        else:
            row.update({c: None for c in crit}, score=None, n_scored=0)
        for c in crit:
            row[f"method_{c}"] = method(crit[c])
        row["lon"], row["lat"] = round((r["west"] + r["east"]) / 2, 5), round((r["south"] + r["north"]) / 2, 5)
        out_rows.append(row)
        if (i + 1) % 20 == 0 or i == len(rows) - 1:
            log(f"  mare {i + 1}/{len(rows)} cells ({time.time() - t0:.0f} s)")
    out_dir = os.path.join(out_root, name)
    kept = write_mare_outputs(out_dir, bbox, dem_res, cfg, out_rows, len(rows), crit=crit if v11 else None)
    log(f"Done in {time.time() - t0:.0f} s. {len(kept)} kept cells, {sum(r.get('score') is not None for r in kept)} "
        f"scored -> {out_dir}/")
    return out_rows, kept

def write_mare_outputs(out_dir, bbox, dem_res, cfg, out_rows, n_cells, crit=None):
    """ranking.csv, cells.geojson, radar.json, run_info.json for Mare rows (also used by night_run --score).
    crit: mare-v1.1 criteria (with C30) -> extra columns and version "mare-v1.1"; default mare-v1."""
    v11 = crit is not None
    crit = crit or cfg["mare"]["criteria"]
    cols = COLS + V11_COLS if v11 else COLS
    kept = [r for r in out_rows if r["keep"]]
    kept.sort(key=lambda r: (r.get("score") is None, -(r.get("score") or 0.0)))
    for k, r in enumerate(kept, 1):
        r["rank"] = k if r.get("score") is not None else None
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in kept:
            w.writerow({k: _clean(r.get(k)) for k in cols})
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
                  "in_total": method(crit[c]) == "target" and crit[c]["weight"] > 0} for c in crit],
        "display": {"c16_day_night_swing": FACT_C16, "c23_basalt": "not computed yet (GLiM)"},
        "score_label": "score (vs Moon): weighted mean of the axes with in_total = true",
        "lunar_target": cfg["lunar_targets"].get("mare", {}),
        "cells": [{"id": r["id"], "rank": r.get("rank"), "score": r.get("score"), "lon": r["lon"], "lat": r["lat"],
                   "scores": {c: _clean(r.get(f"s_{c}")) for c in crit},
                   "raw": {c: _clean(r.get(c)) for c in crit}} for r in kept],
    }
    with open(os.path.join(out_dir, "radar.json"), "w") as f:
        json.dump(radar, f, indent=1)
    with open(os.path.join(out_dir, "run_info.json"), "w") as f:
        json.dump({"base_type": "mare", "version": "mare-v1.1" if v11 else "mare-v1", "bbox": list(bbox), "dem": f"Copernicus GLO-{dem_res} (AWS)",
                   "note": scoring_note(crit), "n_cells": n_cells, "n_kept": len(kept),
                   "n_scored": sum(r.get("score") is not None for r in kept),
                   "config": {"grid": cfg["grid"], "filter": cfg["filter"], "mare": cfg["mare"],
                              **({"mare_v11": cfg["mare_v11"]} if v11 else {})}}, f, indent=1)
    return kept
