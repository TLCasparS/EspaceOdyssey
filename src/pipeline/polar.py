"""Polar terrain criteria v1 (DEM only): 7 bowl, 9 relief, 10 flat base spot, 11 steep walls,
13 roughness, 14 aspect. Numbers follow the team plan (docs/HANDOFF_terrain.md).

Input: one cell on the common metric grid (dem.grid.MetricGrid), read WITH a buffer around
the cell (config polar.buffer_m), plus boolean masks on that grid:
    in_cell  pixels inside the cell        usable  pixels allowed as base spot (land-cover filter)
Each criterion function returns Crit(raw, score, info); score is None for rank-scored criteria
(filled later across all cells, see scoring.py) and for no data.

Rules:
- No pixel is ever masked by slope. The only slope limit is on the base spot (criterion 10):
  cell dropped if the flattest usable pad is steeper than polar.max_base_slope_deg.
- 10 and 11 stay separate (one combined slope score would cancel out).
- The "low point" anchors 9 and 11: the deepest point of the deepest closed depression inside
  the cell, or the lowest pixel of the cell if there is no depression (interpreted).
"""
from __future__ import annotations

import heapq
from typing import NamedTuple

import numpy as np
from scipy import ndimage

from dem.terrain import Terrain, compute_terrain
from pipeline.scoring import score_direct


class Crit(NamedTuple):
    raw: float | None
    score: float | None
    info: dict


def _crit(name, raw, cfg, **info) -> Crit:
    raw = None if raw is None or not np.isfinite(raw) else float(raw)
    return Crit(raw, score_direct(raw, cfg["criteria"][name]), info)


# --- depressions ------------------------------------------------------------------------------

def fill_depressions(z: np.ndarray) -> np.ndarray:
    """Priority-flood fill (Barnes, Lehman & Mulla 2014): every closed depression is raised to its
    spill level. Grid edges and NaN pixels are outlets (water can leave there)."""
    h, w = z.shape
    nan = np.isnan(z)
    filled = np.where(nan, np.nan, z).astype(np.float64)
    done = nan.copy()
    heap = []
    # seeds: grid border + pixels next to NaN
    seed = np.zeros_like(done)
    seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    seed |= ndimage.binary_dilation(nan, np.ones((3, 3), bool))
    seed &= ~nan
    for r, c in zip(*np.nonzero(seed)):
        heapq.heappush(heap, (filled[r, c], r, c))
        done[r, c] = True
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    while heap:
        e, r, c = heapq.heappop(heap)
        for dr, dc in nbrs:
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and not done[rr, cc]:
                done[rr, cc] = True
                if filled[rr, cc] < e:
                    filled[rr, cc] = e
                heapq.heappush(heap, (filled[rr, cc], rr, cc))
    return filled


def low_point(z: np.ndarray, in_cell: np.ndarray, res_m: float, cfg: dict):
    """(row, col, depression info or None). Depth = spill level minus floor."""
    depth = fill_depressions(z) - z
    d_in = np.where(in_cell & np.isfinite(depth), depth, -np.inf)
    r, c = np.unravel_index(np.argmax(d_in), d_in.shape)
    if d_in[r, c] >= cfg["min_depression_depth_m"]:
        labels, _ = ndimage.label(depth > 1e-6, structure=np.ones((3, 3), bool))
        comp = labels == labels[r, c]
        area = comp.sum() * res_m ** 2
        width = 2 * np.sqrt(area / np.pi)              # equivalent diameter
        return r, c, {"depth_m": float(depth[r, c]), "width_m": float(width),
                      "extends_outside_cell": bool((comp & ~in_cell).any())}
    zc = np.where(in_cell & np.isfinite(z), z, np.inf)
    r, c = np.unravel_index(np.argmin(zc), zc.shape)
    return r, c, None


# --- criteria ---------------------------------------------------------------------------------

def c7_bowl(dep: dict | None, cfg: dict) -> Crit:
    """Closed depression: depth / equivalent diameter. No depression -> 0 (data exists)."""
    if dep is None:
        return _crit("c7_bowl", 0.0, cfg, depth_m=0.0, width_m=0.0)
    return _crit("c7_bowl", dep["depth_m"] / dep["width_m"], cfg,
                 depth_m=round(dep["depth_m"], 1), width_m=round(dep["width_m"], 0))


def c9_relief(t: Terrain, low: tuple[int, int], cfg: dict) -> Crit:
    """Max - min elevation in a relief_window_m square centred on the low point (NaN window -> None)."""
    return _crit("c9_relief", t.relief_m[low], cfg)


def c10_flat_base(t: Terrain, in_cell: np.ndarray, usable: np.ndarray, res_m: float, cfg: dict) -> Crit:
    """Mean slope of the flattest pad (~pad_m) lying fully inside the cell and the usable area."""
    k = max(1, int(round(cfg["pad_m"] / res_m))) | 1
    ok = in_cell & usable & np.isfinite(t.slope_deg)
    full = ndimage.minimum_filter(ok.astype(np.uint8), size=k, mode="constant", cval=0) == 1
    mean = ndimage.uniform_filter(np.where(np.isfinite(t.slope_deg), t.slope_deg, 0.0), size=k, mode="nearest")
    mean = np.where(full, mean, np.inf)
    if not np.isfinite(mean).any():
        return _crit("c10_flat_base", None, cfg, pad_px=k, base=None)
    r, c = np.unravel_index(np.argmin(mean), mean.shape)
    return _crit("c10_flat_base", mean[r, c], cfg, pad_px=k, base=(int(r), int(c)))


