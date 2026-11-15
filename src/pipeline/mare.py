"""Mare surface base: terrain criteria per cell, Earth and Moon with the same code (agreed with Mateo, 14 Nov 2026).

Anchor: the base spot = the flattest ~200 m pad (mare.pad_m, 3x3 px at 60 m) in the cell (usable pixels only;
ties within 0.01 deg -> the pad nearest the cell centre). Around it, within mare.radius_km (5 km):
    c9_relief      max - min elevation (m)
    c10_flat_base  mean slope of the base pad (deg)
    c12_drivable   share of pixels flatter than mare.drivable_slope_deg (15 deg)
    c13_roughness  median elevation std in 3x3 px windows (m), as in polar
Counting for Mare (config mare.criteria): c9, c10, c12, c13. Display: c16 day-night swing (no Earth analog
possible, fact), c23 basalt (not computed yet: GLiM download not checked).

Lunar target (Mateo, compute_lunar_target / lunar side): median over a FIXED list of mare cells (~20 across
4 maria, random with a seed, inside the mare; NO bowl exclusion, as on Earth: has_bowl() is information only). Tolerance per
criterion = IQR across those cells, at least mare.tolerance_floor[criterion]. target_from_cells() computes
exactly the entry stored in config/lunar_targets.json["mare"]["criteria"][name].
Named site for the card: Apollo 11 (Mare Tranquillitatis).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from dem.terrain import compute_terrain

MARE_CRITERIA = ("c9_relief", "c10_flat_base", "c12_drivable", "c13_roughness")
MARE_DISPLAY = ("c16_day_night_swing", "c23_basalt")

FACT_C16 = ("No Earth analog possible: near the lunar equator the surface reaches about 387-397 K at noon and "
            "cools to about 95 K just before sunrise, a day-night swing of roughly 290-300 K (LRO Diviner, "
            "Williams et al. 2017, Icarus, doi:10.1016/j.icarus.2016.08.012). Earth's largest surface swings "
            "are far smaller. Shown for information, weight 0.")


def _f(v):
    return None if v is None or not np.isfinite(v) else float(v)


def has_bowl(mg, in_cell: np.ndarray, cfg: dict) -> bool:
    """True if the cell holds a qualifying bowl by the POLAR bowl detector (depth, width, elongation limits
    from config polar). Mateo uses it to exclude lunar mare cells with a crater."""
    from pipeline.polar import find_depressions
    return bool(find_depressions(mg.dem, in_cell, mg.res_m, cfg["polar"]))


def base_pad(slope_deg: np.ndarray, in_cell: np.ndarray, usable: np.ndarray, res_m: float, pad_m: float):
    """(row, col, mean slope) of the flattest fully usable k x k pad whose centre lies in the cell, or None.
    Ties within 0.01 deg of the flattest -> the pad nearest the cell centre (deterministic on flat mare)."""
    k = max(1, int(round(pad_m / res_m))) | 1
    ok = usable & np.isfinite(slope_deg)
    full = ndimage.minimum_filter(ok.astype(np.uint8), size=k, mode="constant", cval=0) == 1
    mean = ndimage.uniform_filter(np.where(np.isfinite(slope_deg), slope_deg, 0.0), size=k, mode="nearest")
    cand = np.where(full & in_cell, mean, np.inf)
    if not np.isfinite(cand).any():
        return None
    near_min = cand <= cand.min() + 0.01
    rr, cc = np.nonzero(in_cell)
    cr, ccen = rr.mean(), cc.mean()
    r_idx, c_idx = np.indices(cand.shape)
    dist = np.where(near_min, np.hypot(r_idx - cr, c_idx - ccen), np.inf)
    r, c = np.unravel_index(np.argmin(dist), dist.shape)
    return int(r), int(c), float(cand[r, c])


def mare_cell(mg, in_cell: np.ndarray, usable: np.ndarray | None, cfg: dict) -> dict:
    """Raw Mare criteria for one buffered cell (Earth or Moon; no land cover on the Moon -> usable = all)."""
    m = cfg["mare"]
    usable = np.ones_like(in_cell) if usable is None else usable
    out = {c: None for c in MARE_CRITERIA}
    out.update({c: None for c in MARE_DISPLAY})
    out.update(keep=False, reason="", base_row=None, base_col=None, base_elev_m=None, zone_px=None, zone_covered=None)
    if not (in_cell & np.isfinite(mg.dem)).any():
        out["reason"] = "no DEM data in cell"
        return out
    t = compute_terrain(mg, relief_window_m=m["radius_km"] * 1000, roughness_window_px=m["roughness_window_px"])
    pad = base_pad(t.slope_deg, in_cell, usable, mg.res_m, m["pad_m"])
    if pad is None:
        out["reason"] = "no usable base pad in the cell"
        return out
    r, c, pad_slope = pad
    rr, cc = np.indices(mg.dem.shape)
    zone = np.hypot(rr - r, cc - c) * mg.res_m <= m["radius_km"] * 1000
    z, s, rough = mg.dem[zone], t.slope_deg[zone], t.roughness_m[zone]
    full_px = np.pi * (m["radius_km"] * 1000 / mg.res_m) ** 2
    covered = float(np.isfinite(z).sum() / full_px)
    out.update(base_row=r, base_col=c, base_elev_m=round(float(mg.dem[r, c]), 1),
               zone_px=int(zone.sum()), zone_covered=round(covered, 3))
    out["c10_flat_base"] = round(pad_slope, 4)
    if covered >= 0.5:                                    # else the 5 km zone runs off the data: no data
        out["c9_relief"] = _f(np.nanmax(z) - np.nanmin(z))
        sf = s[np.isfinite(s)]
        out["c12_drivable"] = _f((sf < m["drivable_slope_deg"]).mean()) if sf.size else None
        rf = rough[np.isfinite(rough)]
        out["c13_roughness"] = _f(np.median(rf)) if rf.size else None
    reasons = []
    if pad_slope > m["max_base_slope_deg"]:
        reasons.append(f"base-spot slope {pad_slope:.1f}>{m['max_base_slope_deg']:g} deg")
    if covered < 0.5:
        reasons.append(f"5 km zone only {covered:.0%} covered by data")
    out["keep"], out["reason"] = not reasons, "; ".join(reasons)
    for k in MARE_CRITERIA:
        if out[k] is not None:
            out[k] = round(out[k], 4)
    return out


C30 = "c30_small_craters"


def small_crater_density(z: np.ndarray, base_rc: tuple[int, int], res_m: float, p: dict) -> float | None:
    """Display criterion c30, weight 0 (Earth AND Moon, same code): closed depressions per km2 whose low point lies
    within p["radius_km"] of the base spot (base_rc = row, col on the 60 m grid z).

    A depression counts if it is >= p["min_depth_m"] deep (filled depth), >= p["min_width_m"] wide (equivalent
    diameter of the filled area) and elongation (longest axis / equivalent diameter) <= p["max_elongation"]:
    pipeline.polar.find_depressions with these limits instead of the Polar bowl limits.
    The grid is first cut to a square of radius_km + margin_km around the base spot, so Earth and Moon see the
    same window geometry whatever the base spot's position in its cell (cut edges and NaN are outlets, as in
    fill_depressions: a depression cut by the window edge does not close and is not counted).
    Area = data-covered pixels of the radius_km disc. None (no data, never 0) if less than half of the disc
    has data. Nested depressions: the priority-flood fill merges a small pit inside a larger closed depression
    into that one depression (counted once, if it qualifies).
    """
    from pipeline.polar import find_depressions
    r0, c0 = base_rc
    k = int(np.ceil((p["radius_km"] + p["margin_km"]) * 1000 / res_m))
    r1, c1 = max(r0 - k, 0), max(c0 - k, 0)
    sub = np.asarray(z, dtype=np.float64)[r1:r0 + k + 1, c1:c0 + k + 1]
    rr, cc = np.indices(sub.shape)
    disc = np.hypot(rr - (r0 - r1), cc - (c0 - c1)) * res_m <= p["radius_km"] * 1000
    full_px = np.pi * (p["radius_km"] * 1000 / res_m) ** 2
    data_px = int((disc & np.isfinite(sub)).sum())
    if data_px < 0.5 * full_px:
        return None
    lim = {"min_depression_depth_m": p["min_depth_m"], "min_depression_width_m": p["min_width_m"],
           "max_elongation": p["max_elongation"]}
    n = len(find_depressions(sub, disc, res_m, lim))
    return round(n / (data_px * res_m ** 2 / 1e6), 5)


def target_from_cells(values: dict[str, list[float]], floors: dict[str, float], cells: list, seed) -> dict:
    """Lunar Mare target entries (config/lunar_targets.json["mare"]["criteria"]) from the raw values of the
    fixed lunar cell list: value = median, tolerance = max(IQR, floor). None values (no data) are skipped."""
    out = {}
    for name, vals in values.items():
        v = np.array([x for x in vals if x is not None and np.isfinite(x)], float)
        if v.size == 0:
            out[name] = {"value": None, "tolerance": None, "n_cells": 0, "verified": False}
            continue
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        iqr = float(q3 - q1)
        out[name] = {"value": round(float(med), 4), "iqr": round(iqr, 4),
                     "tolerance": round(max(iqr, floors[name]), 4),
                     "tolerance_rule": f"max(IQR, floor {floors[name]:g})",
                     "n_cells": int(v.size), "seed": seed, "cells": cells}
    return out
