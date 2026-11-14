"""Pick the lunar mare cells for the Mare target, ONCE, with a fixed seed, and commit the list.

Team decision (14 Nov 2026, Caspar + Mateo): the Mare target is the median over cells spread across
four maria, not one site; the spread between cells (IQR) sets the tolerance. The list is fixed
before any value is computed, so nobody can pick cells that give a convenient answer.

Rule
  - maria: Tranquillitatis, Serenitatis, Imbrium, Crisium (outlines: LROC global mare map,
    Nelson et al. 2014, LPSC 45 #2861; field MARE_NAME)
  - a cell = cell_km square (config grid.cell_km); its centre is drawn uniformly at random inside
    the mare shrunk by (half cell diagonal + margin_km), so the whole cell lies inside the mare
    with at least margin_km to the edge
  - cells of one mare do not overlap (centres at least one cell diagonal apart)
  - CANDIDATES per mare are stored in draw order. The target script takes, per mare, the first
    PER_MARE candidates that pass the bowl filter (no depression >= polar.min_depression_width_m
    wide and >= polar.min_depression_depth_m deep, same detector as on Earth). Order is fixed here.

    curl -L -o data/moon/LROC_GLOBAL_MARE_180.ZIP \\
      https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/SHAPEFILE/LROC_GLOBAL_MARE/LROC_GLOBAL_MARE_180.ZIP
    python src/mare_cells.py            # -> config/mare_cells.json (commit it)
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
from pipeline.config import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE = ROOT / "data" / "moon" / "LROC_GLOBAL_MARE_180.ZIP"
OUT = ROOT / "config" / "mare_cells.json"
MARIA = ("Tranquillitatis", "Serenitatis", "Imbrium", "Crisium")
PER_MARE = 5              # team decision: 5 per mare x 4 maria
CANDIDATES = 15           # (team start value) spares in draw order, for cells the bowl filter removes
SEED = 20261114           # fixed: the date of the decision
MARGIN_KM = 10.0          # (team start value) minimum distance from the cell to the mare edge
MOON_LL = "+proj=longlat +R=1737400 +no_defs"
# Named site for the card (not a scored cell): Apollo 11 lunar module, NASA NSSDC lunar_sites
# (LRO images, Wagner et al. 2017, Icarus 283), MOON_ME / DE421
APOLLO_11 = {"lat": 0.67416, "lon": 23.47314,
             "source": "NASA NSSDC Apollo landing site coordinates (Wagner et al. 2017, Icarus 283, 92-103)"}


def local_crs(lat: float, lon: float) -> str:
    """Metric CRS centred on a point: stereographic on the 1737.4 km sphere (same family as polar)."""
    return f"+proj=stere +lat_0={lat:.6f} +lon_0={lon:.6f} +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"


def mare_geometry(gdf, name: str):
    sel = gdf[gdf["MARE_NAME"].astype(str).str.contains(name, case=False, na=False)]
    if sel.empty:
        names = sorted(gdf["MARE_NAME"].astype(str).unique())
        raise SystemExit(f"no MARE_NAME contains {name!r}; available: {names[:40]}")
    return sel, sel.geometry.union_all() if hasattr(sel.geometry, "union_all") else sel.unary_union


def pick_cells(geom_ll, cell_km: float, margin_km: float, n: int, seed: int) -> list[tuple[float, float]]:
    """n non-overlapping cell centres (lon, lat) drawn inside geom shrunk by half a cell diagonal + margin."""
    import geopandas as gpd
    from shapely.geometry import Point
    c = geom_ll.representative_point()
    crs = local_crs(c.y, c.x)
    g = gpd.GeoSeries([geom_ll], crs=MOON_LL).to_crs(crs).iloc[0]
    half_diag = cell_km * 1000 / 2 * np.sqrt(2)
    inner = g.buffer(-(half_diag + margin_km * 1000))
    if inner.is_empty:
        raise ValueError("mare too small for the cell + margin")
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = inner.bounds
    pts: list[Point] = []
    for _ in range(200_000):
        if len(pts) == n:
            break
        p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
        if inner.contains(p) and all(p.distance(q) >= 2 * half_diag for q in pts):
            pts.append(p)
    if len(pts) < n:
        raise ValueError(f"only {len(pts)} of {n} cells fit")
    ll = gpd.GeoSeries(pts, crs=crs).to_crs(MOON_LL)
    return [(float(q.x), float(q.y)) for q in ll]


def main():
    import geopandas as gpd
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shapefile", default=str(SHAPEFILE))
    ap.add_argument("--force", action="store_true", help="overwrite an existing (committed) list")
    a = ap.parse_args()
    if OUT.exists() and not a.force:
        raise SystemExit(f"{OUT.relative_to(ROOT)} exists: the list is fixed once. Use --force only on purpose.")

    cell_km = load_config()["grid"]["cell_km"]
    gdf = gpd.read_file(a.shapefile)
    if gdf.crs is None:
        gdf = gdf.set_crs(MOON_LL)
    gdf = gdf.to_crs(MOON_LL)
    cells = []
    for i, name in enumerate(MARIA):
        sel, geom = mare_geometry(gdf, name)
        print(f"{name}: {len(sel)} polygon(s), names {sorted(sel['MARE_NAME'].astype(str).unique())}")
        for k, (lon, lat) in enumerate(pick_cells(geom, cell_km, MARGIN_KM, CANDIDATES, SEED + i), 1):
            cells.append({"id": f"{name.lower()}_{k:02d}", "mare": name, "order": k,
                          "lat": round(lat, 5), "lon": round(lon, 5)})
    out = {
        "_readme": [
            "Lunar mare cells for the Mare target (median over cells, tolerance = IQR, team decision 14 Nov).",
            f"Per mare the target uses the first {PER_MARE} candidates in 'order' that pass the bowl filter.",
            "Fixed once by src/mare_cells.py with the seed below; do not edit by hand.",
        ],
        "created": date.today().isoformat(), "seed": SEED, "cell_km": cell_km, "margin_km": MARGIN_KM,
        "per_mare": PER_MARE, "candidates_per_mare": CANDIDATES,
        "outlines": "LROC global mare map (Nelson et al. 2014, LPSC 45 #2861), LROC_GLOBAL_MARE_180",
        "lon_domain": "-180..180, planetocentric",
        "named_site": {"apollo_11": APOLLO_11},
        "cells": cells,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cells)} candidate cells -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
