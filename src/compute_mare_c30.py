"""mare-v1.1: lunar c30 small-crater density over the SAME 20 mare cells as the frozen mare-v1 target.

Per cell (config/lunar_targets.json["mare"]["cells"], i.e. the cells compute_mare_target.py used): the SLDEM
window (src/fetch_sldem_window.py) onto the 60 m grid exactly as compute_mare_target.load_cell_grid does, base
spot from pipeline.mare.mare_cell, then pipeline.mare.small_crater_density (the function the Earth side uses).
Check: mare_cell should reproduce the stored c9/c10/c12/c13 of each cell. With the SLDEM2015 tiles (Mateo's source)
and unchanged code, 15 Nov 2026 gave small differences (c10 up to ~0.03 deg, c9 a few m; serenitatis_04 c9 188 vs
126 m: base spot moved), probably GDAL / library versions in the reprojection (not verified). They are printed
and stored per cell ("repro_diff") for Mateo to check; a cell differing by more than 50 % in c9 stops the script.

Writes (computed by Claude Code, to be checked by Mateo):
  config/lunar_targets.json["mare"]["criteria"]["c30_small_craters"]: median, IQR, tolerance = max(IQR, floor)
  config/lunar_targets_candidates.json: c30 per mare (median of its 5 cells) for the 4 maria targets
The four mare-v1 criteria are not touched (tests/test_mare_freeze.py).

    python src/fetch_sldem_window.py --cells config/mare_cells.json --first 5
    python src/compute_mare_c30.py            # prints the per-cell table; --write to store the entries
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compute_mare_target import SLDEM_DIR, load_cell_grid  # noqa: E402
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.mare import C30, MARE_CRITERIA, mare_cell, small_crater_density  # noqa: E402
from pipeline.multi_target import CANDIDATES_PATH  # noqa: E402

CHECK = "computed by Claude Code, to be checked by Mateo"


def lunar_c30(cfg: dict, sldem_dir: Path = SLDEM_DIR) -> list[dict]:
    cells = cfg["lunar_targets"]["mare"]["cells"]
    p = cfg["mare_v11"]["c30"]
    out = []
    for c in cells:
        tif = sldem_dir / f"{c['id']}.tif"
        if not tif.exists():
            out.append({"id": c["id"], "mare": c["mare"], C30: None, "reason": "no SLDEM window"})
            continue
        mg, in_cell = load_cell_grid(tif, c["lat"], c["lon"], cfg)
        r = mare_cell(mg, in_cell, None, cfg)
        if r["c9_relief"] is None or abs(r["c9_relief"] - c["c9_relief"]) > 0.5 * c["c9_relief"]:
            raise SystemExit(f"{c['id']}: c9 {r['c9_relief']} vs frozen {c['c9_relief']}: not Mateo's grid")
        diff = {k: round(r[k] - c[k], 4) for k in MARE_CRITERIA}
        out.append({"id": c["id"], "mare": c["mare"], "repro_diff": diff,
                    C30: small_crater_density(mg.dem, (r["base_row"], r["base_col"]), mg.res_m, p)})
    return out


def entry(vals: list, floor: float, ids: list, extra: dict) -> dict:
    v = np.array([x for x in vals if x is not None], float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    iqr = float(q3 - q1)
    return {"value": round(float(med), 5), "iqr": round(iqr, 5), "tolerance": round(max(iqr, floor), 5),
            "tolerance_rule": f"max(IQR, mare_v11.c30_tolerance_floor {floor:g})", "n_cells": int(v.size),
            "cells": ids, "cell_values": [None if x is None else round(x, 5) for x in vals],
            "repro_note": "base spot recomputed with mare_cell on the SLDEM2015 tile windows; c9/c10/c12/c13 differ "
                          "slightly from the frozen per-cell values (repro_diff = now - frozen), see compute_mare_c30.py",
            "unit": "closed depressions per km2 (>= 10 m deep, >= 300 m wide, elongation <= 2) within 5 km of the base spot",
            "source": "SLDEM2015 windows (src/fetch_sldem_window.py) on the 60 m grid as compute_mare_target.py; "
                      "pipeline.mare.small_crater_density via src/compute_mare_c30.py",
            "date": date.today().isoformat(), "verified": False, "check": CHECK, "version": "mare-v1.1", **extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    np.seterr(invalid="ignore")
    cfg = load_config()
    rows = lunar_c30(cfg)
    print(f"{'cell':22s} {'c30 /km2':>9s}")
    for r in rows:
        print(f"{r['id']:22s} {r[C30] if r[C30] is not None else 'no data':>9}   repro diff {r.get('repro_diff')}")
    floor = cfg["mare_v11"]["c30_tolerance_floor"]
    e = entry([r[C30] for r in rows], floor, [r["id"] for r in rows],
              {"repro_diff": {r["id"]: r.get("repro_diff") for r in rows}})
    print(f"\n20 cells: median {e['value']}, IQR {e['iqr']}, tolerance {e['tolerance']}  (n {e['n_cells']})")
    per_mare = {}
    for r in rows:
        per_mare.setdefault(r["mare"], []).append(r)
    for m, rs in per_mare.items():
        v = [r[C30] for r in rs if r[C30] is not None]
        print(f"  {m:16s} median {np.median(v):.4f}  values {[round(x, 4) for x in v]}")
    if not a.write:
        return
    t = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    t["mare"]["criteria"][C30] = e
    Path(TARGETS_PATH).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cand = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    for tg in cand["targets"]:
        if tg.get("base_type") == "mare" and tg.get("mare") in per_mare:
            rs = per_mare[tg["mare"]]
            tg["criteria"][C30] = entry([r[C30] for r in rs], floor, [r["id"] for r in rs],
                                        {"note": "only 5 cells: the IQR is a rough spread estimate; under "
                                                 "mare_v11.common_tolerance the 20-cell tolerance is used"})
    CANDIDATES_PATH.write_text(json.dumps(cand, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written -> {TARGETS_PATH} and {CANDIDATES_PATH}")


if __name__ == "__main__":
    main()
