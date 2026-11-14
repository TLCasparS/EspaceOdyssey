"""Compute the lunar Mare target with the Earth pipeline's own code and write it into
config/lunar_targets.json["mare"]: median over the fixed cell list, tolerance = max(IQR, floor).

Per mare, in the committed order of config/mare_cells.json:
  - the SLDEM window (src/fetch_sldem_window.py) goes onto the 60 m grid in a local stereographic CRS
    (dem.grid.reproject_dem, grid.resampling), cell = grid.cell_km square centred on the cell point
  - NO bowl exclusion (team decision 14 Nov, to mirror Earth, where Mare cells keep their craters):
    small craters are normal mare texture; excluding them biased the target toward unusually smooth
    mare (34 of 60 cells had a >= 1 km bowl). has_bowl is recorded per cell for information only.
  - the first mare_cells.per_mare cells that pipeline.mare.mare_cell keeps count
Then pipeline.mare.target_from_cells builds the entries. Apollo 11 is computed the same way, stored as
display only (the named site on the card), never part of the median.

    python src/mare_cells.py                                   # once: config/mare_cells.json (commit)
    python src/fetch_sldem_window.py --cells config/mare_cells.json
    python src/compute_mare_target.py                          # -> config/lunar_targets.json["mare"]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem.grid import reproject_dem  # noqa: E402
from mare_cells import local_crs  # noqa: E402
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.mare import MARE_CRITERIA, has_bowl, mare_cell, target_from_cells  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "config" / "mare_cells.json"
SLDEM_DIR = ROOT / "data" / "moon" / "sldem"
SOURCE = ("SLDEM2015 (LOLA + SELENE Kaguya TC merge, 512 ppd = 59 m; Barker et al. 2016) windows from "
          "src/fetch_sldem_window.py, resampled to the 60 m grid; cells: config/mare_cells.json")


def load_cell_grid(tif: Path, lat: float, lon: float, cfg: dict):
    import rasterio
    with rasterio.open(tif) as s:
        z, tf, crs = s.read(1).astype("float32"), s.transform, s.crs
    mg = reproject_dem(z, tf, crs, res_m=cfg["grid"]["res_m"], dst_crs=local_crs(lat, lon),
                       resampling=cfg["grid"]["resampling"])
    rr, cc = np.indices(mg.dem.shape)
    x = mg.transform.c + (cc + 0.5) * mg.transform.a
    y = mg.transform.f + (rr + 0.5) * mg.transform.e
    h = cfg["grid"]["cell_km"] * 500
    return mg, (np.abs(x) <= h) & (np.abs(y) <= h)            # the point is the CRS origin


def evaluate(spec: dict, sldem_dir: Path, cfg: dict) -> tuple[dict, list, list, dict]:
    """(values per criterion, used cells, skipped cells, Apollo 11 result)."""
    per_mare = spec["per_mare"]
    values = {c: [] for c in MARE_CRITERIA}
    used, skipped = [], []
    by_mare: dict[str, list] = {}
    for c in spec["cells"]:
        by_mare.setdefault(c["mare"], []).append(c)
    for mare, cand in by_mare.items():
        n = 0
        for c in sorted(cand, key=lambda c: c["order"]):
            if n == per_mare:
                break
            tif = sldem_dir / f"{c['id']}.tif"
            if not tif.exists():
                skipped.append({**c, "reason": "no SLDEM window (run fetch_sldem_window.py)"})
                continue
            mg, in_cell = load_cell_grid(tif, c["lat"], c["lon"], cfg)
            bowl = has_bowl(mg, in_cell, cfg)                  # information only, not an exclusion
            r = mare_cell(mg, in_cell, None, cfg)
            if not r["keep"]:
                skipped.append({**c, "reason": r["reason"]})
                continue
            for k in MARE_CRITERIA:
                values[k].append(r[k])
            used.append({k: c[k] for k in ("id", "mare", "order", "lat", "lon")} | {k: r[k] for k in MARE_CRITERIA}
                        | {"has_bowl": bowl})
            n += 1
        if n < per_mare:
            print(f"WARNING: {mare}: only {n} of {per_mare} cells usable")
    apollo = None
    for name, site in spec.get("named_site", {}).items():
        tif = sldem_dir / f"{name}.tif"
        if tif.exists():
            mg, in_cell = load_cell_grid(tif, site["lat"], site["lon"], cfg)
            r = mare_cell(mg, in_cell, None, cfg)
            apollo = {"name": name, **site, **{k: r[k] for k in MARE_CRITERIA},
                      "has_bowl": has_bowl(mg, in_cell, cfg), "keep": r["keep"], "reason": r["reason"]}
    return values, used, skipped, apollo


def main():
    cfg = load_config()
    spec = json.loads(CELLS.read_text(encoding="utf-8"))
    values, used, skipped, apollo = evaluate(spec, SLDEM_DIR, cfg)
    floors = cfg["mare"]["tolerance_floor"]
    entries = target_from_cells(values, floors, [c["id"] for c in used], spec["seed"])

    print(f"{len(used)} cells used ({sum(c['has_bowl'] for c in used)} contain a bowl, kept as on Earth), "
          f"{len(skipped)} skipped")
    for s in skipped:
        print(f"  skipped {s['id']}: {s['reason']}")
    print(f"\n{'criterion':15s} {'median':>9s} {'IQR':>8s} {'floor':>7s} {'tolerance':>9s} {'min':>8s} {'max':>8s}  n")
    for k in MARE_CRITERIA:
        e, v = entries[k], np.array([x for x in values[k] if x is not None], float)
        if v.size:
            print(f"{k:15s} {e['value']:9.4g} {e['iqr']:8.4g} {floors[k]:7.4g} {e['tolerance']:9.4g} "
                  f"{v.min():8.4g} {v.max():8.4g}  {e['n_cells']}")
    if apollo:
        print("Apollo 11:", {k: apollo[k] for k in MARE_CRITERIA}, "bowl" if apollo["has_bowl"] else "no bowl")

    t = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    m = t["mare"]
    today = date.today().isoformat()
    m["status"] = (f"computed {today} by src/compute_mare_target.py: median over {len(used)} lunar mare cells "
                   "(pipeline.mare.mare_cell; first per_mare cells per mare in the fixed order of "
                   "config/mare_cells.json, no bowl exclusion, as on Earth), tolerance = max(IQR, floor) "
                   "(pipeline.mare.target_from_cells)")
    m["seed"], m["cells"], m["cells_skipped"] = spec["seed"], used, skipped
    for k in MARE_CRITERIA:
        e = entries[k]
        m["criteria"][k].update(e, source=SOURCE, date=today, verified=e.get("value") is not None)
    if apollo:
        m["named_site_values"] = {"_note": "Apollo 11 cell, same code; display only, not in the median", **apollo}
    Path(TARGETS_PATH).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwritten -> {Path(TARGETS_PATH).relative_to(ROOT)}  (check the spread above; floors for c10/c12 are "
          "a team decision in config/pipeline.yaml mare.tolerance_floor)")


if __name__ == "__main__":
    np.seterr(invalid="ignore")
    main()
