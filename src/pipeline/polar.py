"""Polar terrain criteria v1 (DEM only): 7 bowl, 9 relief, 10 flat base spot, 11 steep walls,
13 roughness, 14 aspect. Numbers follow the team plan (docs/HANDOFF_terrain.md).

A cell is scored as ONE coherent place: a depression (bowl) + the walls around it + a base
spot near it.
1. Fill closed depressions on the whole buffered window (cell + polar.buffer_m), so a
   depression crossing the cell border is found whole.
2. Candidates = depressions at least min_depression_depth_m deep and min_depression_width_m
   wide whose low point (deepest pixel) lies INSIDE the cell (nothing is counted twice).
   No qualifying depression -> one fallback candidate anchored at the cell's lowest pixel with
   bowl = 0 (interpreted; polar.require_depression: true drops the cell instead).
3. Per candidate: 7 depth/width, 9 relief at its low point, 10 flattest usable pad within
   max_base_to_low_km of the low point (rejected if > max_base_slope_deg), 11 mean slope in the
   wall ring around the low point, 14 pole-facing share of the steep pixels within the ring's
   outer radius. 13 roughness is cell-wide.
4. The best candidate (highest weighted score) is the cell's result. In run_pipeline, rank
   scores are computed across ALL candidates of the run before choosing (select_best).

Rules: no pixel is ever masked by slope; the only slope limit is on the base pad. 10 and 11 stay
separate. Missing data = None, never 0.
"""
from __future__ import annotations

import heapq

import numpy as np
from scipy import ndimage

from dem.terrain import compute_terrain
from pipeline.scoring import apply_rank, score_direct, weighted_score

CRITERIA = ("c7_bowl", "c9_relief", "c10_flat_base", "c11_walls", "c13_roughness", "c14_aspect")
PLACE_CRITERIA = ("c7_bowl", "c9_relief", "c10_flat_base", "c11_walls", "c14_aspect")


def _f(v):
    return None if v is None or not np.isfinite(v) else float(v)


# --- depressions ------------------------------------------------------------------------------

def fill_depressions(z: np.ndarray) -> np.ndarray:
    """Priority-flood fill (Barnes, Lehman & Mulla 2014): every closed depression is raised to its
    spill level. Grid edges and NaN pixels are outlets (water can leave there)."""
    h, w = z.shape
    nan = np.isnan(z)
    filled = np.where(nan, np.nan, z).astype(np.float64)
    done = nan.copy()
    heap = []
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


def find_depressions(z: np.ndarray, in_cell: np.ndarray, res_m: float, pcfg: dict) -> list[dict]:
    """Qualifying closed depressions whose low point lies inside the cell."""
    depth = fill_depressions(z) - z
    labels, n = ndimage.label(np.nan_to_num(depth) > 1e-6, structure=np.ones((3, 3), bool))
    if n == 0:
        return []
    idx = np.arange(1, n + 1)
    d = np.nan_to_num(depth)
    max_depth = ndimage.maximum(d, labels, idx)
    low = ndimage.maximum_position(d, labels, idx)
    count = ndimage.sum(np.ones_like(d), labels, idx)
    out = []
    for k in range(n):
        width = 2 * np.sqrt(count[k] * res_m ** 2 / np.pi)       # equivalent diameter
        r, c = (int(v) for v in low[k])
        if (max_depth[k] >= pcfg["min_depression_depth_m"] and width >= pcfg["min_depression_width_m"]
                and in_cell[r, c]):
            out.append({"low": (r, c), "depth_m": float(max_depth[k]), "width_m": float(width),
                        "extends_outside_cell": bool(((labels == k + 1) & ~in_cell).any())})
    return out


# --- per-place criteria -------------------------------------------------------------------------

