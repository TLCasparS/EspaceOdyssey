"""Candidate Mare lunar targets, one per mare (Tranquillitatis, Serenitatis, Imbrium, Crisium). Night Task 5.

    python src/compute_mare_candidates.py

Splits the existing 20-cell Mare target into four. Inputs are the per-cell raw values already stored in
config/lunar_targets.json["mare"]["cells"] (computed by src/compute_mare_target.py from SLDEM2015 with
pipeline.mare.mare_cell; read only, no DEM reads here). Per mare: median + IQR over its cells,
tolerance = max(IQR, floor) with the same function (pipeline.mare.target_from_cells) and the same floors
(config/pipeline.yaml mare.tolerance_floor). Writes the "mare" entries of config/lunar_targets_candidates.json
(verified: false) and figures/moon/targets/mare_per_mare.png.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.mare import target_from_cells  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "config" / "lunar_targets_candidates.json"
FIG = ROOT / "figures" / "moon" / "targets" / "mare_per_mare.png"
MARIA = ("Tranquillitatis", "Serenitatis", "Imbrium", "Crisium")


def main():
    cfg = load_config()
    floors = cfg["mare"]["tolerance_floor"]
    crit_names = list(cfg["mare"]["criteria"])
    mare = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))["mare"]
    src = next(iter(mare["criteria"].values()))["source"]
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    today = date.today().isoformat()
    recs = []
    for m in MARIA:
        cells = [c for c in mare["cells"] if c["mare"] == m]
        vals = {k: [c[k] for c in cells] for k in crit_names}
        entries = target_from_cells(vals, floors, [c["id"] for c in cells], mare["seed"])
        for k, e in entries.items():
            e.update(source=src + "; per-mare split of config/lunar_targets.json mare.cells", date=today,
                     verified=False, cell_values=[round(v, 4) for v in vals[k]])
        recs.append({"name": f"mare_{m.lower()}", "label": f"Mare · Mare {m} ({len(cells)} cells)",
                     "base_type": "mare", "mare": m, "n_cells": len(cells),
                     "has_bowl_cells": sum(bool(c["has_bowl"]) for c in cells),
                     "cells_lat_lon": [[c["lat"], c["lon"]] for c in cells],
                     "criteria": entries, "date": today, "git_commit": commit, "verified": False,
                     "note": f"only {len(cells)} cells: the IQR of so few values is a rough spread estimate",
                     "preview": str(FIG.relative_to(ROOT))})
        print(m, {k: (e["value"], e["tolerance"]) for k, e in entries.items()})

    out = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {"targets": []}
    out["targets"] = [t for t in out["targets"] if t["base_type"] != "mare"] + recs
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("->", OUT_JSON)
    figure(recs, mare["criteria"], crit_names)


def figure(recs, pooled, crit_names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(crit_names), figsize=(4 * len(crit_names), 4))
    for ax, k in zip(axes, crit_names):
        for i, r in enumerate(recs):
            e = r["criteria"][k]
            ax.plot([i] * len(e["cell_values"]), e["cell_values"], "o", color="0.5", ms=4)
            ax.errorbar(i, e["value"], yerr=e["tolerance"], fmt="s", color="C0", capsize=4)
        p = pooled[k]
        ax.axhline(p["value"], color="C3", ls="--", lw=1, label="current 20-cell target")
        ax.set_xticks(range(len(recs)), [r["mare"][:6] for r in recs])
        ax.set_title(f"{k} ({p.get('unit', '')})", fontsize=9)
    axes[0].legend(fontsize=7)
    fig.suptitle("Per-mare targets: cells (grey), median ± tolerance (blue)  [verified: false]", fontsize=10)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=90, bbox_inches="tight")
    print("figure ->", FIG)


if __name__ == "__main__":
    main()
