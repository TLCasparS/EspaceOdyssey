"""Fake app exports for the scale test (night guide, Task 4). NOT real data.

Writes clearly fake files in the export format of src/export_app.py (v2: scores.csv with NAME/COUNTRY/ROLE/
TERRAIN_SCORE/LIGHT_SCORE/MISSED_REASON, raw_values.csv, heatmap.json, cells.json near places only,
coverage.json per 1 deg tile, regions.json) to outputs_fake/<n>/, one folder per size. Never writes to outputs/.
targets.json is copied unchanged from outputs/ (the lunar reference; the app needs it to start).

Every place is called FAKE_0001, FAKE_0002, ...; every run is fake_rXX; every value is random (fixed seed).

    python scripts/make_fake_outputs.py                 # sizes 200 2000 10000, 20000 coverage tiles
    python scripts/make_fake_outputs.py --sizes 500 --tiles 5000

Open the app on one of them with  app/index.html?data=outputs_fake/2000
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Column order as written by src/export_app.py (APP_COLUMNS, DISPLAY_COLUMNS, EXTRA_COLS).
SIM_COLS = ["SUNNY_RIDGE", "DARK_FLOOR", "LIGHT_NEAR_DARK", "GRAZING_SUN", "SKY_VIEW", "BOWL_SHAPE", "RELIEF",
            "SLOPE_BASE", "STEEP_WALLS", "ROUGHNESS", "ASPECT"]
DISPLAY_COLS = ["DRIVABLE", "BARE", "GROUND_ICE", "IMPACT_CRATER", "CRATER_SIZE"]
EXTRA_COLS = ["RUN", "CELL", "BASE_TYPE", "SCORE_TOTAL", "RANK", "NAME", "COUNTRY", "ROLE",
              "TERRAIN_SCORE", "LIGHT_SCORE", "MISSED_REASON"]
RAW_EXTRA = ["DEPTH_SPILL_M", "DIAMETER_EQUIV_M", "LOW_ELEV_M", "BASE_LAT", "BASE_LON", "BASE_ELEV_M", "MAX_DARK_DAYS",
             "NEAR_PERMANENT_SHADOW_SHARE", "RANK_SCORE_WITHIN_RUN", "ICE_FLOOR_SHARE", "ICE_RIM_SHARE",
             "DRIVABLE_RIM_SHARE", "DRIVABLE_5KM_SHARE", "BARE_SHARE", "CRATER_DIAMETER_EQUIV_M",
             "CRATER_RIM_TO_FLOOR_M", "IMPACT_NAME", "IMPACT_DIAMETER_KM", "IMPACT_DIST_KM", "IMPACT_SOURCE",
             "RUN", "CELL", "BASE_TYPE"]
LIGHT = SIM_COLS[:5]
CELL_DEG = 0.15                  # ~15 km cells, like the real grid
OTHER_STATUS = ["no_bowl", "no_bowl", "no_bowl", "filtered", "dropped", "ice_floor"]


def f4(v):
    return "" if v is None else f"{v:.4f}"


def regions_for(rng: random.Random, n_regions: int):
    """Fake search regions: centres between 55 S and 80 N, each a few degrees wide."""
    return [{"name": f"fake_r{i:02d}", "title": f"Fake region {i:02d}", "country": "FAKE", "role": "screening",
             "lat": rng.uniform(-55, 78), "lon": rng.uniform(-179, 179), "half": rng.uniform(1.0, 3.0)}
            for i in range(n_regions)]


def make(n: int, n_tiles: int, out: Path, seed: int):
    rng = random.Random(seed + n)
    regions = regions_for(rng, max(5, n // 40))
    places = []
    for i in range(n):
        rg = rng.choice(regions)
        lat = max(-59.9, min(83.9, rg["lat"] + rng.uniform(-rg["half"], rg["half"])))
        lon = (rg["lon"] + rng.uniform(-rg["half"], rg["half"]) + 540) % 360 - 180
        sims = {c: round(rng.random(), 4) for c in SIM_COLS}
        sims["GRAZING_SUN"] = 0.0
        disp = {"DRIVABLE": round(rng.random(), 4), "BARE": round(rng.random(), 4),
                "GROUND_ICE": round(rng.random() * 0.2, 4), "IMPACT_CRATER": 1 if rng.random() < 0.02 else 0,
                "CRATER_SIZE": None}
        terrain = sum(sims[c] for c in SIM_COLS if c not in LIGHT) / (len(SIM_COLS) - len(LIGHT))
        light = sum(sims[c] for c in LIGHT) / len(LIGHT)
        places.append({"SITE": f"FAKE_{i + 1:04d}", "LAT": lat, "LON": lon, **sims, **disp, "RUN": rg["name"],
                       "CELL": f"r{i // 100:03d}c{i % 100:03d}", "BASE_TYPE": "polar",
                       "SCORE_TOTAL": round(0.6 * terrain + 0.4 * light, 4), "NAME": f"FAKE_{i + 1:04d}",
                       "COUNTRY": "FAKE", "ROLE": "screening", "TERRAIN_SCORE": round(terrain, 4),
                       "LIGHT_SCORE": round(light, 4), "MISSED_REASON": "", "_region": rg})
    places.sort(key=lambda p: -p["SCORE_TOTAL"])
    for r, p in enumerate(places, 1):
        p["RANK"] = r

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SITE", "LAT", "LON", *SIM_COLS, *DISPLAY_COLS, *EXTRA_COLS])
        for p in places:
            w.writerow([p["SITE"], f"{p['LAT']:.5f}", f"{p['LON']:.5f}", *[f4(p[c]) for c in SIM_COLS],
                        *[f4(p[c]) if c != "IMPACT_CRATER" else p[c] for c in DISPLAY_COLS],
                        p["RUN"], p["CELL"], p["BASE_TYPE"], f4(p["SCORE_TOTAL"]), p["RANK"], p["NAME"],
                        p["COUNTRY"], p["ROLE"], f4(p["TERRAIN_SCORE"]), f4(p["LIGHT_SCORE"]), ""])

    with open(out / "raw_values.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SITE", "LAT", "LON", *SIM_COLS, *RAW_EXTRA])
        for p in places:
            diam = rng.uniform(800, 6000)
            depth = diam * rng.uniform(0.03, 0.2)
            raw = [rng.uniform(0.5, 1.2), rng.random(), rng.uniform(0, 3), rng.uniform(20, 80), rng.random(),
                   depth / diam, depth, rng.uniform(0, 8), rng.uniform(5, 35), rng.uniform(0.5, 5), rng.uniform(0, 360)]
            w.writerow([p["SITE"], f"{p['LAT']:.5f}", f"{p['LON']:.5f}", *[f4(v) for v in raw],
                        f4(depth), f4(diam), f4(rng.uniform(0, 2000)), f"{p['LAT']:.5f}", f"{p['LON']:.5f}",
                        f4(rng.uniform(0, 2000)), "", f4(rng.random() * 0.1), f4(rng.random()), f4(rng.random() * 0.2),
                        f4(rng.random() * 0.2), f4(rng.random()), f4(p["DRIVABLE"]), f4(p["BARE"]), f4(diam),
                        f4(depth), "", "", "", "", p["RUN"], p["CELL"], p["BASE_TYPE"]])

    shutil.copyfile(ROOT / "outputs" / "targets.json", out / "targets.json")
    (out / "heatmap.json").write_text(json.dumps([{"lat": round(p["LAT"], 5), "lng": round(p["LON"], 5),
                                                   "weight": p["SCORE_TOTAL"]} for p in places], indent=1) + "\n")

    # cells.json: the place's own cell plus 3 searched neighbours without a result ("cells near places only")
    cells = []
    for p in places:
        for k in range(4):
            la = p["LAT"] + (0 if k == 0 else rng.choice([-1, 1]) * CELL_DEG)
            lo = p["LON"] + (0 if k == 0 else rng.choice([-1, 1]) * CELL_DEG)
            st = "ranked" if k == 0 else rng.choice(OTHER_STATUS)
            cells.append({"run": p["RUN"], "cell": p["CELL"] if k == 0 else f"{p['CELL']}n{k}", "base": "polar",
                          "lat": round(la, 5), "lng": round(lo, 5),
                          "bbox": [round(lo - CELL_DEG / 2, 5), round(la - CELL_DEG / 2, 5),
                                   round(lo + CELL_DEG / 2, 5), round(la + CELL_DEG / 2, 5)],
                          "status": st, "reason": "" if k == 0 else "fake: no depression",
                          "site": p["SITE"] if k == 0 else None, "score_total": p["SCORE_TOTAL"] if k == 0 else None})
    (out / "cells.json").write_text(json.dumps(cells, indent=1) + "\n")

    # coverage.json: n_tiles distinct 1 deg tiles, with counts per status (format of export_app.py)
    tiles, seen = [], set()
    while len(tiles) < n_tiles:
        la, lo = rng.randint(-60, 83), rng.randint(-180, 179)
        if (la, lo) in seen:
            continue
        seen.add((la, lo))
        s = rng.randint(20, 49)
        nb = rng.randint(0, s)
        tiles.append({"lat": la, "lon": lo, "polar": {"searched": s, "filtered": s - nb, "no_bowl": nb}})
    tiles.sort(key=lambda t: (t["lat"], t["lon"]))
    (out / "coverage.json").write_text(json.dumps(tiles, indent=1) + "\n")

    reg = {}
    for c in cells:
        reg.setdefault(c["run"], {}).setdefault(c["status"], 0)
        reg[c["run"]][c["status"]] += 1
    (out / "regions.json").write_text(json.dumps(
        [{"name": r["name"], "title": r["title"], "role": r["role"], "country": r["country"],
          "bbox": [round(r["lon"] - r["half"], 3), round(r["lat"] - r["half"], 3),
                   round(r["lon"] + r["half"], 3), round(r["lat"] + r["half"], 3)],
          "cells": {"polar": reg.get(r["name"], {})}} for r in regions], indent=1) + "\n")

    (out / "README.md").write_text(
        f"# FAKE data for the app scale test\n\nWritten by `scripts/make_fake_outputs.py` (seed {seed}): {n} fake places "
        f"(FAKE_0001…), {len(cells)} cells, {len(tiles)} coverage tiles, {len(regions)} fake regions. "
        "All values are random. Not results. `targets.json` is a copy of `outputs/targets.json`.\n", encoding="utf-8")
    sizes = {f.name: f.stat().st_size for f in sorted(out.iterdir())}
    print(f"{out.relative_to(ROOT)}: {n} places, {len(cells)} cells, {len(tiles)} tiles, "
          + ", ".join(f"{k} {v / 1024:.0f} KB" for k, v in sizes.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sizes", type=int, nargs="+", default=[200, 2000, 10000])
    ap.add_argument("--tiles", type=int, default=20000)
    ap.add_argument("--out", type=Path, default=ROOT / "outputs_fake")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    if a.out.resolve() == (ROOT / "outputs").resolve():
        raise SystemExit("refusing to write fake data to outputs/")
    for n in a.sizes:
        make(n, a.tiles, a.out / str(n), a.seed)


if __name__ == "__main__":
    main()