class _Cell:
    """Arrays shared by all candidates of one cell (computed once)."""

    def __init__(self, mg, in_cell, usable, lat, cfg):
        p = cfg["polar"]
        self.mg, self.in_cell, self.lat, self.cfg, self.p = mg, in_cell, lat, cfg, p
        self.t = compute_terrain(mg, relief_window_m=p["relief_window_m"],
                                 roughness_window_px=p["roughness_window_px"])
        self.rr, self.cc = np.indices(mg.dem.shape)
        s = self.t.slope_deg
        k = max(1, int(round(p["pad_m"] / mg.res_m))) | 1
        ok = usable & np.isfinite(s)
        full = ndimage.minimum_filter(ok.astype(np.uint8), size=k, mode="constant", cval=0) == 1
        mean = ndimage.uniform_filter(np.where(np.isfinite(s), s, 0.0), size=k, mode="nearest")
        self.pad_mean = np.where(full, mean, np.inf)        # mean slope of a fully usable k x k pad
        self.pad_px = k

    def dist_m(self, low):
        return np.hypot(self.rr - low[0], self.cc - low[1]) * self.mg.res_m

    def place(self, low, dep: dict | None) -> dict:
        p, t, crit = self.p, self.t, self.p["criteria"]
        d = self.dist_m(low)
        raw = {}
        raw["c7_bowl"] = dep["depth_m"] / dep["width_m"] if dep else 0.0
        raw["c9_relief"] = _f(t.relief_m[low])
        # 10: flattest usable pad whose centre is within max_base_to_low_km of the low point
        pads = np.where(d <= p["max_base_to_low_km"] * 1000, self.pad_mean, np.inf)
        if np.isfinite(pads).any():
            br, bc = np.unravel_index(np.argmin(pads), pads.shape)
            raw["c10_flat_base"], base = float(pads[br, bc]), (int(br), int(bc))
        else:
            raw["c10_flat_base"], base = None, None
        # 11: walls = ring around the low point (never masked by slope)
        ring = (d >= p["wall_ring_m"][0]) & (d <= p["wall_ring_m"][1])
        s = t.slope_deg[ring]
        raw["c11_walls"] = _f(np.nanmean(s)) if ring.any() and np.isfinite(s).mean() >= 0.5 else None
        # 14: steep pixels within the ring's outer radius that face the nearer pole
        near = d <= p["wall_ring_m"][1]
        sl, a = t.slope_deg[near], t.aspect_deg[near]
        steep = np.isfinite(sl) & (sl > p["steep_slope_deg"]) & np.isfinite(a)
        n_steep = int(steep.sum())
        if n_steep:
            pole_az = 0.0 if self.lat >= 0 else 180.0
            diff = np.abs((a[steep] - pole_az + 180.0) % 360.0 - 180.0)
            raw["c14_aspect"] = float((diff <= p["pole_sector_deg"]).mean())
        else:
            raw["c14_aspect"] = 0.0                       # (interpreted) no steep walls at all

        reasons = []
        if raw["c10_flat_base"] is None:
            reasons.append(f"no usable base pad within {p['max_base_to_low_km']:g} km")
        elif raw["c10_flat_base"] > p["max_base_slope_deg"]:
            reasons.append(f"base-spot slope {raw['c10_flat_base']:.1f}>{p['max_base_slope_deg']:g} deg")

        out = {"keep": not reasons, "reason": "; ".join(reasons),
               "anchor": "depression" if dep else "lowest_point",
               "low_row": int(low[0]), "low_col": int(low[1]), "low_elev_m": round(float(self.mg.dem[low]), 1),
               "base_row": base[0] if base else None, "base_col": base[1] if base else None,
               "base_elev_m": round(float(self.mg.dem[base]), 1) if base else None,
               "base_to_low_km": round(float(d[base]) / 1000, 2) if base else None,
               "c7_depth_m": round(dep["depth_m"], 1) if dep else 0.0,
               "c7_width_m": round(dep["width_m"], 0) if dep else 0.0,
               "depression_extends_outside_cell": dep["extends_outside_cell"] if dep else None,
               "c14_n_steep": n_steep}
        for name in PLACE_CRITERIA:
            v = raw[name]
            out[name] = None if v is None else round(v, 4)
            sc = score_direct(v, crit[name])
            out[f"s_{name}"] = None if sc is None else round(sc, 4)
        return out


def polar_candidates(mg, in_cell: np.ndarray, usable: np.ndarray | None, lat: float, cfg: dict):
    """(cell-level dict, list of candidate places). Candidates carry raw values and direct
    scores; rank scores are filled later by select_best (per cell or across the whole run)."""
    p = cfg["polar"]
    usable = np.ones_like(in_cell) if usable is None else usable
    if not (in_cell & np.isfinite(mg.dem)).any():
        return {"keep": False, "reason": "no DEM data in cell", "n_depressions": 0}, []
    cell = _Cell(mg, in_cell, usable, lat, cfg)
    deps = find_depressions(mg.dem, in_cell, mg.res_m, p)

    rough = cell.t.roughness_m[in_cell]
    rough = rough[np.isfinite(rough)]
    c13 = _f(np.median(rough)) if rough.size else None
    s13 = score_direct(c13, p["criteria"]["c13_roughness"])
    info = {"keep": True, "reason": "", "n_depressions": len(deps),
            "c13_roughness": None if c13 is None else round(c13, 4),
            "s_c13_roughness": None if s13 is None else round(s13, 4)}

    if deps:
        cands = [cell.place(dp["low"], dp) for dp in deps]
    elif p["require_depression"]:
        info.update(keep=False, reason="no depression >= "
                    f"{p['min_depression_depth_m']:g} m deep and >= {p['min_depression_width_m']:g} m wide")
        return info, []
    else:
        zc = np.where(in_cell & np.isfinite(mg.dem), mg.dem, np.inf)
        low = np.unravel_index(np.argmin(zc), zc.shape)
        cands = [cell.place((int(low[0]), int(low[1])), None)]
    for c in cands:
        c["c13_roughness"], c["s_c13_roughness"] = info["c13_roughness"], info["s_c13_roughness"]
    if not any(c["keep"] for c in cands):
        info.update(keep=False, reason=cands[0]["reason"] if len(cands) == 1
                    else f"none of {len(cands)} depressions has a flat usable base within "
                         f"{p['max_base_to_low_km']:g} km")
    return info, cands


def select_best(cands: list[dict], criteria: dict) -> None:
    """Rank all valid candidates against each other, add weighted score; marks 'best' per call."""
    valid = [c for c in cands if c["keep"]]
    apply_rank(valid, criteria)
    for c in valid:
        c["score"], c["n_scored"] = weighted_score(c, criteria)


def best_of(cands: list[dict]) -> dict | None:
    valid = [c for c in cands if c["keep"] and c.get("score") is not None]
    if not valid:
        return None
    return max(valid, key=lambda c: (c["score"], c["c7_depth_m"]))


def evaluate_polar_cell(mg, in_cell, usable, lat, cfg) -> dict:
    """Single-cell use (tests, quick checks): ranks the cell's own candidates against each other
    and returns the best one merged with the cell info. run_pipeline ranks across the whole run."""
    info, cands = polar_candidates(mg, in_cell, usable, lat, cfg)
    select_best(cands, cfg["polar"]["criteria"])
    best = best_of(cands)
    if best is None:
        base = cands[0] if cands else {}
        out = {**{c: None for c in CRITERIA}, **base, **info}
        out["keep"] = False
        return out
    return {**best, **{k: v for k, v in info.items() if k not in ("keep", "reason")},
            "n_candidates": len(cands)}
