"""Track A1: cheap bowl prescreen for a whole 1 deg tile at native GLO-90 resolution (night run).

The tile (+ a small pad, so bowls at the tile edge close) is reprojected to local UTM at 90 m, every closed
depression is found with the SAME detector as config-v1 (pipeline.polar.find_depressions), but with LENIENT
limits passed on the command line (default >= 25 m deep, >= 700 m wide, elongation <= 2; NOT config-v1: they
only decide which cells go to A2 = the 30 m config-v1 pipeline). Each depression is assigned to the cell that
holds its low point. Lenient because 90 m smooths small bowls: config-v1 itself needs 50 m / 1000 m at 60 m.
"""
from __future__ import annotations

import numpy as np

from dem.grid import metric_crs_for, reproject_dem
from pipeline.polar import find_depressions


def a1_tile(z90, tf90, cells: list[dict], limits: dict) -> dict:
    """{cell id: [depressions]} for depressions whose low point lies in a cell of `cells`.
    z90/tf90: GLO-90 lon/lat array covering the tile + pad. limits: min_depth_m, min_width_m, max_elongation."""
    from pipeline.run import pixel_lonlat
    w = min(c["west"] for c in cells)
    e = max(c["east"] for c in cells)
    s = min(c["south"] for c in cells)
    n = max(c["north"] for c in cells)
    mg = reproject_dem(z90, tf90, "EPSG:4326", res_m=90.0, dst_crs=metric_crs_for((w + e) / 2, (s + n) / 2))
    pcfg = {"min_depression_depth_m": limits["min_depth_m"], "min_depression_width_m": limits["min_width_m"],
            "max_elongation": limits["max_elongation"]}
    deps = find_depressions(mg.dem, np.ones(mg.dem.shape, bool), mg.res_m, pcfg)
    out = {c["id"]: [] for c in cells}
    for d in deps:
        lon, lat = pixel_lonlat(mg, d["low"][0], d["low"][1])
        lon, lat = float(lon), float(lat)
        for c in cells:
            if c["west"] <= lon < c["east"] and c["south"] <= lat < c["north"]:
                out[c["id"]].append({"lat": round(lat, 5), "lon": round(lon, 5), "depth_m": round(d["depth_m"], 1),
                                     "width_m": round(d["width_m"]), "elongation": round(d["elongation"], 2)})
                break
    return out


def skip_reason(limits: dict) -> str:
    return (f"A1: no closed depression >= {limits['min_depth_m']:g} m deep, >= {limits['min_width_m']:g} m wide, "
            f"elongation <= {limits['max_elongation']:g} at 90 m (GLO-90)")