def _ring(shape, center, res_m, r_in, r_out):
    rr, cc = np.indices(shape)
    d = np.hypot(rr - center[0], cc - center[1]) * res_m
    return (d >= r_in) & (d <= r_out)


def c11_walls(t: Terrain, low: tuple[int, int], res_m: float, cfg: dict) -> Crit:
    """Mean slope in a ring around the low point. None if less than half the ring has data."""
    ring = _ring(t.slope_deg.shape, low, res_m, *cfg["wall_ring_m"])
    s = t.slope_deg[ring]
    if ring.sum() == 0 or np.isfinite(s).mean() < 0.5:
        return _crit("c11_walls", None, cfg)
    return _crit("c11_walls", np.nanmean(s), cfg)


def c13_roughness(t: Terrain, in_cell: np.ndarray, cfg: dict) -> Crit:
    """Median std of elevation (roughness_window_px window) over the cell."""
    v = t.roughness_m[in_cell]
    v = v[np.isfinite(v)]
    return _crit("c13_roughness", np.median(v) if v.size else None, cfg)


def c14_aspect(t: Terrain, in_cell: np.ndarray, lat: float, cfg: dict) -> Crit:
    """Share of steep pixels (slope > steep_slope_deg) in the cell whose downslope direction lies
    within pole_sector_deg of the nearer pole. No steep pixel -> 0 (interpreted: no walls at all)."""
    s, a = t.slope_deg[in_cell], t.aspect_deg[in_cell]
    steep = np.isfinite(s) & (s > cfg["steep_slope_deg"]) & np.isfinite(a)
    n = int(steep.sum())
    if n == 0:
        return _crit("c14_aspect", 0.0, cfg, n_steep=0)
    pole_az = 0.0 if lat >= 0 else 180.0
    diff = np.abs((a[steep] - pole_az + 180.0) % 360.0 - 180.0)
    return _crit("c14_aspect", (diff <= cfg["pole_sector_deg"]).mean(), cfg, n_steep=n)


# --- one cell -----------------------------------------------------------------------------------

CRITERIA = ("c7_bowl", "c9_relief", "c10_flat_base", "c11_walls", "c13_roughness", "c14_aspect")


def evaluate_polar_cell(mg, in_cell: np.ndarray, usable: np.ndarray | None, lat: float, cfg: dict) -> dict:
    """All Polar terrain criteria for one buffered cell. Returns a flat dict:
    <criterion> raw, s_<criterion> score (None until ranked / no data), extra info, drop reason."""
    pcfg = cfg["polar"]
    usable = np.ones_like(in_cell) if usable is None else usable
    t = compute_terrain(mg, relief_window_m=pcfg["relief_window_m"],
                        roughness_window_px=pcfg["roughness_window_px"])
    if not (in_cell & np.isfinite(mg.dem)).any():
        return {"keep": False, "reason": "no DEM data in cell", **{c: None for c in CRITERIA}}

    r, c, dep = low_point(mg.dem, in_cell, mg.res_m, pcfg)
    low = (r, c)
    res = {
        "c7_bowl": c7_bowl(dep, pcfg),
        "c9_relief": c9_relief(t, low, pcfg),
        "c10_flat_base": c10_flat_base(t, in_cell, usable, mg.res_m, pcfg),
        "c11_walls": c11_walls(t, low, mg.res_m, pcfg),
        "c13_roughness": c13_roughness(t, in_cell, pcfg),
        "c14_aspect": c14_aspect(t, in_cell, lat, pcfg),
    }
    reasons = []
    base_slope = res["c10_flat_base"].raw
    if base_slope is None:
        reasons.append("no usable base pad")
    elif base_slope > pcfg["max_base_slope_deg"]:
        reasons.append(f"base-spot slope {base_slope:.1f}>{pcfg['max_base_slope_deg']:g} deg")

    out = {"keep": not reasons, "reason": "; ".join(reasons),
           "has_depression": dep is not None, "low_row": int(r), "low_col": int(c),
           "low_elev_m": round(float(mg.dem[low]), 1)}
    for name, cr in res.items():
        out[name] = None if cr.raw is None else round(cr.raw, 4)
        out[f"s_{name}"] = None if cr.score is None else round(cr.score, 4)
    out["c7_depth_m"] = res["c7_bowl"].info["depth_m"]
    out["c7_width_m"] = res["c7_bowl"].info["width_m"]
    out["depression_extends_outside_cell"] = dep["extends_outside_cell"] if dep else None
    base = res["c10_flat_base"].info["base"]
    out["base_row"], out["base_col"] = base if base else (None, None)
    out["c14_n_steep"] = res["c14_aspect"].info["n_steep"]
    return out
